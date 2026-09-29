"""Central Orchestrator Agent coordinating multi-step planning, tool calling, and human-in-the-loop approvals."""

import json
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.agents.activity import (
    AgentActivityEvent,
    ActivityType,
    ActivityStatus,
)
from app.agents.registry import AgentRegistry, agent_registry
from app.core.config import settings
from app.core.logging import logger
from app.integrations.llm_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    ToolCall,
    ModelAvailabilityStatus,
)
from app.integrations.ollama_provider import OllamaProvider
from app.memory.storage import UnifiedMemoryManager, memory_manager
from app.permissions.models import PermissionContext, ApprovalRequest
from app.services.approval_service import (
    ApprovalService,
    approval_service,
)
from app.tools.registry import ToolRegistry, tool_registry


SYSTEM_ORCHESTRATOR_PROMPT = """You are the central Orchestrator of Personal AI OS, a local-first, privacy-respecting personal AI platform.
You interact directly with the user, understand their goals, retrieve contextual knowledge, and coordinate tools.

Guidelines:
1. When the user asks for operational or system status, or actions that require a tool, use the appropriate available tool.
2. If the user asks a general question or conversational request where no tool is needed, respond directly, politely, and concisely.
3. Once a tool has returned its results, synthesize those results into a helpful, natural-language response. Do not repeat raw JSON unless asked.
4. Do not invent or hallucinate tool names. Only call tools that are explicitly declared in the tool definitions.
"""


