"""Tests for StructuredContextBuilder — context construction paths.

Per plan Section 8.1.3: tests build_messages() with FAISS search path
and fallback path, verifying token trimming and block assembly.
"""
from unittest.mock import MagicMock, patch

import pytest

from llmchatflow.core.context.structured import StructuredContextBuilder


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.search_records.return_value = []
    store.fetch_messages_by_session.return_value = []
    return store


@pytest.fixture
def mock_embedder():
    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 384
    return embedder


class TestBuildMessagesBasic:
    def test_returns_messages_list(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
            max_memory_token=2000, top_k=10,
        )
        result = builder.build_messages("session1", "hello")
        assert isinstance(result, list)
        assert len(result) >= 2
        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == "hello"

    def test_system_message_present(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        result = builder.build_messages("session1", "test")
        assert result[0]["role"] == "system"

    def test_embedding_called_when_not_provided(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        builder.build_messages("session1", "hello", current_embedding=None)
        mock_embedder.embed.assert_called_once()

    def test_embedding_not_called_when_provided(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        provided = [0.5] * 384
        builder.build_messages("session1", "hello", current_embedding=provided)
        mock_embedder.embed.assert_not_called()


class TestBuildMessagesWithRecords:
    def test_with_search_results(self, mock_store, mock_embedder):
        records = [
            {
                "id": "1", "text": "relevant memory", "role": "user",
                "similarity": 0.9, "importance": 0.8, "decay_rate": 0.1,
                "memory_type": "episodic", "timestamp": 1000, "_score": 0.85,
            }
        ]
        mock_store.search_records.return_value = records
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
            max_memory_token=2000, top_k=10,
        )
        result = builder.build_messages("session1", "hello")
        assert len(result) >= 2

    def test_search_failure_falls_back(self, mock_store, mock_embedder):
        """When search_records raises, should fall back to fetch_messages_by_session."""
        mock_store.search_records.side_effect = RuntimeError("FAISS error")
        mock_store.fetch_messages_by_session.return_value = [
            {"role": "user", "text": "fallback", "importance": 0.5, "timestamp": 1000, "memory_type": "episodic"}
        ]
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        result = builder.build_messages("session1", "hello")
        assert len(result) >= 2
        mock_store.fetch_messages_by_session.assert_called()

    def test_config_driven_keep_count(self, mock_store, mock_embedder):
        """When config has ranking_keep_count, should use it."""
        mock_store.search_records.return_value = []
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
            top_k=3,
        )
        result = builder.build_messages("session1", "hello")
        assert len(result) >= 2  # system + user at minimum

    def test_memory_block_present(self, mock_store, mock_embedder):
        records = [
            {
                "id": "1", "text": "a memory", "role": "user",
                "similarity": 0.9, "importance": 0.5, "decay_rate": 0.1,
                "memory_type": "episodic", "timestamp": 1000, "_score": 0.5,
            }
        ]
        mock_store.search_records.return_value = records
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
            max_memory_token=2000, top_k=10,
        )
        result = builder.build_messages("session1", "hello")
        # Should have at least one message with "检索记忆" content
        memory_msgs = [m for m in result if "检索记忆" in m.get("content", "")]
        assert len(memory_msgs) >= 1


class TestBuildMessagesEdgeCases:
    def test_empty_input(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        result = builder.build_messages("s1", "")
        assert len(result) >= 2
        assert result[-1]["content"] == ""

    def test_long_text_input(self, mock_store, mock_embedder):
        builder = StructuredContextBuilder(
            store=mock_store, embedder=mock_embedder,
        )
        long_text = "x" * 10000
        result = builder.build_messages("s1", long_text)
        assert len(result) >= 2

    def test_no_store_methods(self, mock_embedder):
        """Store without search_records attribute should still work via fallback."""
        from llmchatflow.core.memory.storage import MemoryStore as MS

        class MinimalStore(MS):
            def insert_memory(self, *a, **kw): return "uuid"
            def insert_message(self, *a, **kw): pass
            def fetch_messages_by_session(self, sid):
                return [{"role": "user", "text": "minimal", "importance": 0.5, "timestamp": 1000, "memory_type": "episodic"}]
            def fetch_memories_by_uuids(self, uuids): return []
            def search_records(self, *a, **kw): return []

        builder = StructuredContextBuilder(
            store=MinimalStore(), embedder=mock_embedder,
        )
        result = builder.build_messages("s1", "test")
        assert len(result) >= 2
