import re
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.models.entities import MemoryModel
from app.schemas.memory import MemoryCreate, MemoryUpdate
import logging

logger = logging.getLogger(__name__)

def utc_now():
    return datetime.now(timezone.utc)

class MemoryServiceError(Exception):
    pass

class MemoryValidationError(MemoryServiceError):
    pass

class MemoryNotFoundError(MemoryServiceError):
    pass

class MemoryService:
    SECRET_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE),  # General secret keys (e.g. OpenAI)
        re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),    # AWS Access Key
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{32,}", re.IGNORECASE), # Bearer tokens
        re.compile(r"gh[p|a|s|r]_[a-zA-Z0-9]{36}", re.IGNORECASE), # GitHub tokens
    ]

    def _normalize_content(self, content: str) -> str:
        # Normalize whitespace
        return " ".join(content.split())
        
    def _contains_secrets(self, content: str) -> bool:
        for pattern in self.SECRET_PATTERNS:
            if pattern.search(content):
                return True
        return False

    def create_memory(self, db: Session, req: MemoryCreate) -> MemoryModel:
        if not req.content or not req.content.strip():
            raise MemoryValidationError("Memory content cannot be empty.")
            
        normalized = self._normalize_content(req.content)
        
        if len(normalized) > 10000:
            raise MemoryValidationError("Memory content exceeds maximum length.")
            
        if self._contains_secrets(normalized):
            raise MemoryValidationError("Memory content rejected: Contains potential secrets or credentials.")
            
        # Check for exact duplicate (active)
        existing = db.query(MemoryModel).filter(
            MemoryModel.content == normalized,
            MemoryModel.memory_type == req.memory_type,
            MemoryModel.is_archived == False
        ).first()
        
        if existing:
            return existing
            
        mem = MemoryModel(
            content=normalized,
            memory_type=req.memory_type,
            category=req.category,
            source=req.source,
            importance=req.importance,
            confidence=req.confidence,
            metadata_json=req.metadata_json
        )
        db.add(mem)
        try:
            db.commit()
            db.refresh(mem)
        except Exception as e:
            db.rollback()
            logger.error(f"DB Error creating memory: {e}")
            raise MemoryServiceError("Failed to create memory due to internal error.")
        return mem

    def get_memory(self, db: Session, memory_id: str) -> MemoryModel:
        mem = db.query(MemoryModel).filter(MemoryModel.id == memory_id).first()
        if not mem:
            raise MemoryNotFoundError("Memory not found.")
        return mem

    def update_memory(self, db: Session, memory_id: str, req: MemoryUpdate) -> MemoryModel:
        mem = self.get_memory(db, memory_id)
        
        if req.content is not None:
            if not req.content.strip():
                raise MemoryValidationError("Memory content cannot be empty.")
            normalized = self._normalize_content(req.content)
            if self._contains_secrets(normalized):
                raise MemoryValidationError("Memory content rejected: Contains potential secrets or credentials.")
            mem.content = normalized
            
        if req.memory_type is not None:
            mem.memory_type = req.memory_type
        if req.category is not None:
            mem.category = req.category
        if req.importance is not None:
            mem.importance = req.importance
        if req.confidence is not None:
            mem.confidence = req.confidence
        if req.metadata_json is not None:
            mem.metadata_json = req.metadata_json
        if req.is_archived is not None:
            mem.is_archived = req.is_archived
            
        try:
            db.commit()
            db.refresh(mem)
        except Exception as e:
            db.rollback()
            logger.error(f"DB Error updating memory: {e}")
            raise MemoryServiceError("Failed to update memory due to internal error.")
            
        return mem

    def delete_memory(self, db: Session, memory_id: str):
        mem = self.get_memory(db, memory_id)
        try:
            db.delete(mem)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB Error deleting memory: {e}")
            raise MemoryServiceError("Failed to delete memory due to internal error.")

    def archive_memory(self, db: Session, memory_id: str) -> MemoryModel:
        return self.update_memory(db, memory_id, MemoryUpdate(is_archived=True))

    def restore_memory(self, db: Session, memory_id: str) -> MemoryModel:
        return self.update_memory(db, memory_id, MemoryUpdate(is_archived=False))
        
    def record_memory_access(self, db: Session, memory_id: str) -> MemoryModel:
        mem = self.get_memory(db, memory_id)
        mem.access_count += 1
        mem.last_accessed_at = utc_now()
        try:
            db.commit()
            db.refresh(mem)
        except Exception as e:
            db.rollback()
            logger.error(f"DB Error recording access: {e}")
            # Non-critical, do not raise
        return mem

    def list_memories(self, db: Session, memory_type: Optional[str] = None, category: Optional[str] = None, include_archived: bool = False, limit: int = 100, skip: int = 0) -> Tuple[List[MemoryModel], int]:
        q = db.query(MemoryModel)
        
        if not include_archived:
            q = q.filter(MemoryModel.is_archived == False)
            
        if memory_type:
            q = q.filter(MemoryModel.memory_type == memory_type)
        if category:
            q = q.filter(MemoryModel.category == category)
            
        total = q.count()
        items = q.order_by(desc(MemoryModel.created_at)).offset(skip).limit(min(limit, 500)).all()
        return items, total

    def search_memories(self, db: Session, query: str, include_archived: bool = False, limit: int = 50) -> List[MemoryModel]:
        if not query or not query.strip():
            return []
            
        query = query.strip()
        if len(query) > 200:
            query = query[:200]
            
        q = db.query(MemoryModel)
        if not include_archived:
            q = q.filter(MemoryModel.is_archived == False)
            
        search_term = f"%{query}%"
        q = q.filter(or_(
            MemoryModel.content.ilike(search_term),
            MemoryModel.category.ilike(search_term)
        ))
        
        return q.order_by(desc(MemoryModel.importance), desc(MemoryModel.created_at)).limit(min(limit, 100)).all()

    def retrieve_relevant_memories(self, db: Session, query: str, limit: int = 5) -> List[MemoryModel]:
        if not query or not query.strip():
            return []
            
        query = query.strip().lower()
        if len(query) > 500:
            query = query[:500]
            
        # Tokenize query for meaningful words (length > 3)
        tokens = [t for t in re.split(r'\W+', query) if len(t) > 3]
        
        q = db.query(MemoryModel).filter(MemoryModel.is_archived == False)
        
        # If we have tokens, filter DB to only load potentially relevant ones to save memory
        if tokens:
            filters = [MemoryModel.content.ilike(f"%{query}%")] # Exact phrase match
            for t in tokens[:10]: # Max 10 tokens to prevent huge SQL
                filters.append(MemoryModel.content.ilike(f"%{t}%"))
                filters.append(MemoryModel.category.ilike(f"%{t}%"))
            q = q.filter(or_(*filters))
            
        memories = q.all()
        
        scored_memories = []
        now = utc_now()
        
        for mem in memories:
            score = 0.0
            content_lower = mem.content.lower()
            category_lower = mem.category.lower() if mem.category else ""
            
            # Exact phrase match
            if query in content_lower:
                score += 5.0
                
            # Token overlap
            overlap_count = 0
            for t in tokens:
                if t in content_lower:
                    overlap_count += 1
                if category_lower and t in category_lower:
                    overlap_count += 1.5
                    
            if overlap_count > 0:
                score += overlap_count
                
            # Base importance
            score += mem.importance * 2.0
            
            # Recency tie-breaker (max 0.5 points for very recent)
            mem_dt = mem.created_at
            if mem_dt.tzinfo is None:
                mem_dt = mem_dt.replace(tzinfo=timezone.utc)
            
            age_days = (now - mem_dt).total_seconds() / 86400.0
            recency_bonus = max(0.0, 0.5 - (age_days * 0.01))
            score += recency_bonus
            
            # Only include if there's actual lexical relevance (overlap > 0 or exact match)
            if query in content_lower or overlap_count > 0:
                scored_memories.append((score, mem))
                
        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [m for score, m in scored_memories[:limit]]

memory_service = MemoryService()
