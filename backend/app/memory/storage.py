"""Working baseline implementations of the 5 memory facets."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.memory.base import (
    ConversationMemory,
    LongTermMemory,
    SemanticMemory,
    EpisodicMemory,
    PreferenceMemory,
    MemoryItem,
    EpisodeRecord,
)


class InMemoryConversationMemory(ConversationMemory):
    """In-memory implementation of conversation history."""

    def __init__(self) -> None:
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append({
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        messages = self._conversations.get(conversation_id, [])
        return messages[-limit:]

    async def clear(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)


class InMemoryLongTermMemory(LongTermMemory):
    """In-memory key-value fact store for user knowledge."""

    def __init__(self) -> None:
        self._facts: Dict[str, MemoryItem] = {}

    async def set_fact(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        item = MemoryItem(
            id=str(uuid.uuid4()),
            category="fact",
            key=key,
            content=value,
            metadata=metadata or {},
        )
        self._facts[key] = item

    async def get_fact(self, key: str) -> Optional[str]:
        item = self._facts.get(key)
        return item.content if item else None

    async def list_facts(self) -> List[MemoryItem]:
        return list(self._facts.values())


class InMemorySemanticMemory(SemanticMemory):
    """Keyword-based fallback for document retrieval before vector embedding engine is attached."""

    def __init__(self) -> None:
        self._chunks: List[MemoryItem] = []

    async def store_chunk(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        item = MemoryItem(
            id=str(uuid.uuid4()),
            category="semantic",
            key=doc_id,
            content=content,
            metadata=metadata or {},
        )
        self._chunks.append(item)

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        query_words = set(query.lower().split())
        scored: List[tuple[int, MemoryItem]] = []
        for chunk in self._chunks:
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            scored.append((overlap, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]


class InMemoryEpisodicMemory(EpisodicMemory):
    """Interaction history and episode recall."""

    def __init__(self) -> None:
        self._episodes: List[EpisodeRecord] = []

    async def record_episode(self, episode: EpisodeRecord) -> None:
        self._episodes.append(episode)

    async def recall_recent_episodes(self, limit: int = 10) -> List[EpisodeRecord]:
        return sorted(self._episodes, key=lambda e: e.timestamp, reverse=True)[:limit]


class InMemoryPreferenceMemory(PreferenceMemory):
    """User preferences and behavioral guidelines."""

    def __init__(self) -> None:
        self._preferences: Dict[str, Any] = {
            "tone": "concise, direct, professional",
            "operating_cost_target": "zero_cost_local",
            "default_agent": "orchestrator",
        }

    async def set_preference(self, key: str, value: Any) -> None:
        self._preferences[key] = value

    async def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.get(key, default)

    async def get_all_preferences(self) -> Dict[str, Any]:
        return self._preferences.copy()


class UnifiedMemoryManager:
    """Combines all 5 memory facets behind a cohesive interface."""

    def __init__(
        self,
        conversation: Optional[ConversationMemory] = None,
        long_term: Optional[LongTermMemory] = None,
        semantic: Optional[SemanticMemory] = None,
        episodic: Optional[EpisodicMemory] = None,
        preferences: Optional[PreferenceMemory] = None,
    ) -> None:
        self.conversation = conversation or InMemoryConversationMemory()
        self.long_term = long_term or InMemoryLongTermMemory()
        self.semantic = semantic or InMemorySemanticMemory()
        self.episodic = episodic or InMemoryEpisodicMemory()
        self.preferences = preferences or InMemoryPreferenceMemory()

    async def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on stored memory items."""
        facts = await self.long_term.list_facts()
        episodes = await self.episodic.recall_recent_episodes()
        prefs = await self.preferences.get_all_preferences()
        return {
            "facts_count": len(facts),
            "episodes_count": len(episodes),
            "preferences_count": len(prefs),
        }


# Global default instance
memory_manager = UnifiedMemoryManager()
