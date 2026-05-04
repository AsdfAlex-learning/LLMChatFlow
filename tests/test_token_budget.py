"""Tests for core.prompt.token_budget module."""
from llmchatflow.core.prompt.token_budget import (
    proportional_budget,
    reserve_budget,
    trim_records_to_token_budget,
    within_budget,
)


class TestWithinBudget:
    def test_under_budget(self):
        assert within_budget(["short"], 1000, "gpt2") is True

    def test_empty_list(self):
        assert within_budget([], 100, "gpt2") is True


class TestTrimRecordsToTokenBudget:
    def test_under_max_returns_all(self):
        records = [{"text": "hello", "_score": 0.5}]
        result = trim_records_to_token_budget(records, 1000, "gpt2")
        assert len(result) == 1

    def test_over_max_trims_low_score(self):
        records = [
            {"text": "A" * 500, "_score": 0.1},
            {"text": "B" * 500, "_score": 0.9},
        ]
        result = trim_records_to_token_budget(records, 50, "gpt2")
        assert len(result) <= 2

    def test_empty_list(self):
        result = trim_records_to_token_budget([], 100, "gpt2")
        assert result == []


class TestReserveBudget:
    def test_reserve_works(self):
        result = reserve_budget(1000, {"system": 200, "history": 500})
        assert result["system"] == 200
        assert result["history"] == 500
        assert result["_remaining"] == 300

    def test_over_total(self):
        result = reserve_budget(100, {"system": 200})
        assert result["system"] == 100
        assert result["_remaining"] == 0


class TestProportionalBudget:
    def test_basic_distribution(self):
        result = proportional_budget(1000, {"a": 0.5, "b": 0.5})
        assert result["a"] + result["b"] == 1000
