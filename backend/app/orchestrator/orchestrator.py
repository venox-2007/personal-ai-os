"""Central Orchestrator Agent coordinating multi-step planning, tool calling, and activity logging."""

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
from app.permissions.models import PermissionContext
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
    """Central Orchestrator Agent executing the agentic tool-calling lifecycle."""

    def __init__(
        self,
        agents: Optional[AgentRegistry] = None,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[UnifiedMemoryManager] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        permission_context: Optional[PermissionContext] = None,
        max_tool_iterations: Optional[int] = None,
    ) -> None:
        self.agents = agents or agent_registry
        self.tools = tools or tool_registry
        self.memory = memory or memory_manager
        self.llm = llm_provider or OllamaProvider()
        self.permission_context = permission_context or PermissionContext(
            require_level_2_approval=settings.REQUIRE_APPROVAL_FOR_LEVEL_2,
            require_level_3_approval=settings.REQUIRE_APPROVAL_FOR_LEVEL_3,
        )
        self.max_tool_iterations = max_tool_iterations or settings.MAX_TOOL_ITERATIONS

    async def handle_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> Tuple[str, str, List[AgentActivityEvent], List[Dict[str, Any]], str]:
        """Processes an incoming user message through the multi-step tool-calling agent loop.

        Returns:
            Tuple of:
            - conversation_id (str)
            - final_response_text (str)
            - activities (List[AgentActivityEvent])
            - executed_tool_calls (List[Dict[str, Any]])
            - status (str: "completed", "waiting_approval", or "error")
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
            return conv_id, response_text, activities, executed_tool_calls, "error"

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
            return conv_id, response_text, activities, executed_tool_calls, "error"

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
                return conv_id, err_text, activities, executed_tool_calls, "error"

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
                return conv_id, final_text, activities, executed_tool_calls, "completed"

            # Case B: Model requested one or more tool calls
            # Append assistant message with tool calls to context
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
                        f"Execution has been safely paused in accordance with Personal AI OS safety protocols."
                    )
                    await self.memory.conversation.add_message(conv_id, "assistant", waiting_text)
                    return conv_id, waiting_text, activities, executed_tool_calls, "waiting_approval"

                # Execute tool (Level 0 / Level 1 without approval)
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
        return conv_id, limit_text, activities, executed_tool_calls, "error"


# Global default instance
orchestrator = Orchestrator()
