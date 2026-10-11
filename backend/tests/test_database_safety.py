"""Tests for database integrity checking, corruption protection, and write prevention."""

import os
import tempfile
import sqlite3
import pytest
from sqlalchemy import create_engine, text
from app.database.session import (
    DatabaseCorruptionError,
    check_database_integrity,
    init_db,
    get_db,
    is_database_corrupted,
    get_database_corruption_error,
    reset_database_corruption_state,
)


@pytest.fixture(autouse=True)
def clean_corruption_state():
    """Ensure corruption flags are reset before and after each test."""
    reset_database_corruption_state()
    yield
    reset_database_corruption_state()


def test_integrity_check_valid_temporary_database():
    """Verifies that check_database_integrity passes on a clean SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create a valid sqlite db with a table and record
        conn = sqlite3.connect(tmp_path)
        conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, note TEXT);")
        conn.execute("INSERT INTO test_data (note) VALUES ('hello');")
        conn.commit()
        conn.close()

        test_engine = create_engine(f"sqlite:///{tmp_path}")
        result = check_database_integrity(test_engine)
        assert result == "ok"
    finally:
        test_engine.dispose()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_integrity_check_malformed_file_preserves_content_and_raises():
    """Verifies that an unreadable or non-database file raises DatabaseCorruptionError

    and is never deleted, overwritten, or repaired.
    """
    corrupt_bytes = b"Corrupted SQLite header and random garbage bytes 0123456789"
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(corrupt_bytes)
        tmp_path = tmp.name

    try:
        test_engine = create_engine(f"sqlite:///{tmp_path}")

        with pytest.raises(DatabaseCorruptionError) as exc_info:
            check_database_integrity(test_engine)

        assert "unreadable or malformed" in str(exc_info.value) or "integrity check failed" in str(exc_info.value)

        # File must still exist and its bytes must remain completely unmodified
        assert os.path.exists(tmp_path)
        with open(tmp_path, "rb") as f:
            current_bytes = f.read()
        assert current_bytes == corrupt_bytes
    finally:
        test_engine.dispose()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_init_db_halts_on_corrupt_database_without_writing():
    """Verifies that init_db aborts and halts before writing metadata to a corrupted database."""
    corrupt_bytes = b"NOT A VALID SQLITE DATABASE FILE AT ALL!"
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(corrupt_bytes)
        tmp_path = tmp.name

    try:
        test_engine = create_engine(f"sqlite:///{tmp_path}")

        with pytest.raises(DatabaseCorruptionError):
            init_db(test_engine)

        # Bytes remain intact - no table creation or repair was executed
        with open(tmp_path, "rb") as f:
            assert f.read() == corrupt_bytes
    finally:
        test_engine.dispose()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_get_db_blocks_when_corruption_flagged():
    """Verifies that get_db() dependency raises DatabaseCorruptionError if the database is flagged corrupt."""
    import app.database.session as session_module

    session_module._db_corruption_error = "Deliberate test corruption error"
    assert is_database_corrupted() is True
    assert get_database_corruption_error() == "Deliberate test corruption error"

    with pytest.raises(DatabaseCorruptionError) as exc_info:
        gen = get_db()
        next(gen)

    assert "Database session blocked" in str(exc_info.value)


@pytest.mark.asyncio
async def test_health_check_reports_degraded_when_database_is_corrupted():
    """Verifies that the health endpoint reports degraded status and corrupted database details."""
    import app.database.session as session_module
    from app.api.routes.health import get_health

    session_module._db_corruption_error = "Integrity check failed: Page 2 is corrupted"

    health = await get_health()
    assert health.status == "degraded"
    assert health.components["database"].status == "corrupted"
    assert "Integrity check failed: Page 2 is corrupted" in health.components["database"].details.get("error", "")
    assert "Writes are disabled" in health.components["database"].details.get("diagnostic", "")
