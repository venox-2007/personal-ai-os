"""Database session and declarative base configuration."""

from typing import Generator, Optional
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("personal_ai_os")


class DatabaseCorruptionError(RuntimeError):
    """Raised when the SQLite database fails integrity checking or is corrupted."""
    pass


# Global integrity tracking state
_db_integrity_verified: bool = False
_db_corruption_error: Optional[str] = None

# Configure SQLite engine with thread check disabled for multi-threaded FastAPI workers
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.APP_DEBUG,
)


@event.listens_for(engine, "before_cursor_execute")
def _guard_against_corrupted_db_execution(conn, cursor, statement, parameters, context, executemany):
    """Blocks any SQL execution on the default engine if corruption has been detected."""
    if _db_corruption_error is not None:
        raise DatabaseCorruptionError(
            f"Database execution blocked to prevent data loss: {_db_corruption_error}"
        )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def is_database_corrupted() -> bool:
    """Returns True if the database failed integrity verification."""
    return _db_corruption_error is not None


def get_database_corruption_error() -> Optional[str]:
    """Returns the corruption diagnostic if database failed integrity verification, else None."""
    return _db_corruption_error


def reset_database_corruption_state() -> None:
    """Resets corruption tracking flags (used primarily in test fixtures)."""
    global _db_integrity_verified, _db_corruption_error
    _db_integrity_verified = False
    _db_corruption_error = None


def check_database_integrity(db_engine=None) -> str:
    """Runs PRAGMA integrity_check once or on demand on SQLite engines.

    Returns 'ok' if healthy.
    Raises DatabaseCorruptionError if corrupted or unreadable.
    Preserves existing files without altering, deleting, or repairing them.
    """
    target_engine = db_engine or engine
    if not str(target_engine.url).startswith("sqlite"):
        return "ok"

    try:
        with target_engine.connect() as conn:
            rows = conn.execute(text("PRAGMA integrity_check")).fetchall()
            messages = [r[0] for r in rows if r]
            if not messages or messages != ["ok"]:
                detail = "; ".join(messages) if messages else "Empty integrity response"
                raise DatabaseCorruptionError(
                    f"SQLite database integrity check failed ({detail}). "
                    "Application writes are blocked to preserve database file and prevent data loss."
                )
            return "ok"
    except DatabaseCorruptionError:
        raise
    except Exception as e:
        raise DatabaseCorruptionError(
            f"SQLite database is unreadable or malformed ({e}). "
            "Application writes are blocked to preserve database file and prevent data loss."
        ) from e


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    if _db_corruption_error is not None:
        raise DatabaseCorruptionError(
            f"Database session blocked: {_db_corruption_error}. "
            "All writes are halted to preserve existing database file."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(db_engine=None) -> None:
    """Initializes tables in database after verifying file integrity.

    Halts startup immediately if corruption is detected, preventing
    Base.metadata.create_all() or write routines from mutating a corrupt database.
    """
    global _db_integrity_verified, _db_corruption_error
    target_engine = db_engine or engine

    # Run integrity check before creating tables or writing metadata
    try:
        check_database_integrity(target_engine)
        if target_engine is engine:
            _db_integrity_verified = True
            _db_corruption_error = None
    except DatabaseCorruptionError as err:
        if target_engine is engine:
            _db_corruption_error = str(err)
        logger.critical(f"DATABASE CORRUPTION DETECTED: {err}")
        raise

    Base.metadata.create_all(bind=target_engine)
