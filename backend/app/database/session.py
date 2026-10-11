"""Database session and declarative base configuration."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Configure SQLite engine with thread check disabled for multi-threaded FastAPI workers
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.APP_DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initializes tables in database and verifies file integrity."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA integrity_check")).fetchone()
            status = result[0] if result else "unknown"
            if status != "ok":
                import logging
                logging.getLogger("personal_ai_os").warning(f"SQLite PRAGMA integrity_check warning: {status}")
    except Exception as e:
        import logging
        logging.getLogger("personal_ai_os").warning(f"Could not verify database integrity PRAGMA: {e}")

    Base.metadata.create_all(bind=engine)
