"""Tests for core.memory.semantic module."""
import math

from llmchatflow.core.memory.semantic import semantic_scores


class TestSemanticScores:
    def test_returns_list_of_scores(self):
        """Basic sanity: returns list of floats."""
        embedding = [1.0, 0.0, 0.0]
        records = [
            {"id": "1", "text": "hello", "importance": 0.5},
            {"id": "2", "text": "world", "importance": 0.7},
        ]
        scores = semantic_scores(embedding, records)
        assert isinstance(scores, list)
        assert len(scores) == 2
        assert all(isinstance(s, float) for s in scores)

    def test_empty_records_returns_empty(self):
        scores = semantic_scores([1.0, 0.0], [])
        assert scores == []
