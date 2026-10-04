"""FastAPI application entry point for Personal AI OS."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.database.session import init_db
from app.api.router import api_router
from app.api.routes.health import get_health
from app.agents.registry import agent_registry
from app.agents.base import BaseAgent, AgentRunResult
from app.tools.registry import tool_registry
from app.tools.system_info import SystemInfoTool
from app.tools.demo_action import DemoActionTool
from app.agents.file_agent import FileAgentRegistration
from app.tools.local_file import FileSearchTool, FileMetadataTool, FileReadTool, FileSummarizeTool


class OrchestratorAgentRegistration(BaseAgent):
    """Core orchestrator registration entry."""

    name: str = "orchestrator"
    description: str = (
        "Central coordinator responsible for intent decomposition, memory retrieval, "
        "permission verification, and routing tasks to specialized agents."
    )
    tools: list = []

    async def run(self, task: str, context=None) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary="Orchestrator executed baseline evaluation.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")

    # Initialize SQLite database tables
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}", exc_info=True)

    # Register default core orchestrator agent
    if not agent_registry.get("orchestrator"):
        agent_registry.register(OrchestratorAgentRegistration())
        logger.info("Registered Core Orchestrator Agent.")

    # Register standard initial tools
    if not tool_registry.get("get_system_info"):
        tool_registry.register(SystemInfoTool())
        logger.info("Registered SystemInfoTool.")

    if not tool_registry.get("request_demo_action"):
        tool_registry.register(DemoActionTool())
        logger.info("Registered DemoActionTool.")

    # Register File Agent and its tools
    if not agent_registry.get("file_agent"):
        agent_registry.register(FileAgentRegistration())
        logger.info("Registered File Agent.")
    
    for tool_cls in [FileSearchTool, FileMetadataTool, FileReadTool, FileSummarizeTool]:
        tool = tool_cls()
        if not tool_registry.get(tool.name):
            tool_registry.register(tool)
            logger.info(f"Registered {tool.name}.")

    # Register Study Agent and its tools
    from app.agents.study_agent import StudyAgentRegistration
    from app.tools.study import (
        StudyIngestTool, StudySearchTool, StudyListDocumentsTool,
        StudyRemoveDocumentTool, StudyAskTool
    )
    
    if not agent_registry.get("study_agent"):
        agent_registry.register(StudyAgentRegistration())
        logger.info("Registered Study Agent.")
        
    for tool_cls in [StudyIngestTool, StudySearchTool, StudyListDocumentsTool, StudyRemoveDocumentTool, StudyAskTool]:
        tool = tool_cls()
        if not tool_registry.get(tool.name):
            tool_registry.register(tool)
            logger.info(f"Registered {tool.name}.")

    # Register Coding Agent and its tools
    from app.agents.coding_agent import CodingAgentRegistration
    from app.tools.coding import (
        CodeListRepositoryTool, CodeSearchTool, CodeReadFileTool,
        CodeGitStatusTool, CodeGitLogTool, CodeGitShowTool,
        CodeRepoMetadataTool, GithubRepoInfoTool,
        CodeProposeEditTool, CodeApplyEditTool, CodeGitDiffTool,
        CodeCreateBranchTool, CodeCommitTool, CodeRunTestsTool
    )
    
    if not agent_registry.get("coding_agent"):
        agent_registry.register(CodingAgentRegistration())
        logger.info("Registered Coding Agent.")
        
    for tool_cls in [
        CodeListRepositoryTool, CodeSearchTool, CodeReadFileTool,
        CodeGitStatusTool, CodeGitLogTool, CodeGitShowTool,
        CodeRepoMetadataTool, GithubRepoInfoTool,
        CodeProposeEditTool, CodeApplyEditTool, CodeGitDiffTool,
        CodeCreateBranchTool, CodeCommitTool, CodeRunTestsTool
    ]:
        tool = tool_cls()
        if not tool_registry.get(tool.name):
            tool_registry.register(tool)
            logger.info(f"Registered {tool.name}.")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Local-first, agentic personal AI operating platform.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS for Vite React frontend
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Direct GET /health endpoint for root inspection
    application.add_api_route(
        "/health",
        get_health,
        methods=["GET"],
        tags=["Health"],
        summary="Application health check",
    )

    # Mount API routes under /api
    application.include_router(api_router, prefix="/api")

    return application


app = create_application()
