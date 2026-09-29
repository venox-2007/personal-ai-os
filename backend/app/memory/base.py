"""Memory abstractions for Personal AI OS."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """Generic memory record with metadata."""

    id: str
    category: str
    key: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EpisodeRecord(BaseModel):
    """Episodic memory representing a past interaction or milestone."""

    id: str
    task_summary: str
    agents_involved: List[str]
    outcome: str
    learnings: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMemory(ABC):
    """Short-term conversational context memory."""

    @abstractmethod
    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        pass

    @abstractmethod
    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def clear(self, conversation_id: str) -> None:
        pass


class LongTermMemory(ABC):
    """User facts, persistent profile information, and accumulated knowledge."""

    @abstractmethod
    async def set_fact(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    async def get_fact(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def list_facts(self) -> List[MemoryItem]:
        pass


class SemanticMemory(ABC):
    """Document, notes, and semantic chunk retrieval abstraction."""

    @abstractmethod
    async def store_chunk(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        pass


class EpisodicMemory(ABC):
    """Interaction history and past problem-solving episodes."""

    @abstractmethod
    async def record_episode(self, episode: EpisodeRecord) -> None:
        pass

    @abstractmethod
    async def recall_recent_episodes(self, limit: int = 10) -> List[EpisodeRecord]:
        pass


class PreferenceMemory(ABC):
    """User preferences, system constraints, and customized instructions."""

    @abstractmethod
    async def set_preference(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def get_preference(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    async def get_all_preferences(self) -> Dict[str, Any]:
        pass
