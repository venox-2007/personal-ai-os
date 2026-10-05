import json
from typing import List, Dict, Any
from app.integrations.llm_provider import BaseLLMProvider, LLMMessage
from app.agents.registry import AgentRegistry, agent_registry
from app.tools import ToolRegistry, tool_registry
from app.schemas.workflow import WorkflowPlan, WorkflowPlanStep
from app.permissions.models import PermissionLevel

class WorkflowPlannerError(Exception):
    pass

class WorkflowPlanner:
    def __init__(self, llm_provider: BaseLLMProvider, agents: AgentRegistry = None, tools: ToolRegistry = None):
        self.llm = llm_provider
        self.agents = agents or agent_registry
        self.tools = tools or tool_registry

    async def plan_workflow(self, goal: str) -> WorkflowPlan:
        # Build available tools schema
        available_tools = []
        for agent_inst in self.agents.list_agents():
            for tool_name in agent_inst.tools:
                tool_inst = self.tools.get(tool_name)
                if tool_inst:
                    available_tools.append({
                        "agent": agent_inst.name,
                        "tool_name": tool_inst.name,
                        "description": tool_inst.description,
                        "permission_level": tool_inst.permission_level.value,
                        "schema": tool_inst.parameters_schema
                    })

        system_prompt = f"""You are the Personal AI OS Workflow Planner.
Your job is to translate a complex user request into a strictly structured JSON workflow plan.
Available tools:
{json.dumps(available_tools, indent=2)}

Rules:
1. Output valid JSON matching this schema:
{{
  "goal": "string",
  "steps": [
    {{
      "step_id": "step_1",
      "agent": "agent_name",
      "action": "description",
      "tool_name": "exact_tool_name",
      "input_mapping": {{"arg": "value or ${{step_X.output.field}}"}},
      "depends_on": ["step_X"],
      "on_failure": "FAIL" or "SKIP"
    }}
  ]
}}
2. Maximum 10 steps.
3. NEVER invent tool names or agent names. Only use the provided list.
4. If a step uses output from a previous step, reference it using strict string format: "${{step_id.output.json_field}}".
5. Do NOT execute Python or arbitary logic. Just pure function mapping.
6. Order steps sequentially based on dependencies.
"""
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"Create a workflow plan for this goal: {goal}\nRespond ONLY with JSON.")
        ]

        # In a real implementation we'd use response_format={"type": "json_object"} if supported
        res = await self.llm.chat(messages)
        content = res.content.strip()
        
        # Clean markdown backticks if any
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise WorkflowPlannerError(f"Failed to parse LLM JSON: {e}\nContent: {content}")

        return self._validate_and_build(data)

    def _validate_and_build(self, data: Dict[str, Any]) -> WorkflowPlan:
        steps = []
        step_ids = set()
        
        for idx, s in enumerate(data.get("steps", [])):
            if len(steps) >= 10:
                break
                
            step_id = s.get("step_id", f"step_{idx+1}")
            if step_id in step_ids:
                raise WorkflowPlannerError(f"Duplicate step_id: {step_id}")
            step_ids.add(step_id)
            
            # Validate agent
            agent = s.get("agent")
            if not self.agents.get(agent):
                raise WorkflowPlannerError(f"Invalid agent: {agent}")
                
            # Validate tool
            tool_name = s.get("tool_name")
            tool = self.tools.get(tool_name)
            if not tool:
                raise WorkflowPlannerError(f"Invalid tool: {tool_name}")
                
            # Validate dependencies
            for dep in s.get("depends_on", []):
                if dep not in step_ids:
                    raise WorkflowPlannerError(f"Invalid dependency '{dep}' for step '{step_id}'. Note: dependencies must appear before the step in the list.")

            requires_approval = tool.permission_level >= PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT

            steps.append(WorkflowPlanStep(
                step_id=step_id,
                agent=agent,
                action=s.get("action", "Execute tool"),
                tool_name=tool_name,
                input_mapping=s.get("input_mapping", {}),
                depends_on=s.get("depends_on", []),
                requires_approval=requires_approval,
                on_failure=s.get("on_failure", "FAIL")
            ))

        return WorkflowPlan(
            goal=data.get("goal", "Workflow"),
            steps=steps,
            max_steps=10
        )
