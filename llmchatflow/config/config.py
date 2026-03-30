from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional
import ast
import json


@dataclass
class AppConfig:
    user_mode: str = "single"
    session_id_default: str = "default_session"
    query_rewrite_trigger: str = "none"
    query_rewrite_persist: str = "none"
    embedding_input_source: str = "original"
    embedding_dimension: int = 384
    faiss_topk: int = 20
    faiss_filter_strategy: str = "global"
    ranking_score_normalize: bool = True
    ranking_weight_mode: str = "by_memory_type"
    ranking_type_weights_episodic: Dict[str, float] = field(
        default_factory=lambda: {"alpha": 0.5, "beta": 0.1, "theta": 0.4}
    )
    ranking_type_weights_habit: Dict[str, float] = field(
        default_factory=lambda: {"alpha": 0.7, "beta": 0.3, "theta": 0.0}
    )
    ranking_type_weights_summary: Dict[str, float] = field(
        default_factory=lambda: {"alpha": 0.6, "beta": 0.3, "theta": 0.1}
    )
    ranking_type_weights_default: Dict[str, float] = field(
        default_factory=lambda: {"alpha": 0.5, "beta": 0.2, "theta": 0.3}
    )
    ranking_keep_count: int = 10
    context_max_token: int = 2000
    context_min_token: int = 500
    history_summarize: bool = True
    system_prompt: str = "built-in"
    memory_type_llm_judge: bool = True
    faiss_write_strategy: str = "real_time"
    importance_llm_judge: bool = True
    importance_default: float = 0.5
    archive_days: int = 90
    archive_importance: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_literal(value: str) -> Any:
    text = value.strip()
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        return ast.literal_eval(text)
    except Exception:
        return text


def _parse_simple_yaml(content: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        data[key] = _safe_literal(value) if value else None
    return data


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(content)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _parse_simple_yaml(content)


def _normalize_weights(value: Any, fallback: Dict[str, float]) -> Dict[str, float]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            value = parsed
        except Exception:
            try:
                value = ast.literal_eval(value)
            except Exception:
                return fallback
    if not isinstance(value, dict):
        return fallback
    alpha = float(value.get("alpha", fallback["alpha"]))
    beta = float(value.get("beta", fallback["beta"]))
    theta = float(value.get("theta", fallback["theta"]))
    return {"alpha": alpha, "beta": beta, "theta": theta}


def _build_config_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    valid_keys = {item.name for item in fields(AppConfig)}
    built: Dict[str, Any] = {}
    for key in valid_keys:
        if key in raw:
            built[key] = raw[key]
    default_cfg = AppConfig()
    built["ranking_type_weights_episodic"] = _normalize_weights(
        built.get("ranking_type_weights_episodic"),
        default_cfg.ranking_type_weights_episodic,
    )
    built["ranking_type_weights_habit"] = _normalize_weights(
        built.get("ranking_type_weights_habit"),
        default_cfg.ranking_type_weights_habit,
    )
    built["ranking_type_weights_summary"] = _normalize_weights(
        built.get("ranking_type_weights_summary"),
        default_cfg.ranking_type_weights_summary,
    )
    built["ranking_type_weights_default"] = _normalize_weights(
        built.get("ranking_type_weights_default"),
        default_cfg.ranking_type_weights_default,
    )
    return built


def load_config(config_path: Optional[str] = None) -> AppConfig:
    path = Path(config_path) if config_path else Path(__file__).with_name("config.yaml")
    raw = _load_yaml_file(path)
    built = _build_config_dict(raw)
    return AppConfig(**built)


config = load_config()
