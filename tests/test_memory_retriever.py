"""Tests for MemoryRetriever."""
from unittest.mock import MagicMock, PropertyMock

import pytest

from llmchatflow.core.memory.retriever import MemoryRetriever
from llmchatflow.core.memory.policy.default import DefaultMemoryPolicy


@pytest.fixture
def mock_store():
    return MagicMock()


@pytest.fixture
def mock_embedder():
    emb = MagicMock()
    emb.embed.return_value = [0.1] * 384
    return emb


@pytest.fixture
def mock_policy():
    policy = MagicMock()
    policy.select.return_value = [
        {"role": "user", "text": "hello", "memory_type": "episodic", "timestamp": 1000, "turn_id": "t1", "_score": 0.9},
    ]
    return policy


@pytest.fixture
def retriever(mock_store, mock_embedder, mock_policy):
    return MemoryRetriever(mock_store, mock_embedder, mock_policy)


class TestMemoryRetrieverInit:
    def test_default_policy(self, mock_store, mock_embedder):
        r = MemoryRetriever(mock_store, mock_embedder)
        assert isinstance(r.policy, DefaultMemoryPolicy)

    def test_custom_policy(self, mock_store, mock_embedder, mock_policy):
        r = MemoryRetriever(mock_store, mock_embedder, mock_policy)
        assert r.policy is mock_policy


class TestMemoryRetrieverRetrieve:
    def test_happy_path(self, retriever, mock_store, mock_embedder, mock_policy):
        mock_store.search_records.return_value = [
            {"uuid": "1", "role": "user", "text": "hello", "memory_type": "episodic",
             "timestamp": 1000, "turn_id": "t1", "similarity": 0.9},
        ]
        result = retriever.retrieve("hello", session_id="s1")
        assert "memories" in result
        assert "turns" in result
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], int)

    def test_embedding_failure(self, retriever, mock_embedder, mock_store):
        # embed() now returns None on failure instead of raising
        mock_embedder.embed.return_value = None
        mock_store.search_records.return_value = []
        mock_store.fetch_messages_by_session.return_value = []
        result = retriever.retrieve("hello", session_id="s1")
        assert result["memories"] == [] or isinstance(result["memories"], list)

    def test_faiss_failure_fallback(self, retriever, mock_store, mock_policy):
        mock_store.search_records.side_effect = RuntimeError("FAISS down")
        mock_store.fetch_messages_by_session.return_value = [
            {"role": "user", "text": "hello", "memory_type": "episodic",
             "timestamp": 1000, "embedding": [0.1] * 384},
        ]
        result = retriever.retrieve("hello", session_id="s1")
        assert isinstance(result["memories"], list)

    def test_empty_results(self, mock_store, mock_embedder):
        mock_store.search_records.return_value = []
        mock_store.fetch_messages_by_session.return_value = []
        empty_policy = MagicMock()
        empty_policy.select.return_value = []
        r = MemoryRetriever(mock_store, mock_embedder, empty_policy)
        result = r.retrieve("hello", session_id="s1")
        assert result["memories"] == []

    def test_returns_dict_shape(self, retriever, mock_store):
        mock_store.search_records.return_value = []
        result = retriever.retrieve("hello", session_id="s1")
        assert set(result.keys()) == {"memories", "turns", "latency_ms"}


class TestGroupByTurn:
    def test_grouping(self, retriever):
        memories = [
            {"role": "user", "text": "hi", "turn_id": "t1", "timestamp": 1000},
            {"role": "assistant", "text": "hello", "turn_id": "t1", "timestamp": 1001},
            {"role": "user", "text": "bye", "turn_id": "t2", "timestamp": 2000},
        ]
        turns = retriever._group_by_turn(memories)
        assert len(turns) == 2
        assert len(turns[0]) == 2  # t1 has 2 messages
        assert len(turns[1]) == 1  # t2 has 1 message

    def test_empty_memories(self, retriever):
        turns = retriever._group_by_turn([])
        assert turns == []

    def test_role_ordering(self, retriever):
        memories = [
            {"role": "assistant", "text": "hello", "turn_id": "t1", "timestamp": 1001},
            {"role": "user", "text": "hi", "turn_id": "t1", "timestamp": 1000},
        ]
        turns = retriever._group_by_turn(memories)
        assert turns[0][0]["role"] == "user"
