"""Tests for the FastAPI API server."""
import pytest
from fastapi.testclient import TestClient

from apps.api_server import app, RATE_LIMIT_MAX_REQUESTS


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Yield a TestClient with mocked heavy dependencies."""

    class MockSentenceEmbedding:
        def __init__(self, model_name=None, device=None):
            self.dim = 384

        def embed(self, text):
            return [0.1] * self.dim

    # Avoid loading real sentence-transformer models in lifespan
    import apps.api_server

    monkeypatch.setattr(apps.api_server, "SentenceEmbedding", MockSentenceEmbedding)

    # Redirect SQLite store to a temp path so tests are isolated
    from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore as RealStore

    temp_db = str(tmp_path / "api_test.db")
    monkeypatch.setattr(
        apps.api_server, "SQLiteFaissMemoryStore", lambda db_path, **kw: RealStore(temp_db, **kw)
    )

    with TestClient(app) as c:
        # Attach a MemoryManager so /retrieve returns structured dicts
        from llmchatflow.core.memory.manager import MemoryManager

        c.app.state.engine.memory_manager = MemoryManager(c.app.state.store, c.app.state.embedder)
        yield c


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestReady:
    def test_ready_all_checks_pass(self, client):
        client.app.state.ready_checks["openai_key"] = True
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_ready_openai_key_false(self, client):
        client.app.state.ready_checks["openai_key"] = False
        resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["detail"]["status"] == "not_ready"


class TestChat:
    def test_chat_empty_input(self, client):
        resp = client.post("/chat", json={"user_input": "", "session_id": "s1"})
        assert resp.status_code == 400

    def test_chat_no_api_key(self, client):
        client.app.state.ready_checks["openai_key"] = False
        resp = client.post("/chat", json={"user_input": "hello", "session_id": "s1"})
        assert resp.status_code == 503


class TestRetrieve:
    def test_retrieve_empty_input(self, client):
        resp = client.post("/retrieve", json={"user_input": "", "session_id": "s1"})
        assert resp.status_code == 400

    def test_retrieve_valid_input(self, client):
        resp = client.post("/retrieve", json={"user_input": "hello", "session_id": "s1"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "memories" in data
        assert "turns" in data
        assert "latency_ms" in data

    def test_retrieve_input_too_long(self, client):
        long_input = "x" * 10001
        resp = client.post("/retrieve", json={"user_input": long_input, "session_id": "s1"})
        assert resp.status_code == 422


class TestRateLimit:
    def test_rate_limit(self, client):
        client.app.state.ready_checks["openai_key"] = False
        for i in range(RATE_LIMIT_MAX_REQUESTS):
            resp = client.post("/chat", json={"user_input": f"req{i}", "session_id": "s1"})
            assert resp.status_code == 503, f"Request {i + 1} should be allowed"

        # 31st request should be rate limited
        resp = client.post("/chat", json={"user_input": "blocked", "session_id": "s1"})
        assert resp.status_code == 429
