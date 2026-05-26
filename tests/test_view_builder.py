"""Tests for MemoryViewBuilder."""
from unittest.mock import patch

import pytest

from llmchatflow.core.memory.view_builder import MemoryViewBuilder


@pytest.fixture
def builder():
    return MemoryViewBuilder(model="gpt-3.5-turbo", max_tokens=2000)


@pytest.fixture
def sample_result():
    return {
        "memories": [
            {"id": "1", "uuid": "1", "role": "user", "text": "hello",
             "memory_type": "episodic", "importance": 0.7, "timestamp": 1000, "_score": 0.9},
            {"id": "2", "uuid": "2", "role": "assistant", "text": "hi there",
             "memory_type": "episodic", "importance": 0.5, "timestamp": 1001, "_score": 0.8},
        ],
        "turns": [
            [
                {"role": "user", "text": "hello", "timestamp": 1000},
                {"role": "assistant", "text": "hi there", "timestamp": 1001},
            ]
        ],
    }


class TestBuildViewStructured:
    def test_structured_format(self, builder, sample_result):
        result = builder.build_view(sample_result, format="structured")
        assert "memories" in result
        assert "turns" in result
        assert len(result["memories"]) == 2
        assert result["memories"][0]["role"] == "user"
        assert result["memories"][0]["score"] == 0.9

    def test_empty_memories(self, builder):
        result = builder.build_view({"memories": [], "turns": []}, format="structured")
        assert result["memories"] == []
        assert result["turns"] == []


class TestBuildViewText:
    def test_text_format(self, builder, sample_result):
        with patch("llmchatflow.core.memory.view_builder.count_tokens", return_value=10):
            result = builder.build_view(sample_result, format="text")
        assert isinstance(result, str)
        assert "hello" in result
        assert "user" in result

    def test_empty_text(self, builder):
        with patch("llmchatflow.core.memory.view_builder.count_tokens", return_value=0):
            result = builder.build_view({"memories": [], "turns": []}, format="text")
        assert result == ""


class TestBuildViewPrompt:
    def test_prompt_format(self, builder, sample_result):
        with patch("llmchatflow.core.memory.view_builder.count_tokens", return_value=10):
            result = builder.build_view(sample_result, format="prompt")
        assert isinstance(result, str)
        assert "user: hello" in result or "hello" in result

    def test_empty_prompt(self, builder):
        with patch("llmchatflow.core.memory.view_builder.count_tokens", return_value=0):
            result = builder.build_view({"memories": [], "turns": []}, format="prompt")
        assert result == ""


class TestBuildViewUnknownFormat:
    def test_unknown_falls_back(self, builder, sample_result):
        result = builder.build_view(sample_result, format="unknown_format")
        assert "memories" in result  # falls back to structured
