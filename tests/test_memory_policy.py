"""Tests for MemoryPolicy module."""
from llmchatflow.core.memory.policy import DefaultMemoryPolicy, MemoryPolicy


class TestMemoryPolicyABC:
    def test_cannot_instantiate_abc(self):
        import pytest
        with pytest.raises(TypeError):
            MemoryPolicy()  # type: ignore


class TestDefaultMemoryPolicy:
    def setup_method(self):
        self.policy = DefaultMemoryPolicy()

    def test_select_empty(self):
        result = self.policy.select([], [0.1, 0.2])
        assert result == []

    def test_select_basic(self):
        memories = [
            {"id": "1", "memory_type": "episodic", "importance": 0.8, "decay_rate": 0.1, "timestamp": 1000, "similarity": 0.9, "text": "a"},
            {"id": "2", "memory_type": "habit", "importance": 0.5, "decay_rate": 0.1, "timestamp": 2000, "similarity": 0.5, "text": "b"},
        ]
        result = self.policy.select(memories, [0.1, 0.2])
        assert len(result) == 2
        assert all("_score" in r or "similarity" in r for r in result)

    def test_score_returns_float(self):
        memory = {"id": "1", "memory_type": "episodic", "importance": 0.5, "decay_rate": 0.1, "timestamp": 1000, "similarity": 0.8}
        score = self.policy.score(memory, [0.1, 0.2])
        assert isinstance(score, float)
        assert score >= 0.0
