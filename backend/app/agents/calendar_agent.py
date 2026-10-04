from typing import Any
from app.agents.base import BaseAgent, AgentRunResult

class CalendarAgentRegistration(BaseAgent):
    """Calendar Agent for scheduling, querying, and managing events."""
    
    name: str = "calendar_agent"
    description: str = (
        "Agent responsible for managing the local calendar. It can create events, "
        "search for events, check upcoming schedules, and manage recurrence and conflicts."
    )
    tools: list = [
        "calendar_create_event",
        "calendar_update_event",
        "calendar_delete_event",
        "calendar_list_events",
        "calendar_search",
        "calendar_upcoming",
        "calendar_find_conflicts"
    ]

    async def run(self, task: str, context: Any = None) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="Calendar agent executed task."
        )
