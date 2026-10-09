import pytest
from app.services.memory_service import memory_service, MemoryValidationError, MemoryNotFoundError
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.database.session import SessionLocal
from app.models.entities import MemoryModel

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        # clear memories before test
        db.query(MemoryModel).delete()
        db.commit()
        yield db
    finally:
        db.query(MemoryModel).delete()
        db.commit()
        db.close()

def test_create_valid_memory(db):
    req = MemoryCreate(content="User likes python", memory_type="PREFERENCE")
    mem = memory_service.create_memory(db, req)
    assert mem.content == "User likes python"
    assert mem.memory_type == "PREFERENCE"
    assert mem.id is not None
    assert mem.importance == 0.5
    assert mem.access_count == 0

def test_reject_empty_oversized(db):
    with pytest.raises(MemoryValidationError):
        memory_service.create_memory(db, MemoryCreate(content="   ", memory_type="FACT"))
    
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MemoryCreate(content="A" * 10001, memory_type="FACT")

def test_secret_pattern_rejection(db):
    with pytest.raises(MemoryValidationError, match="potential secrets"):
        memory_service.create_memory(db, MemoryCreate(content="My AWS key is AKIAIOSFODNN7EXAMPLE", memory_type="FACT"))
        
    with pytest.raises(MemoryValidationError, match="potential secrets"):
        memory_service.create_memory(db, MemoryCreate(content="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", memory_type="FACT"))

def test_duplicate_prevention(db):
    req = MemoryCreate(content="User likes python", memory_type="PREFERENCE")
    mem1 = memory_service.create_memory(db, req)
    
    req2 = MemoryCreate(content="User   likes   python", memory_type="PREFERENCE")
    mem2 = memory_service.create_memory(db, req2)
    
    assert mem1.id == mem2.id

def test_get_list_filter_search(db):
    m1 = memory_service.create_memory(db, MemoryCreate(content="Fact 1", memory_type="FACT", category="TEST"))
    m2 = memory_service.create_memory(db, MemoryCreate(content="Pref 1", memory_type="PREFERENCE", category="TEST"))
    m3 = memory_service.create_memory(db, MemoryCreate(content="Archived fact", memory_type="FACT", category="ARCHIVED"))
    memory_service.archive_memory(db, m3.id)
    
    memories, total = memory_service.list_memories(db)
    assert total == 2
    
    memories, total = memory_service.list_memories(db, memory_type="FACT")
    assert total == 1
    assert memories[0].id == m1.id
    
    results = memory_service.search_memories(db, "Fact")
    assert len(results) == 1
    assert results[0].id == m1.id
    
    results_with_archived = memory_service.search_memories(db, "Fact", include_archived=True)
    assert len(results_with_archived) == 2

def test_update_preserves_id_and_created_at(db):
    m1 = memory_service.create_memory(db, MemoryCreate(content="Initial", memory_type="FACT"))
    orig_id = m1.id
    orig_created = m1.created_at
    
    m2 = memory_service.update_memory(db, m1.id, MemoryUpdate(content="Updated"))
    assert m2.id == orig_id
    assert m2.created_at == orig_created
    assert m2.content == "Updated"

def test_delete(db):
    m1 = memory_service.create_memory(db, MemoryCreate(content="Delete me", memory_type="FACT"))
    memory_service.delete_memory(db, m1.id)
    with pytest.raises(MemoryNotFoundError):
        memory_service.get_memory(db, m1.id)

def test_archive_restore(db):
    m1 = memory_service.create_memory(db, MemoryCreate(content="Archive me", memory_type="FACT"))
    memory_service.archive_memory(db, m1.id)
    
    memories, total = memory_service.list_memories(db)
    assert total == 0
    
    memory_service.restore_memory(db, m1.id)
    memories, total = memory_service.list_memories(db)
    assert total == 1

def test_access_tracking(db):
    m1 = memory_service.create_memory(db, MemoryCreate(content="Track me", memory_type="FACT"))
    assert m1.access_count == 0
    assert m1.last_accessed_at is None
    
    m2 = memory_service.record_memory_access(db, m1.id)
    assert m2.access_count == 1
    assert m2.last_accessed_at is not None

def test_missing_ids(db):
    with pytest.raises(MemoryNotFoundError):
        memory_service.get_memory(db, "invalid_id")
        
    with pytest.raises(MemoryNotFoundError):
        memory_service.update_memory(db, "invalid_id", MemoryUpdate(content="x"))
