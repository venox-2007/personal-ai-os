from typing import Any
from app.agents.base import BaseAgent, AgentRunResult

class CodingAgentRegistration(BaseAgent):
    """Coding Agent for inspecting and understanding software repositories."""
    
    name: str = "coding_agent"
    description: str = (
        "Agent responsible for understanding local software repositories and GitHub data. "
        "It can search code, inspect files, check git history, and explain architectures."
    )
    tools: list = [
        "code_list_repository",
        "code_search",
        "code_read_file",
        "code_git_status",
        "code_git_log",
        "code_git_show",
        "code_repo_metadata",
        "github_repo_info"
    ]

    async def run(self, task: str, context: Any = None) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="Coding agent executed task."
        )
