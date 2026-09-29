"""Tests for memory abstractions and storage."""

import pytest
from app.memory.storage import (
    InMemoryConversationMemory,
    InMemoryLongTermMemory,
    InMemorySemanticMemory,
    InMemoryEpisodicMemory,
    InMemoryPreferenceMemory,
    UnifiedMemoryManager,
)
from app.memory.base import EpisodeRecord


@pytest.mark.asyncio
async def test_conversation_memory():
    mem = InMemoryConversationMemory()
    await mem.add_message("conv_1", "user", "Hello")
    await mem.add_message("conv_1", "assistant", "Hi there")

    msgs = await mem.get_messages("conv_1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "Hello"
    assert msgs[1]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_long_term_memory():
    mem = InMemoryLongTermMemory()
    await mem.set_fact("preferred_name", "Alex")
    val = await mem.get_fact("preferred_name")
    assert val == "Alex"

    facts = await mem.list_facts()
    assert len(facts) == 1


@pytest.mark.asyncio
async def test_semantic_memory_search():
    mem = InMemorySemanticMemory()
    await mem.store_chunk("doc1", "Python async programming with FastAPI and Uvicorn")
    await mem.store_chunk("doc2", "React Vite frontend layout with Tailwind CSS")

    results = await mem.search("FastAPI programming")
    assert len(results) > 0
    assert "FastAPI" in results[0].content


@pytest.mark.asyncio
async def test_episodic_memory():
    mem = InMemoryEpisodicMemory()
    ep = EpisodeRecord(
        id="ep_1",
        task_summary="Configured local Ollama LLM provider",
        agents_involved=["Orchestrator"],
        outcome="Successful connection test",
    )
    await mem.record_episode(ep)
    episodes = await mem.recall_recent_episodes()
    assert len(episodes) == 1
    assert episodes[0].task_summary == "Configured local Ollama LLM provider"


@pytest.mark.asyncio
async def test_unified_memory_manager():
    manager = UnifiedMemoryManager()
    stats = await manager.get_stats()
    assert "facts_count" in stats
    assert "episodes_count" in stats
    assert "preferences_count" in stats
