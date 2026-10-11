"""Runtime path resolution for Personal AI OS.

Handles clean separation between:
1. Bundled read-only application resources (sys._MEIPASS when frozen).
2. Writable user data (%LOCALAPPDATA%\\PersonalAIOS when packaged, or ./ in development).
"""

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Returns True if running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Returns directory containing bundled application code and read-only resources."""
    if is_frozen():
        return Path(sys._MEIPASS).resolve()
    # In development: backend directory
    return Path(__file__).resolve().parent.parent.parent


def get_executable_dir() -> Path:
    """Returns directory containing the running executable or python script."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return get_bundle_dir()


def get_app_data_dir() -> Path:
    """Resolves stable user-writable application data directory.

    Priority:
    1. PERSONAL_AI_DATA_DIR environment variable (if explicitly configured)
    2. %LOCALAPPDATA%\\PersonalAIOS when packaged on Windows
    3. ~/.personal_ai_os when packaged on POSIX
    4. Current working directory / repo root in development mode
    """
    env_override = os.environ.get("PERSONAL_AI_DATA_DIR")
    if env_override:
        path = Path(env_override).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if is_frozen():
        if sys.platform == "win32":
            base_dir = os.environ.get("LOCALAPPDATA")
            if not base_dir:
                base_dir = str(Path.home() / "AppData" / "Local")
            app_data = Path(base_dir) / "PersonalAIOS"
        else:
            app_data = Path.home() / ".personal_ai_os"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data

    # Development mode: default to repository root / current directory
    return Path.cwd().resolve()


def get_default_database_url() -> str:
    """Returns appropriate SQLite database URL.

    Handles paths containing spaces safely with posix slash formatting.
    """
    env_db = os.environ.get("DATABASE_URL")
    if env_db:
        return env_db

    if is_frozen():
        data_dir = get_app_data_dir()
        db_file = data_dir / "personal_ai_os.db"
        # Format sqlite:///C:/Path With Spaces/personal_ai_os.db
        return f"sqlite:///{db_file.as_posix()}"

    # In development mode, maintain existing default
    return "sqlite:///./personal_ai_os.db"


def get_default_study_storage_dir() -> str:
    """Returns directory for ChromaDB and vector store persistence."""
    env_dir = os.environ.get("STUDY_STORAGE_DIR")
    if env_dir:
        return env_dir

    if is_frozen():
        study_dir = get_app_data_dir() / "study_data"
        study_dir.mkdir(parents=True, exist_ok=True)
        return str(study_dir)

    # In development mode, maintain existing default
    return "./study_data"
