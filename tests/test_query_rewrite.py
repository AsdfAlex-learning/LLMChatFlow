"""Tests for QueryRewriter."""
from unittest.mock import MagicMock

import pytest

from llmchatflow.core.workflow.query_rewrite import QueryRewriter


@pytest.fixture
def mock_llm():
    return MagicMock()


class TestQueryRewriterInit:
    def test_defaults(self):
        r = QueryRewriter()
        assert r.trigger == "none"
        assert r.llm_client is None


class TestShouldRewrite:
    def test_trigger_none(self):
        r = QueryRewriter(trigger="none")
        assert r.should_rewrite() is False

    def test_trigger_always(self):
        r = QueryRewriter(trigger="always")
        assert r.should_rewrite() is True

    def test_trigger_timed_elapsed(self):
        r = QueryRewriter(trigger="timed", interval_seconds=0)
        r._last_rewrite_time = 0
        assert r.should_rewrite() is True

    def test_trigger_count(self):
        r = QueryRewriter(trigger="count", interval_turns=2)
        assert r.should_rewrite() is False  # count=1, not divisible by 2
        assert r.should_rewrite() is True   # count=2, divisible by 2


class TestRewrite:
    def test_no_rewrite_trigger(self):
        r = QueryRewriter(trigger="none")
        assert r.rewrite("hello") == "hello"

    def test_no_llm_client(self):
        r = QueryRewriter(trigger="always", llm_client=None)
        assert r.rewrite("hello") == "hello"

    def test_successful_rewrite(self, mock_llm):
        mock_llm.chat_completion.return_value = "clear query"
        r = QueryRewriter(trigger="always", llm_client=mock_llm)
        result = r.rewrite("hello")
        assert result == "clear query"

    def test_llm_failure(self, mock_llm):
        mock_llm.chat_completion.side_effect = RuntimeError("API down")
        r = QueryRewriter(trigger="always", llm_client=mock_llm)
        result = r.rewrite("hello")
        assert result == "hello"
