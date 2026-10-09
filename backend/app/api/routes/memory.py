from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemoryListResponse
from app.services.memory_service import memory_service, MemoryValidationError, MemoryNotFoundError

router = APIRouter(prefix="/memory", tags=["Memory"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Keeping stats endpoint for backward compatibility if needed
@router.get("/stats", response_model=Dict[str, Any])
async def get_memory_stats() -> Dict[str, Any]:
    return {"status": "ok", "message": "Memory stats integrated"}

@router.get("/search", response_model=List[MemoryResponse])
def search_memories(
    q: str = Query(..., min_length=1, description="Search query"),
    include_archived: bool = Query(False, description="Include archived memories"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    items = memory_service.search_memories(db, q, include_archived, limit)
    return items

@router.post("", response_model=MemoryResponse)
def create_memory(req: MemoryCreate, db: Session = Depends(get_db)):
    try:
        return memory_service.create_memory(db, req)
    except MemoryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=MemoryListResponse)
def list_memories(
    memory_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    items, total = memory_service.list_memories(db, memory_type, category, include_archived, limit, skip)
    return MemoryListResponse(items=items, total=total)

@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str = Path(...), db: Session = Depends(get_db)):
    try:
        mem = memory_service.record_memory_access(db, memory_id)
        return mem
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{memory_id}", response_model=MemoryResponse)
def update_memory(memory_id: str, req: MemoryUpdate, db: Session = Depends(get_db)):
    try:
        return memory_service.update_memory(db, memory_id, req)
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MemoryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    try:
        memory_service.delete_memory(db, memory_id)
        return {"success": True}
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{memory_id}/archive", response_model=MemoryResponse)
def archive_memory(memory_id: str, db: Session = Depends(get_db)):
    try:
        return memory_service.archive_memory(db, memory_id)
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{memory_id}/restore", response_model=MemoryResponse)
def restore_memory(memory_id: str, db: Session = Depends(get_db)):
    try:
        return memory_service.restore_memory(db, memory_id)
    except MemoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
