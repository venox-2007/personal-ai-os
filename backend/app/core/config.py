"""Core configuration settings for Personal AI OS."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.paths import get_default_database_url, get_default_study_storage_dir


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Personal AI OS"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = get_default_database_url()

    # LLM Provider (Local-first / Ollama)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    DEFAULT_LLM_PROVIDER: str = "ollama"

    # Human-in-the-loop permission requirements
    REQUIRE_APPROVAL_FOR_LEVEL_2: bool = True
    REQUIRE_APPROVAL_FOR_LEVEL_3: bool = True
    APPROVAL_EXPIRY_SECONDS: int = 300

    # Tool Execution Loop
    MAX_TOOL_ITERATIONS: int = 8

    # Local File Agent Sandbox Settings
    # Comma-separated list of allowed absolute paths.
    FILE_AGENT_ALLOWED_ROOTS: str = ""

    # Study Agent / RAG Settings
    STUDY_STORAGE_DIR: str = get_default_study_storage_dir()
    STUDY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    STUDY_CHUNK_SIZE: int = 1000
    STUDY_CHUNK_OVERLAP: int = 200
    STUDY_RETRIEVAL_TOP_K: int = 5
    STUDY_MAX_DOC_SIZE_MB: int = 50

    # Coding Agent Settings
    CODING_AGENT_ALLOWED_ROOTS: str = ""
    CODING_AGENT_MAX_SEARCH_RESULTS: int = 50
    CODING_AGENT_MAX_FILE_SIZE_KB: int = 256
    GITHUB_ACCESS_TOKEN: str = ""
    # JSON string mapping test_id -> {"executable": "pytest", "args": ["backend/tests"], "cwd": "backend"}
    CODING_AGENT_TEST_COMMANDS: str = '{"backend_tests": {"executable": "pytest", "args": ["backend/tests"], "cwd": "."}, "frontend_build": {"executable": "npm", "args": ["run", "build"], "cwd": "frontend"}}'

    # Research Agent Settings
    RESEARCH_MAX_SEARCH_RESULTS: int = 10
    RESEARCH_MAX_SOURCES: int = 5
    RESEARCH_MAX_SOURCE_SIZE_MB: int = 5
    RESEARCH_USER_AGENT: str = "PersonalAIOS/1.0"
    RESEARCH_MAX_REDIRECTS: int = 3
    RESEARCH_REQUEST_TIMEOUT_SECONDS: int = 15
    RESEARCH_MAX_EXTRACTED_CHARS: int = 20000
    RESEARCH_MAX_EVIDENCE_CHARS: int = 5000
    RESEARCH_MAX_TOTAL_CONTEXT_CHARS: int = 40000

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