class Orchestrator:
    """Central Orchestrator Agent executing the agentic tool-calling lifecycle with HITL approval traps."""

    def __init__(
        self,
        agents: Optional[AgentRegistry] = None,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[UnifiedMemoryManager] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        approval_svc: Optional[ApprovalService] = None,
        permission_context: Optional[PermissionContext] = None,
        max_tool_iterations: Optional[int] = None,
    ) -> None:
        self.agents = agents or agent_registry
        self.tools = tools or tool_registry
        self.memory = memory or memory_manager
        self.llm = llm_provider or OllamaProvider()
        self.approval_service = approval_svc or approval_service
        self.permission_context = permission_context or PermissionContext(
            require_level_2_approval=settings.REQUIRE_APPROVAL_FOR_LEVEL_2,
            require_level_3_approval=settings.REQUIRE_APPROVAL_FOR_LEVEL_3,
        )
        self.max_tool_iterations = max_tool_iterations or settings.MAX_TOOL_ITERATIONS

    async def handle_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> Tuple[str, str, List[AgentActivityEvent], List[Dict[str, Any]], str, Optional[Dict[str, Any]]]:
        """Processes an incoming user message through the multi-step tool-calling agent loop.

        Returns:
            Tuple of:
            - conversation_id (str)
            - final_response_text (str)
            - activities (List[AgentActivityEvent])
            - executed_tool_calls (List[Dict[str, Any]])
            - status (str: "completed", "waiting_approval", or "error")
            - approval_dict (Optional[Dict[str, Any]])
        """
        conv_id = conversation_id or str(uuid.uuid4())
        activities: List[AgentActivityEvent] = []
        executed_tool_calls: List[Dict[str, Any]] = []

        # Record incoming message in conversation memory
        await self.memory.conversation.add_message(conv_id, "user", message)

        # Step 1: Check LLM Provider & Model Availability
        try:
            model_status = await self.llm.check_model_status()
        except Exception as e:
            logger.warning(f"Failed to check LLM model status: {e}")
            model_status = ModelAvailabilityStatus.PROVIDER_UNAVAILABLE

        if model_status == ModelAvailabilityStatus.PROVIDER_UNAVAILABLE:
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.PLANNING,
                    status=ActivityStatus.WARNING,
                    action="Assessed local LLM engine status",
                    description=f"Provider '{self.llm.provider_name}' is unreachable at configured endpoint.",
                )
            )
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action="LLM connection unavailable",
                    description="Local Ollama daemon is offline. Standing by in offline mode.",
                )
            )
            response_text = (
                f"⚠️ **Local LLM Engine Offline**\n\n"
                f"The local inference service ({self.llm.provider_name}) is currently unreachable at `{settings.OLLAMA_BASE_URL}`.\n\n"
                f"To enable local autonomous execution at ₹0 cost, please start Ollama in your terminal:\n"
                f"```bash\nollama run {settings.OLLAMA_MODEL}\n```\n"
                f"The Personal AI OS architecture remains healthy and ready to process requests once the engine starts."
            )
            await self.memory.conversation.add_message(conv_id, "assistant", response_text)
            return conv_id, response_text, activities, executed_tool_calls, "error", None

        if model_status == ModelAvailabilityStatus.MODEL_NOT_FOUND:
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action=f"Model not found: '{settings.OLLAMA_MODEL}'",
                    description=f"Ollama is running, but the configured model '{settings.OLLAMA_MODEL}' has not been pulled.",
                )
            )
            response_text = (
                f"⚠️ **Model Not Found in Ollama**\n\n"
                f"Ollama is online, but model `{settings.OLLAMA_MODEL}` is not installed.\n\n"
                f"Please download the model locally by running:\n"
                f"```bash\nollama pull {settings.OLLAMA_MODEL}\n```"
            )
            await self.memory.conversation.add_message(conv_id, "assistant", response_text)
            return conv_id, response_text, activities, executed_tool_calls, "error", None

        # Step 2: Build Context & Messages History
        history = await self.memory.conversation.get_messages(conv_id, limit=10)
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=SYSTEM_ORCHESTRATOR_PROMPT)
        ]

        for h in history:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant"):
                messages.append(LLMMessage(role=role, content=content))

        # Ensure current user message is at the end if not already present
        if not messages or messages[-1].content != message or messages[-1].role != "user":
            messages.append(LLMMessage(role="user", content=message))

        # Step 3: Collect available tool schemas from ToolRegistry
        all_tools = self.tools.list_tools()
        tool_definitions = [t.to_llm_tool_definition() for t in all_tools]

        activities.append(
            AgentActivityEvent(
                agent="Orchestrator",
                activity_type=ActivityType.PLANNING,
                status=ActivityStatus.SUCCESS,
                action="Analyzed request and prepared execution plan",
                description=f"Discovered {len(all_tools)} tools. Dispatched prompt to {self.llm.provider_name}.",
                metadata={"available_tools": [t.name for t in all_tools]},
            )
        )

        # Step 4: Multi-Step Tool Execution Loop
        iteration = 0
        final_text = ""

        while iteration < self.max_tool_iterations:
            iteration += 1

            try:
                llm_response: LLMResponse = await self.llm.chat(
                    messages=messages,
                    tools=tool_definitions if tool_definitions else None,
                )
            except Exception as e:
                logger.error(f"Error during LLM chat turn: {e}", exc_info=True)
                activities.append(
                    AgentActivityEvent(
                        agent="Orchestrator",
                        activity_type=ActivityType.ERROR,
                        status=ActivityStatus.FAILED,
                        action="Inference error occurred",
                        description=f"LLM generation failed: {str(e)}",
                    )
                )
                err_text = f"An error occurred while communicating with the LLM engine: {str(e)}"
                await self.memory.conversation.add_message(conv_id, "assistant", err_text)
                return conv_id, err_text, activities, executed_tool_calls, "error", None

            # Case A: Model responded with normal text without tool requests
            if not llm_response.has_tool_calls:
                final_text = llm_response.content or "Task completed."
                activities.append(
                    AgentActivityEvent(
                        agent="Orchestrator",
                        activity_type=ActivityType.COMPLETED,
                        status=ActivityStatus.SUCCESS,
                        action="Completed response generation",
                        description="Synthesized final response without further actions.",
                    )
                )
                await self.memory.conversation.add_message(conv_id, "assistant", final_text)
                return conv_id, final_text, activities, executed_tool_calls, "completed", None

            # Case B: Model requested one or more tool calls
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=llm_response.content or "",
                    tool_calls=llm_response.tool_calls,
                )
            )

            for tc in llm_response.tool_calls:
                activities.append(
                    AgentActivityEvent(
                        agent="Orchestrator",
                        activity_type=ActivityType.AGENT_SELECTED,
                        status=ActivityStatus.SUCCESS,
                        action=f"Selected tool: {tc.name}",
                        description=f"Model requested execution of tool '{tc.name}'",
                        metadata={"arguments": tc.arguments},
                    )
                )

                # Validate tool existence in registry
                tool = self.tools.get(tc.name)
                if not tool:
                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.ERROR,
                            status=ActivityStatus.FAILED,
                            action=f"Tool '{tc.name}' not found",
                            description=f"Model invoked unregistered tool name '{tc.name}'.",
                        )
                    )
                    error_payload = {"error": f"Tool '{tc.name}' is not registered in the system."}
                    messages.append(
                        LLMMessage(
                            role="tool",
                            name=tc.name,
                            tool_call_id=tc.id,
                            content=json.dumps(error_payload),
                        )
                    )
                    continue

                # Validate tool input arguments
                is_valid, validation_err = tool.validate_arguments(tc.arguments)
                if not is_valid:
                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.ERROR,
                            status=ActivityStatus.FAILED,
                            action=f"Argument validation failed for '{tool.name}'",
                            description=validation_err,
                        )
                    )
                    error_payload = {"error": f"Invalid arguments: {validation_err}"}
                    messages.append(
                        LLMMessage(
                            role="tool",
                            name=tool.name,
                            tool_call_id=tc.id,
                            content=json.dumps(error_payload),
                        )
                    )
                    continue

                # Check Permission Level & Approval requirements
                if self.permission_context.requires_approval(tool.permission_level):
                    # Create persistent ApprovalRequest
                    approval_req = self.approval_service.create_request(
                        tool_name=tool.name,
                        tool_description=tool.description,
                        permission_level=tool.permission_level,
                        arguments=tc.arguments,
                        action_description=f"Execute {tool.name} with arguments: {list(tc.arguments.keys())}",
                        conversation_id=conv_id,
                        execution_context={
                            "messages": [m.to_provider_dict() for m in messages],
                            "tc": tc.model_dump(),
                            "executed_tool_calls": executed_tool_calls,
                            "iteration": iteration,
                        },
                    )

                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.APPROVAL_REQUIRED,
                            status=ActivityStatus.WAITING_APPROVAL,
                            action=f"Approval required for '{tool.name}'",
                            description=(
                                f"Action classified as {tool.permission_level.label} "
                                f"(Level {tool.permission_level.value}). Awaiting explicit user confirmation."
                            ),
                            metadata={
                                "approval_id": approval_req.id,
                                "tool_name": tool.name,
                                "permission_level": tool.permission_level.value,
                                "arguments": tc.arguments,
                            },
                        )
                    )
                    waiting_text = (
                        f"🛡️ **Action Requires Confirmation**\n\n"
                        f"The requested action `{tool.name}` is classified as **{tool.permission_level.label}** "
                        f"(Level {tool.permission_level.value}).\n\n"
                        f"Please approve or reject this action using the authorization card below."
                    )
                    await self.memory.conversation.add_message(conv_id, "assistant", waiting_text)
                    return conv_id, waiting_text, activities, executed_tool_calls, "waiting_approval", approval_req.to_dict()

                # Execute tool (Level 0 / Level 1 without approval requirement)
                activities.append(
                    AgentActivityEvent(
                        agent="Orchestrator",
                        activity_type=ActivityType.TOOL_STARTED,
                        status=ActivityStatus.RUNNING,
                        action=f"Executing tool '{tool.name}'",
                        description=f"Permission {tool.permission_level.label} verified. Invoking local logic.",
                    )
                )

                try:
                    tool_result = await tool.execute(**tc.arguments)
                except Exception as e:
                    logger.error(f"Error during tool '{tool.name}' execution: {e}", exc_info=True)
                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.ERROR,
                            status=ActivityStatus.FAILED,
                            action=f"Execution error in '{tool.name}'",
                            description=str(e),
                        )
                    )
                    error_payload = {"error": f"Tool execution failed: {str(e)}"}
                    messages.append(
                        LLMMessage(
                            role="tool",
                            name=tool.name,
                            tool_call_id=tc.id,
                            content=json.dumps(error_payload),
                        )
                    )
                    executed_tool_calls.append({
                        "name": tool.name,
                        "arguments": tc.arguments,
                        "success": False,
                        "error": str(e),
                    })
                    continue

                if not tool_result.success:
                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.ERROR,
                            status=ActivityStatus.FAILED,
                            action=f"Tool '{tool.name}' reported failure",
                            description=tool_result.error or "Unknown error",
                        )
                    )
                    payload = {"error": tool_result.error or "Tool returned failure."}
                else:
                    activities.append(
                        AgentActivityEvent(
                            agent="Orchestrator",
                            activity_type=ActivityType.TOOL_COMPLETED,
                            status=ActivityStatus.SUCCESS,
                            action=f"Completed tool '{tool.name}'",
                            description="Successfully executed and produced observation data.",
                        )
                    )
                    payload = tool_result.output

                executed_tool_calls.append({
                    "name": tool.name,
                    "arguments": tc.arguments,
                    "success": tool_result.success,
                    "output": tool_result.output,
                })

                # Pass observation result back to the LLM
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=tool.name,
                        tool_call_id=tc.id,
                        content=json.dumps(payload) if not isinstance(payload, str) else payload,
                    )
                )

        # Loop limit reached
        activities.append(
            AgentActivityEvent(
                agent="Orchestrator",
                activity_type=ActivityType.ERROR,
                status=ActivityStatus.FAILED,
                action="Loop limit exceeded",
                description=f"Reached maximum allowed iterations ({self.max_tool_iterations}).",
            )
        )
        limit_text = (
            f"The Orchestrator halted execution because it reached the limit of "
            f"{self.max_tool_iterations} tool execution iterations."
        )
        await self.memory.conversation.add_message(conv_id, "assistant", limit_text)
        return conv_id, limit_text, activities, executed_tool_calls, "error", None

    async def resolve_and_resume(
        self,
        approval_id: str,
        approved: bool,
        reason: Optional[str] = None,
        decided_by: str = "user",
    ) -> Tuple[str, str, List[AgentActivityEvent], List[Dict[str, Any]], str, ApprovalRequest]:
        """Resumes interrupted orchestrator execution following a human approval decision.

        If approved:
            Authorizes and executes the previously paused tool, feeds result to LLM,
            and produces the final synthesized response.
        If rejected:
            Aborts tool execution, updates approval state, and returns a graceful rejection response.

        Returns:
            Tuple of:
            - conversation_id (str)
            - final_response (str)
            - activities (List[AgentActivityEvent])
            - executed_tool_calls (List[Dict[str, Any]])
            - status (str: "completed" or "rejected")
            - approval_request (ApprovalRequest)
        """
        activities: List[AgentActivityEvent] = []
        executed_tool_calls: List[Dict[str, Any]] = []

        if not approved:
            # Rejection flow: never execute tool!
            req = self.approval_service.reject_request(approval_id, reason=reason, decided_by=decided_by)
            conv_id = req.conversation_id or str(uuid.uuid4())

            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.STATUS_MESSAGE,
                    status=ActivityStatus.SUCCESS,
                    action=f"User rejected action '{req.tool_name}'",
                    description=reason or "Authorization declined by user.",
                )
            )

            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.COMPLETED,
                    status=ActivityStatus.SUCCESS,
                    action="Execution safely terminated",
                    description=f"Tool '{req.tool_name}' was not executed.",
                )
            )

            rejection_text = (
                f"I didn't execute `{req.tool_name}` because you rejected the authorization request."
                + (f" (Reason: {reason})" if reason else "")
            )
            await self.memory.conversation.add_message(conv_id, "assistant", rejection_text)
            return conv_id, rejection_text, activities, executed_tool_calls, "rejected", req

        # Approval flow: authorize and execute
        req = self.approval_service.approve_request(approval_id, reason=reason, decided_by=decided_by)
        conv_id = req.conversation_id or str(uuid.uuid4())

        activities.append(
            AgentActivityEvent(
                agent="Orchestrator",
                activity_type=ActivityType.STATUS_MESSAGE,
                status=ActivityStatus.SUCCESS,
                action=f"User approved action '{req.tool_name}'",
                description=reason or "Human authorization confirmed.",
            )
        )

        tool = self.tools.get(req.tool_name)
        if not tool:
            err_msg = f"Approved tool '{req.tool_name}' is no longer registered in the system."
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action="Tool not found",
                    description=err_msg,
                )
            )
            return conv_id, err_msg, activities, executed_tool_calls, "error", req

        # Security double-check: verify tool matches approval
        if tool.name != req.tool_name:
            err_msg = f"Security mismatch: Approval tool '{req.tool_name}' does not match requested tool '{tool.name}'."
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action="Security validation failed",
                    description=err_msg,
                )
            )
            return conv_id, err_msg, activities, executed_tool_calls, "error", req

        # Execute approved tool
        activities.append(
            AgentActivityEvent(
                agent="Orchestrator",
                activity_type=ActivityType.TOOL_STARTED,
                status=ActivityStatus.RUNNING,
                action=f"Executing approved tool '{tool.name}'",
                description=f"Authorization confirmed. Invoking action with arguments: {list(req.arguments.keys())}",
            )
        )

        try:
            tool_result = await tool.execute(**req.arguments)
        except Exception as e:
            logger.error(f"Error during execution of approved tool '{tool.name}': {e}", exc_info=True)
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action=f"Error executing approved '{tool.name}'",
                    description=str(e),
                )
            )
            err_text = f"Tool '{tool.name}' failed during execution: {str(e)}"
            return conv_id, err_text, activities, executed_tool_calls, "error", req

        if not tool_result.success:
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.ERROR,
                    status=ActivityStatus.FAILED,
                    action=f"Approved tool '{tool.name}' reported failure",
                    description=tool_result.error or "Unknown error",
                )
            )
            payload = {"error": tool_result.error or "Tool reported failure."}
        else:
            activities.append(
                AgentActivityEvent(
                    agent="Orchestrator",
                    activity_type=ActivityType.TOOL_COMPLETED,
                    status=ActivityStatus.SUCCESS,
                    action=f"Completed authorized tool '{tool.name}'",
                    description="Execution output captured successfully.",
                )
            )
            payload = tool_result.output

        executed_tool_calls.append({
            "name": tool.name,
            "arguments": req.arguments,
            "success": tool_result.success,
            "output": tool_result.output,
        })

        # Reconstruct preserved messages context to continue LLM generation
        context_data = req.execution_context or {}
        raw_msgs = context_data.get("messages", [])
        tc_dict = context_data.get("tc", {})

        messages: List[LLMMessage] = []
        if raw_msgs:
            for rm in raw_msgs:
                tcs = [ToolCall(**tc_item["function"]) for tc_item in rm.get("tool_calls", [])] if rm.get("tool_calls") else None
                messages.append(
                    LLMMessage(
                        role=rm.get("role", "user"),
                        content=rm.get("content", ""),
                        tool_calls=tcs,
                        tool_call_id=rm.get("tool_call_id"),
                        name=rm.get("name"),
                    )
                )
        else:
            messages = [
                LLMMessage(role="system", content=SYSTEM_ORCHESTRATOR_PROMPT),
                LLMMessage(role="user", content=f"Execute action {req.tool_name}"),
            ]

        # Append tool observation
        messages.append(
            LLMMessage(
                role="tool",
                name=tool.name,
                tool_call_id=tc_dict.get("id"),
                content=json.dumps(payload) if not isinstance(payload, str) else payload,
            )
        )

        # Query LLM for final synthesized response
        try:
            all_tools = self.tools.list_tools()
            tool_definitions = [t.to_llm_tool_definition() for t in all_tools]
            llm_response = await self.llm.chat(messages=messages, tools=tool_definitions)
            final_response = llm_response.content or f"Action '{tool.name}' was executed successfully."
        except Exception as e:
            logger.warning(f"Failed to get final LLM response after tool execution: {e}")
            final_response = f"Action '{tool.name}' executed successfully with output: {payload}"

        activities.append(
            AgentActivityEvent(
                agent="Orchestrator",
                activity_type=ActivityType.COMPLETED,
                status=ActivityStatus.SUCCESS,
                action="Completed authorized workflow",
                description="Synthesized final response based on observation results.",
            )
        )

        await self.memory.conversation.add_message(conv_id, "assistant", final_response)
        return conv_id, final_response, activities, executed_tool_calls, "completed", req


# Global default instance
orchestrator = Orchestrator()
