"""Offline Legal RAG evaluation."""

from app.evaluation.contracts import (
    EvaluationFailure,
    EvaluationResult,
    EvaluationRunMetadata,
)
from app.evaluation.dataset_loader import DatasetLoader, LoadedDataset
from app.evaluation.dataset_models import EvaluationDatasetMetadata
from app.evaluation.retrieval_eval import RetrievalEvaluator

__all__ = [
    "DatasetLoader",
    "EvaluationDatasetMetadata",
    "EvaluationFailure",
    "EvaluationResult",
    "EvaluationRunMetadata",
    "LoadedDataset",
    "RetrievalEvaluator",
]
