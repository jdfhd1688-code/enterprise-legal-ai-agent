"""Local JSON task store for MVP persistence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.task import TaskRecord


class TaskNotFoundError(KeyError):
    pass


class TaskStore:
    """Stores task records as isolated JSON files under data/tasks."""

    _safe_id = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.directory = Path(self.settings.task_dir)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, task_id: str) -> Path:
        if not self._safe_id.match(task_id):
            raise ValueError(f"非法任务 ID：{task_id}")
        return self.directory / f"{task_id}.json"

    def save(self, task: TaskRecord) -> TaskRecord:
        path = self.path_for(task.task_id)
        data = task.model_dump_json(indent=2)
        path.write_text(data, encoding="utf-8")
        return task

    def load(self, task_id: str) -> TaskRecord:
        path = self.path_for(task_id)
        if not path.exists():
            raise TaskNotFoundError(f"任务不存在：{task_id}")
        try:
            return TaskRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - recoverable store corruption
            raise TaskNotFoundError(f"任务记录损坏：{task_id} ({exc})") from exc

    def list_tasks(self, newest_first: bool = True) -> list[TaskRecord]:
        tasks: list[TaskRecord] = []
        for path in sorted(self.directory.glob("TASK-*.json")):
            try:
                tasks.append(TaskRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 - ignore corrupt file during list
                continue
        if newest_first:
            tasks.sort(key=lambda task: task.created_at, reverse=True)
        return tasks

    def list_status(self, status: str) -> list[TaskRecord]:
        return [task for task in self.list_tasks() if task.status.value == status]

