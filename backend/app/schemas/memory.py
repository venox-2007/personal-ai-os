from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    memory_type: str = Field(..., pattern="^(FACT|PREFERENCE|GOAL|PROJECT|EPISODE)$")
    category: Optional[str] = Field(None, max_length=64)
    source: Optional[str] = Field("USER_EXPLICIT", max_length=64)
    importance: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    metadata_json: Optional[str] = None

class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    memory_type: Optional[str] = Field(None, pattern="^(FACT|PREFERENCE|GOAL|PROJECT|EPISODE)$")
    category: Optional[str] = Field(None, max_length=64)
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata_json: Optional[str] = None
    is_archived: Optional[bool] = None

class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    category: Optional[str]
    source: str
    importance: float
    confidence: float
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime]
    access_count: int
    is_archived: bool
    metadata_json: Optional[str]

    class Config:
        from_attributes = True

class MemoryListResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
