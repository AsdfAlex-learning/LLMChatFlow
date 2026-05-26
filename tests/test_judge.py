"""Tests for LLMJudge."""
from unittest.mock import MagicMock

import pytest

from llmchatflow.core.memory.judge import LLMJudge, FALLBACK_TYPE, FALLBACK_IMPORTANCE


@pytest.fixture
def mock_llm():
    return MagicMock()


class TestLLMJudgeInit:
    def test_with_client(self, mock_llm):
        j = LLMJudge(llm_client=mock_llm)
        assert j.llm_client is mock_llm
        assert j.enable_type_judge is True
        assert j.enable_importance_judge is True

    def test_without_client(self):
        j = LLMJudge()
        assert j.llm_client is None

    def test_disabled_flags(self):
        j = LLMJudge(enable_type_judge=False, enable_importance_judge=False)
        assert j.enable_type_judge is False
        assert j.enable_importance_judge is False


class TestLLMJudgeJudge:
    def test_both_disabled(self):
        j = LLMJudge(enable_type_judge=False, enable_importance_judge=False)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
        assert result["importance"] == FALLBACK_IMPORTANCE

    def test_no_llm_client(self):
        j = LLMJudge(llm_client=None)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
        assert result["importance"] == FALLBACK_IMPORTANCE

    def test_llm_success(self, mock_llm):
        mock_llm.chat_completion.return_value = '{"memory_type": "habit", "importance": 0.8, "reason": "test"}'
        j = LLMJudge(llm_client=mock_llm)
        result = j.judge("I always prefer dark mode")
        assert result["memory_type"] == "habit"
        assert result["importance"] == 0.8

    def test_llm_failure(self, mock_llm):
        mock_llm.chat_completion.side_effect = RuntimeError("API error")
        j = LLMJudge(llm_client=mock_llm)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
        assert result["importance"] == FALLBACK_IMPORTANCE

    def test_malformed_response(self, mock_llm):
        mock_llm.chat_completion.return_value = "not json"
        j = LLMJudge(llm_client=mock_llm)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
        assert result["importance"] == FALLBACK_IMPORTANCE

    def test_type_only(self, mock_llm):
        mock_llm.chat_completion.return_value = '{"memory_type": "summary", "importance": 0.9}'
        j = LLMJudge(llm_client=mock_llm, enable_importance_judge=False)
        result = j.judge("some text")
        assert result["memory_type"] == "summary"
        assert result["importance"] == FALLBACK_IMPORTANCE

    def test_importance_only(self, mock_llm):
        mock_llm.chat_completion.return_value = '{"memory_type": "habit", "importance": 0.3}'
        j = LLMJudge(llm_client=mock_llm, enable_type_judge=False)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
        assert result["importance"] == 0.3

    def test_importance_clamped(self, mock_llm):
        mock_llm.chat_completion.return_value = '{"memory_type": "episodic", "importance": 2.0}'
        j = LLMJudge(llm_client=mock_llm)
        result = j.judge("some text")
        assert result["importance"] <= 1.0

    def test_invalid_type_fallback(self, mock_llm):
        mock_llm.chat_completion.return_value = '{"memory_type": "invalid_type", "importance": 0.5}'
        j = LLMJudge(llm_client=mock_llm)
        result = j.judge("some text")
        assert result["memory_type"] == FALLBACK_TYPE
