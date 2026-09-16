"""Shared run and result contracts for every evaluator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationRunMetadata(EvaluationContract):
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    dataset_name: str
    dataset_version: str
    git_commit: str
    evaluator_version: str
    mode: str
    model_name: str | None = None
    model_version: str | None = None
    temperature: float | None = None
    prompt_version: str | None = None
    python_version: str
    project_version: str
    configuration_snapshot: dict[str, object] = Field(default_factory=dict)


class EvaluationFailure(EvaluationContract):
    case_id: str
    reason: str


class EvaluatorOutput(EvaluationContract):
    status: Literal["completed", "error"] = "completed"
    case_count: int = Field(ge=0)
    metrics: dict[str, float | int] = Field(default_factory=dict)
    failures: list[EvaluationFailure] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvaluationResult(EvaluationContract):
    evaluator: str
    status: Literal["completed", "error"]
    case_count: int = Field(ge=0)
    metrics: dict[str, float | int] = Field(default_factory=dict)
    failures: list[EvaluationFailure] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: EvaluationRunMetadata
