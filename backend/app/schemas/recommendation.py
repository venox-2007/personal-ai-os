from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RecommendationResponse(BaseModel):
    id: str
    category: str
    title: str
    description: str
    reason: str
    priority: int
    status: str
    deduplication_key: str
    suggested_agent: Optional[str] = None
    suggested_workflow_goal: Optional[str] = None
    created_at: datetime
    due_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecommendationListResponse(BaseModel):
    items: List[RecommendationResponse]
    total: int
