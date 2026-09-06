"""Application settings and environment configuration.

The package deliberately keeps every provider setting in the environment.
DEMO MODE is the default and needs no API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv is optional so the demo still runs without pip extras.
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover - exercised only on minimal runtimes
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONTRACT_DIR = DATA_DIR / "contracts"
LEGAL_KB_DIR = DATA_DIR / "legal_kb"
TASK_DIR = DATA_DIR / "tasks"
UPLOAD_DIR = DATA_DIR / "uploads"


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _as_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    """Runtime settings loaded once per process."""

    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    contract_dir: Path = CONTRACT_DIR
    legal_kb_dir: Path = LEGAL_KB_DIR
    task_dir: Path = TASK_DIR
    upload_dir: Path = UPLOAD_DIR

    enable_real_llm: bool = field(default_factory=lambda: _as_bool("ENABLE_REAL_LLM"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    )
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gpt-4o-mini"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )

    confidence_threshold: float = field(
        default_factory=lambda: _as_float("CONFIDENCE_THRESHOLD", 0.75)
    )
    max_upload_mb: int = field(default_factory=lambda: _as_int("MAX_UPLOAD_MB", 10))
    llm_timeout_seconds: int = field(default_factory=lambda: _as_int("LLM_TIMEOUT_SECONDS", 30))
    review_required_domains: tuple[str, ...] = field(default=("intellectual_property",))

    def ensure_dirs(self) -> None:
        for directory in (self.task_dir, self.upload_dir, self.contract_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def demo_mode(self) -> bool:
        """True when the deterministic demo path is used for analysis."""
        return not self.enable_real_llm or not self.openai_api_key

    @property
    def demo_mode_label(self) -> str:
        if self.demo_mode:
            return "DEMO MODE（未启用真实 LLM，使用内置规则引擎演示）"
        return "REAL LLM"

    def domain_requires_specialist_review(self, domain: str) -> bool:
        return domain in self.review_required_domains


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a process-wide Settings instance, creating directories on first use."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
