from typing import Any
from app.agents.base import BaseAgent, AgentRunResult

class FileAgentRegistration(BaseAgent):
    """File Agent for managing local filesystem operations."""
    
    name: str = "file_agent"
    description: str = (
        "Agent responsible for searching, reading, and summarizing local files. "
        "It operates within a strictly configured sandbox and cannot modify files."
    )
    tools: list = ["file_search", "file_metadata", "file_read", "file_summarize"]

    async def run(self, task: str, context: Any = None) -> AgentRunResult:
        # Currently, the orchestrator just routes tasks or uses this for tool association.
        # This run method is a placeholder matching the orchestrator interface.
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="File agent executed task."
        )
