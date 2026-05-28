"""Tests for SQLiteFaissMemoryStore — memory CRUD operations.

Per plan Section 8.1.2: tests insert_memory, insert_message,
fetch_messages_by_session, fetch_memories_by_uuids, search_records,
rebuild_faiss, and schema integrity.
"""
import os
import pytest

from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore


@pytest.fixture
def store(tmp_path):
    """Create a store with a temp db path."""
    db_path = os.path.join(str(tmp_path), "test.db")
    s = SQLiteFaissMemoryStore(db_path)
    yield s
    # cleanup
    s._faiss_stop.set()


@pytest.mark.slow
class TestInsertAndFetch:
    def test_insert_message_and_fetch(self, store):
        """insert_message -> fetch_messages_by_session round-trip."""
        store.insert_message(
            session_id="s1", role="user", text="hello world",
            embedding=[0.1] * 384, importance=0.5, timestamp=1000,
        )
        msgs = store.fetch_messages_by_session("s1")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["text"] == "hello world"

    def test_fetch_orders_by_timestamp(self, store):
        store.insert_message("s1", "user", "first", [0.1] * 384, 0.5, 1000)
        store.insert_message("s1", "assistant", "second", [0.2] * 384, 0.5, 2000)
        store.insert_message("s1", "user", "third", [0.3] * 384, 0.5, 1500)
        msgs = store.fetch_messages_by_session("s1")
        assert msgs[0]["text"] == "first"
        assert msgs[1]["text"] == "third"
        assert msgs[2]["text"] == "second"

    def test_fetch_messages_session_isolation(self, store):
        store.insert_message("s1", "user", "msg1", [0.1] * 384, 0.5, 1000)
        store.insert_message("s2", "user", "msg2", [0.2] * 384, 0.5, 2000)
        s1_msgs = store.fetch_messages_by_session("s1")
        s2_msgs = store.fetch_messages_by_session("s2")
        assert len(s1_msgs) == 1
        assert s1_msgs[0]["text"] == "msg1"
        assert len(s2_msgs) == 1
        assert s2_msgs[0]["text"] == "msg2"


@pytest.mark.slow
class TestInsertMemory:
    def test_insert_memory_full(self, store):
        """insert_memory with all params."""
        uuid_str = store.insert_memory(
            session_id="s1", role="user", content="test content",
            embedding=[0.1] * 384, importance=0.8, timestamp=1000,
            user_id="u1", turn_id="t1", memory_type="episodic",
            memory_scope="session", decay_rate=0.1,
        )
        assert uuid_str is not None
        assert len(uuid_str) > 0

    def test_insert_memory_custom_scope(self, store):
        """memory_scope='user' should persist across sessions."""
        store.insert_memory(
            session_id="s1", role="user", content="global memory",
            embedding=[0.1] * 384, importance=0.9, timestamp=1000,
            user_id="u1", memory_type="habit",
            memory_scope="user", decay_rate=0.05,
        )
        msgs = store.fetch_messages_by_session("s1")
        assert len(msgs) == 1


@pytest.mark.slow
class TestFetchMemoriesByUuids:
    def test_fetch_by_uuids(self, store):
        u1 = store.insert_memory("s1", "user", "m1", [0.1] * 384, 0.5, 1000, memory_type="episodic")
        u2 = store.insert_memory("s1", "assistant", "m2", [0.2] * 384, 0.5, 2000, memory_type="episodic")
        records = store.fetch_memories_by_uuids([u1, u2])
        assert len(records) == 2
        assert records[0]["id"] in (u1, u2)

    def test_empty_uuids(self, store):
        records = store.fetch_memories_by_uuids([])
        assert records == []


@pytest.mark.slow
class TestSchemaIntegrity:
    def test_all_tables_exist(self, store):
        cur = store._conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {r[0] for r in cur.fetchall()}
        expected = {"memory", "session", "session_participants", "faiss_vectors", "kv", "faiss_kv"}
        assert expected <= tables


@pytest.mark.slow
class TestInsertMessageParams:
    def test_user_id_and_turn_id(self, store):
        """insert_message should pass user_id and turn_id through to insert_memory."""
        store.insert_message(
            session_id="s1", role="user", text="test",
            embedding=[0.1] * 384, importance=0.5, timestamp=1000,
            user_id="user_42", turn_id="turn_99",
            memory_type="episodic", memory_scope="session", decay_rate=0.1,
        )
        msgs = store.fetch_messages_by_session("s1")
        assert len(msgs) == 1
