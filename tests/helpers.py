from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402


class TempSettings:
    """Small context manager that isolates task/upload/kb dirs per test."""

    def __init__(self, use_real_kb: bool = False) -> None:
        self.use_real_kb = use_real_kb

    def __enter__(self) -> Settings:
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        kb_dir = (
            ROOT / "data" / "legal_kb"
            if self.use_real_kb
            else root / "legal_kb"
        )
        settings = Settings(
            task_dir=root / "tasks",
            upload_dir=root / "uploads",
            contract_dir=root / "contracts",
            legal_kb_dir=kb_dir,
            playbook_dir=ROOT / "data" / "playbooks" if self.use_real_kb else root / "playbooks",
            eval_dir=ROOT / "data" / "eval" if self.use_real_kb else root / "eval",
        )
        settings.ensure_dirs()
        return settings

    def __exit__(self, *_: object) -> None:
        self.tmp.cleanup()
