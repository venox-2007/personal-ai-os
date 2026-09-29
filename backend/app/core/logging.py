"""Logging configuration for Personal AI OS."""

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configures and returns the application root logger."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("personal_ai_os")


logger = setup_logging()
