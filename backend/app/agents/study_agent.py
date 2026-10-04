from typing import Any
from app.agents.base import BaseAgent, AgentRunResult

class StudyAgentRegistration(BaseAgent):
    """Study Agent for ingesting and interacting with study material via RAG."""
    
    name: str = "study_agent"
    description: str = (
        "Agent responsible for managing and querying a local RAG vector store of study documents. "
        "It can ingest PDFs, text files, markdown, presentations, and answer questions grounded strictly in the user's material."
    )
    tools: list = [
        "study_ingest_document",
        "study_search",
        "study_list_documents",
        "study_remove_document",
        "study_ask"
    ]

    async def run(self, task: str, context: Any = None) -> AgentRunResult:
        # Currently, the orchestrator just routes tasks or uses this for tool association.
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="Study agent executed task."
        )
