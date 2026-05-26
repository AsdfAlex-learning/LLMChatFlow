"""Tests for AppConfig and config loading utilities."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from llmchatflow.config.config import (
    AppConfig,
    _safe_literal,
    _parse_simple_yaml,
    _normalize_weights,
    _build_config_dict,
    load_config,
)


class TestAppConfigDefaults:
    def test_default_values(self):
        cfg = AppConfig()
        assert cfg.user_mode == "single"
        assert cfg.session_id_default == "default_session"
        assert cfg.embedding_dimension == 384
        assert cfg.faiss_topk == 20
        assert cfg.ranking_keep_count == 10
        assert cfg.ranking_lam == 0.1
        assert cfg.ranking_score_normalize is True
        assert cfg.ranking_weight_mode == "by_memory_type"
        assert cfg.context_max_token == 2000
        assert cfg.context_min_token == 500
        assert cfg.history_summarize is True
        assert cfg.memory_type_llm_judge is True
        assert cfg.importance_llm_judge is True
        assert cfg.importance_default == 0.5
        assert cfg.storage_path == "memory.db"
        assert cfg.storage_batch_size == 5
        assert cfg.llm_model == "gpt-3.5-turbo"

    def test_to_dict(self):
        cfg = AppConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["ranking_lam"] == 0.1
        assert d["storage_batch_size"] == 5
        assert "embedding_dimension" in d

    def test_custom_values(self):
        cfg = AppConfig(ranking_lam=0.5, storage_batch_size=10)
        assert cfg.ranking_lam == 0.5
        assert cfg.storage_batch_size == 10


class TestSafeLiteral:
    def test_true(self):
        assert _safe_literal("true") is True

    def test_false(self):
        assert _safe_literal("false") is False

    def test_none(self):
        assert _safe_literal("none") is None

    def test_null(self):
        assert _safe_literal("null") is None

    def test_int(self):
        assert _safe_literal("42") == 42

    def test_float(self):
        assert _safe_literal("3.14") == 3.14

    def test_string(self):
        assert _safe_literal("hello world") == "hello world"

    def test_list(self):
        assert _safe_literal("[1, 2, 3]") == [1, 2, 3]

    def test_whitespace(self):
        assert _safe_literal("  true  ") is True


class TestParseSimpleYaml:
    def test_basic(self):
        result = _parse_simple_yaml("key: value\nnum: 42")
        assert result["key"] == "value"
        assert result["num"] == 42

    def test_comments(self):
        result = _parse_simple_yaml("# comment\nkey: value")
        assert "key" in result
        assert "# comment" not in result

    def test_empty_lines(self):
        result = _parse_simple_yaml("\n\nkey: value\n\n")
        assert result["key"] == "value"

    def test_empty_value(self):
        result = _parse_simple_yaml("key:")
        assert result["key"] is None

    def test_no_colon(self):
        result = _parse_simple_yaml("no_colon_line")
        assert result == {}


class TestNormalizeWeights:
    def test_valid_dict(self):
        w = _normalize_weights({"alpha": 0.6, "beta": 0.3, "theta": 0.1}, {"alpha": 0.5, "beta": 0.2, "theta": 0.3})
        assert w == {"alpha": 0.6, "beta": 0.3, "theta": 0.1}

    def test_string_json(self):
        w = _normalize_weights('{"alpha": 0.7, "beta": 0.2, "theta": 0.1}', {"alpha": 0.5, "beta": 0.2, "theta": 0.3})
        assert w["alpha"] == 0.7

    def test_invalid_string(self):
        fallback = {"alpha": 0.5, "beta": 0.2, "theta": 0.3}
        w = _normalize_weights("not_json", fallback)
        assert w == fallback

    def test_non_dict(self):
        fallback = {"alpha": 0.5, "beta": 0.2, "theta": 0.3}
        w = _normalize_weights(42, fallback)
        assert w == fallback

    def test_partial_dict(self):
        fallback = {"alpha": 0.5, "beta": 0.2, "theta": 0.3}
        w = _normalize_weights({"alpha": 0.8}, fallback)
        assert w["alpha"] == 0.8
        assert w["beta"] == fallback["beta"]


class TestBuildConfigDict:
    def test_valid_keys_only(self):
        built = _build_config_dict({"faiss_topk": 50, "invalid_key": "ignored"})
        assert built["faiss_topk"] == 50
        assert "invalid_key" not in built

    def test_weight_normalization(self):
        built = _build_config_dict({})
        assert "ranking_type_weights_episodic" in built
        assert isinstance(built["ranking_type_weights_episodic"], dict)


class TestLoadConfig:
    def test_missing_file(self, tmp_path):
        cfg = load_config(str(tmp_path / "nonexistent.yaml"))
        assert isinstance(cfg, AppConfig)
        assert cfg.faiss_topk == 20

    def test_valid_yaml(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("faiss_topk: 50\nranking_lam: 0.3\n", encoding="utf-8")
        cfg = load_config(str(yaml_file))
        assert cfg.faiss_topk == 50
        assert cfg.ranking_lam == 0.3
