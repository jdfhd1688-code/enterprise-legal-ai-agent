"""Fail-loud JSON loader for versioned evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from app.evaluation.dataset_models import (
    DATASET_CASE_MODELS,
    EvaluationCase,
    EvaluationDatasetMetadata,
)


class DatasetLoadError(ValueError):
    """The dataset could not be read or did not match its declared contract."""


class LoadedDataset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: EvaluationDatasetMetadata
    cases: list[EvaluationCase]
    source_path: Path


class DatasetLoader:
    def load(self, path: str | Path) -> LoadedDataset:
        source = Path(path)
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetLoadError(f"Cannot read evaluation dataset {source}: {exc}") from exc
        if not isinstance(raw, dict):
            raise DatasetLoadError(f"Evaluation dataset {source} must be a JSON object")
        if "metadata" not in raw or "cases" not in raw:
            raise DatasetLoadError(f"Evaluation dataset {source} requires metadata and cases")
        try:
            metadata = EvaluationDatasetMetadata.model_validate(raw["metadata"])
        except ValidationError as exc:
            raise DatasetLoadError(f"Invalid dataset metadata in {source}: {exc}") from exc
        cases_raw = raw["cases"]
        if not isinstance(cases_raw, list):
            raise DatasetLoadError(f"Dataset cases in {source} must be a list")
        if not cases_raw:
            raise DatasetLoadError(f"Evaluation dataset {source} must contain at least one case")
        case_model = DATASET_CASE_MODELS[metadata.dataset_type]
        cases: list[EvaluationCase] = []
        for index, item in enumerate(cases_raw):
            try:
                cases.append(case_model.model_validate(item))
            except ValidationError as exc:
                raise DatasetLoadError(
                    f"Invalid {metadata.dataset_type.value} case at index {index} in {source}: {exc}"
                ) from exc
        duplicate_ids = self._duplicates([case.id for case in cases])
        if duplicate_ids:
            raise DatasetLoadError(f"Duplicate case IDs in {source}: {', '.join(duplicate_ids)}")
        return LoadedDataset(metadata=metadata, cases=cases, source_path=source.resolve())

    @staticmethod
    def _duplicates(values: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for value in values:
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        return sorted(duplicates)
