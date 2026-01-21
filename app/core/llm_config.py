import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LlmConfig:
    rerank_enabled: bool = True
    rerank_top_k: int = 10
    rerank_mode: str = "per_meal"
    rerank_cache_ttl_seconds: int = 86400


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _as_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "llm_config.json"


def load_llm_config(path: Optional[Path] = None) -> LlmConfig:
    config_path = path or _config_path()
    try:
        data: Dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return LlmConfig()
    except json.JSONDecodeError as exc:
        logger.warning(f"Invalid LLM config JSON at {config_path}: {exc}")
        return LlmConfig()

    return LlmConfig(
        rerank_enabled=_as_bool(data.get("rerank_enabled"), True),
        rerank_top_k=_as_int(data.get("rerank_top_k"), 10),
        rerank_mode=str(data.get("rerank_mode") or "per_meal"),
        rerank_cache_ttl_seconds=_as_int(data.get("rerank_cache_ttl_seconds"), 86400)
    )
