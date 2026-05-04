"""Tests for core.memory.ranking module."""
import math

from llmchatflow.core.memory.ranking import (
    compute_final_scores,
    compute_final_scores_by_type,
    recency_scores,
    temporal_score,
)


class TestTemporalScore:
    def test_zero_delta_returns_one(self):
        """delta=0 -> exp(0) = 1.0"""
        assert temporal_score(100, 100, lam=0.1) == 1.0

    def test_large_delta_approaches_zero(self):
        """Large time difference should make score approach 0"""
        score = temporal_score(0, 1000000, lam=1.0)  # Use higher lam for faster decay
        assert score < 0.01

    def test_higher_lam_faster_decay(self):
        """Higher lambda = faster decay"""
        score1 = temporal_score(100, 200, lam=0.1)
        score2 = temporal_score(100, 200, lam=1.0)
        assert score1 > score2


class TestRecencyScores:
    def test_empty_list_returns_empty(self):
        assert recency_scores([]) == []

    def test_last_item_is_one(self):
        """The most recent (last) item should get score 1.0"""
        scores = recency_scores([{"timestamp": 100}, {"timestamp": 200}, {"timestamp": 300}])
        assert scores[-1] == 1.0

    def test_first_item_is_lowest(self):
        """The oldest (first) item should get the lowest score"""
        scores = recency_scores([{"timestamp": 100}, {"timestamp": 200}, {"timestamp": 300}])
        assert scores[0] < scores[-1]


class TestComputeFinalScores:
    def test_basic_scoring(self):
        records = [{"id": "1", "importance": 0.5, "timestamp": 1000}, {"id": "2", "importance": 0.8, "timestamp": 2000}]
        cos_sims = [0.8, 0.5]
        scored = compute_final_scores(
            records, cos_sims, lam=0.1, alpha=0.5, beta=0.2, gamma=0.15, delta=0.15
        )
        assert len(scored) == 2
        scores = [s for s, _ in scored]
        assert all(s >= 0 for s in scores)


class TestComputeFinalScoresByType:
    def test_type_aware_weights(self):
        records = [
            {"id": "1", "memory_type": "episodic", "importance": 0.5, "decay_rate": 0.1, "timestamp": 1000},
            {"id": "2", "memory_type": "habit", "importance": 0.8, "decay_rate": 0.05, "timestamp": 2000},
        ]
        similarities = [0.9, 0.7]
        type_weights = {
            "episodic": {"alpha": 0.5, "beta": 0.1, "theta": 0.4},
            "habit": {"alpha": 0.7, "beta": 0.3, "theta": 0.0},
        }
        scored = compute_final_scores_by_type(
            records, similarities, lam=0.1, type_weights=type_weights, default_weights={"alpha": 0.5, "beta": 0.2, "theta": 0.3}, normalize=True,
        )
        assert len(scored) == 2

    def test_unknown_type_uses_default(self):
        records = [
            {"id": "1", "memory_type": "unknown_type", "importance": 0.5, "decay_rate": 0.1, "timestamp": 1000},
        ]
        similarities = [0.5]
        scored = compute_final_scores_by_type(
            records, similarities, lam=0.1, type_weights={}, default_weights={"alpha": 0.5, "beta": 0.2, "theta": 0.3}, normalize=False,
        )
        assert len(scored) == 1
