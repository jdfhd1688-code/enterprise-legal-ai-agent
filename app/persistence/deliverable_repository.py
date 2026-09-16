"""Controlled output storage with hashes and traversal protection."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.deliverable import DeliverableMetadata


class DeliverableRepository:
    _safe = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.root = Path(self.settings.output_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def task_directory(self, task_id: str) -> Path:
        if not self._safe.fullmatch(task_id):
            raise ValueError("非法任务 ID")
        target = (self.root / task_id).resolve()
        if self.root not in target.parents:
            raise ValueError("输出路径越界")
        target.mkdir(parents=True, exist_ok=True)
        return target

    def write(self, task_id: str, kind: str, filename: str, content: bytes) -> DeliverableMetadata:
        if not self._safe.fullmatch(filename) or Path(filename).name != filename:
            raise ValueError("非法交付文件名")
        target = self.task_directory(task_id) / filename
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        relative = target.relative_to(self.root).as_posix()
        return DeliverableMetadata(
            task_id=task_id, type=kind, filename=filename, relative_path=relative,
            sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content),
        )

    def read(self, metadata: DeliverableMetadata) -> bytes:
        target = (self.root / metadata.relative_path).resolve()
        if self.root not in target.parents or not target.is_file():
            raise FileNotFoundError("交付文件不存在或路径不安全")
        return target.read_bytes()
