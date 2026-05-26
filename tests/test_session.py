"""Tests for LocalSession."""
from llmchatflow.core.session.local import LocalSession


class TestLocalSession:
    def test_init(self):
        s = LocalSession("test-session")
        assert s.session_id == "test-session"

    def test_get_context_empty(self):
        s = LocalSession("s1")
        assert s.get_context() == {}

    def test_update_context(self):
        s = LocalSession("s1")
        s.update_context("key", "value")
        assert s.get_context() == {"key": "value"}

    def test_update_context_overwrite(self):
        s = LocalSession("s1")
        s.update_context("key", "old")
        s.update_context("key", "new")
        assert s.get_context()["key"] == "new"

    def test_multiple_updates(self):
        s = LocalSession("s1")
        s.update_context("a", 1)
        s.update_context("b", 2)
        assert s.get_context() == {"a": 1, "b": 2}

    def test_load_noop(self):
        s = LocalSession("s1")
        s.load()  # should not raise

    def test_save_noop(self):
        s = LocalSession("s1")
        s.save()  # should not raise
