"""Evaluator registry and offline execution runner."""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Protocol
from uuid import uuid4

from app import __version__
from app.evaluation.contracts import (
    EvaluationFailure,
    EvaluationResult,
    EvaluationRunMetadata,
    EvaluatorOutput,
)
from app.evaluation.dataset_loader import DatasetLoader, LoadedDataset


SENSITIVE_KEY_PARTS = ("api_key", "apikey", "secret", "token", "password", "credential")


class Evaluator(Protocol):
    name: str
    version: str

    def evaluate(self, dataset: LoadedDataset) -> EvaluatorOutput: ...


class EvaluatorNotRegisteredError(LookupError):
    pass


class EvaluationRunner:
    def __init__(self, loader: DatasetLoader | None = None, project_root: Path | None = None) -> None:
        self.loader = loader or DatasetLoader()
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self._registry: dict[str, Evaluator] = {}

    def register(self, evaluator: Evaluator) -> None:
        if not evaluator.name.strip():
            raise ValueError("Evaluator name cannot be empty")
        self._registry[evaluator.name] = evaluator

    def run(
        self,
        evaluator_name: str,
        dataset_path: str | Path,
        *,
        mode: str = "offline_deterministic",
        configuration: Mapping[str, object] | None = None,
    ) -> EvaluationResult:
        evaluator = self._registry.get(evaluator_name)
        if evaluator is None:
            raise EvaluatorNotRegisteredError(f"Evaluator is not registered: {evaluator_name}")
        dataset = self.loader.load(dataset_path)
        metadata = EvaluationRunMetadata(
            run_id=f"eval-{uuid4().hex[:12]}",
            dataset_name=dataset.metadata.dataset_name,
            dataset_version=dataset.metadata.dataset_version,
            git_commit=self._git_commit(),
            evaluator_version=evaluator.version,
            mode=mode,
            python_version=platform.python_version(),
            project_version=__version__,
            configuration_snapshot=self._sanitize_configuration(configuration or {}),
        )
        try:
            output = evaluator.evaluate(dataset)
        except Exception as exc:  # noqa: BLE001 - evaluator errors are reportable results
            output = EvaluatorOutput(
                status="error",
                case_count=len(dataset.cases),
                failures=[
                    EvaluationFailure(
                        case_id="__evaluator__",
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                ],
            )
        metadata.completed_at = datetime.now(timezone.utc)
        return EvaluationResult(
            evaluator=evaluator.name,
            status=output.status,
            case_count=output.case_count,
            metrics=output.metrics,
            failures=output.failures,
            warnings=output.warnings,
            metadata=metadata,
        )

    def _git_commit(self) -> str:
        try:
            return subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    @classmethod
    def _sanitize_configuration(cls, configuration: Mapping[str, object]) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        for key, value in configuration.items():
            lowered = key.lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, Mapping):
                sanitized[key] = cls._sanitize_configuration(value)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized


class FoundationValidationEvaluator:
    """Validates foundation wiring only; it does not claim system performance."""

    name = "foundation_validation"
    version = "b1-foundation-v1"

    def evaluate(self, dataset: LoadedDataset) -> EvaluatorOutput:
        return EvaluatorOutput(
            status="completed",
            case_count=len(dataset.cases),
            metrics={"validated_cases": len(dataset.cases)},
            warnings=[
                "Foundation fixture validation only; this result is not a product performance metric."
            ],
        )
