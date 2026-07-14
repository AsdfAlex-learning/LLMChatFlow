"""Integration tests using real SQLite + FAISS stores with mocked heavy deps."""
import os
import time
from unittest.mock import MagicMock

import pytest

from llmchatflow.core.memory.manager import MemoryManager
from llmchatflow.core.session.local import LocalSession
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore


@pytest.fixture
def temp_store(tmp_path):
    db_path = os.path.join(str(tmp_path), "test_integration.db")
    store = SQLiteFaissMemoryStore(db_path, embedding_dim=384)
    yield store
    store.close()


@pytest.fixture
def mock_embedder():
    emb = MagicMock()
    emb.embed.return_value = [0.1] * 384
    return emb


def _wait_for_faiss(store, timeout=2.0):
    """Drain the async FAISS write queue before querying."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if store._faiss_queue.empty():
            time.sleep(0.1)
            return
        time.sleep(0.05)


@pytest.mark.slow
class TestFullWorkflow:
    def test_full_workflow_process(self, temp_store, mock_embedder):
        manager = MemoryManager(temp_store, mock_embedder)
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "mocked response"
        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = []

        engine = SemanticMemoryEngine(
            llm_client=mock_llm,
            context_builder=mock_ctx,
            store=temp_store,
            embedder=mock_embedder,
            memory_manager=manager,
            mode="full",
        )
        session = LocalSession("s1")
        result = engine.process("hello", session=session)
        assert result == "mocked response"

        _wait_for_faiss(temp_store)

        retrieval = engine.retrieve("hello", session=session)
        assert isinstance(retrieval, dict)
        assert "memories" in retrieval
        texts = [m["text"] for m in retrieval["memories"]]
        assert "hello" in texts

    def test_headless_retrieve_via_manager(self, temp_store, mock_embedder):
        manager = MemoryManager(temp_store, mock_embedder)
        manager.store("hello", "hi there", session_id="s1")
        _wait_for_faiss(temp_store)

        result = manager.retrieve("hello", session_id="s1")
        assert isinstance(result, dict)
        assert "memories" in result
        assert "turns" in result
        assert "latency_ms" in result
        texts = [m["text"] for m in result["memories"]]
        assert "hello" in texts

    def test_store_and_retrieve_roundtrip(self, temp_store, mock_embedder):
        manager = MemoryManager(temp_store, mock_embedder)
        manager.store("roundtrip input", "roundtrip output", session_id="s2")
        _wait_for_faiss(temp_store)

        result = manager.retrieve("roundtrip input", session_id="s2")
        texts = [m["text"] for m in result["memories"]]
        assert "roundtrip input" in texts

    def test_engine_process_with_session_parameter(self, temp_store, mock_embedder):
        mock_llm = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = []

        engine = SemanticMemoryEngine(
            llm_client=mock_llm,
            context_builder=mock_ctx,
            store=temp_store,
            embedder=mock_embedder,
            mode="headless",
        )
        session = LocalSession("test_session")
        result = engine.process("test", session=session)
        assert result == ""
