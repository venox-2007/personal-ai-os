from typing import Any
from app.agents.base import BaseAgent, AgentRunResult

class ResearchAgentRegistration(BaseAgent):
    """Research Agent for searching the web and synthesizing cited answers."""
    
    name: str = "research_agent"
    description: str = (
        "Agent responsible for web research. It can search the web, fetch sources, "
        "and synthesize answers with citations."
    )
    tools: list = [
        "research_search",
        "research_fetch_source",
        "research_extract_evidence"
    ]

    async def run(self, task: str, context: Any = None) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="Research agent executed task."
        )
