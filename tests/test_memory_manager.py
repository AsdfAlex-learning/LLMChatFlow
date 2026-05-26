"""Tests for MemoryManager."""
from unittest.mock import MagicMock, call

import pytest

from llmchatflow.core.memory.manager import MemoryManager
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
def manager(mock_store, mock_embedder):
    return MemoryManager(mock_store, mock_embedder)


class TestMemoryManagerInit:
    def test_default_policy(self, mock_store, mock_embedder):
        m = MemoryManager(mock_store, mock_embedder)
        assert isinstance(m.policy, DefaultMemoryPolicy)

    def test_custom_policy(self, mock_store, mock_embedder):
        policy = MagicMock()
        m = MemoryManager(mock_store, mock_embedder, policy=policy)
        assert m.policy is policy

    def test_creates_retriever(self, manager):
        assert manager.retriever is not None

    def test_creates_view_builder(self, manager):
        assert manager.view_builder is not None


class TestMemoryManagerRetrieve:
    def test_delegates_to_retriever(self, manager):
        manager.retriever.retrieve = MagicMock(return_value={"memories": [], "turns": [], "latency_ms": 0})
        result = manager.retrieve("hello", session_id="s1")
        manager.retriever.retrieve.assert_called_once()
        assert "memories" in result


class TestMemoryManagerBuildView:
    def test_delegates_to_view_builder(self, manager):
        manager.view_builder.build_view = MagicMock(return_value={"memories": [], "turns": []})
        retrieval = {"memories": [], "turns": []}
        result = manager.build_view(retrieval, format="structured")
        manager.view_builder.build_view.assert_called_once()


class TestMemoryManagerStore:
    def test_stores_user_and_assistant(self, mock_store, mock_embedder):
        mgr = MemoryManager(mock_store, mock_embedder)
        mgr.store("hello", "hi there", session_id="s1")
        assert mock_store.insert_message.call_count == 2

    def test_stores_with_no_response(self, mock_store, mock_embedder):
        mgr = MemoryManager(mock_store, mock_embedder)
        mgr.store("hello", "", session_id="s1")
        assert mock_store.insert_message.call_count == 1

    def test_uses_config_importance(self, mock_store, mock_embedder):
        mgr = MemoryManager(mock_store, mock_embedder)
        config = MagicMock()
        config.importance_default = 0.9
        mgr.store("hello", "hi", session_id="s1", config=config)
        for c in mock_store.insert_message.call_args_list:
            kw = c.kwargs
            assert kw.get("importance") == 0.9
