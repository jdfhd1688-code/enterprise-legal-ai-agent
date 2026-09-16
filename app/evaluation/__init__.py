"""Offline Legal RAG evaluation."""

from app.evaluation.contracts import (
    EvaluationFailure,
    EvaluationResult,
    EvaluationRunMetadata,
)
from app.evaluation.dataset_loader import DatasetLoader, LoadedDataset
from app.evaluation.dataset_models import EvaluationDatasetMetadata
from app.evaluation.retrieval_eval import RetrievalEvaluator
from app.evaluation.retrieval_v2 import RetrievalV2Evaluator

__all__ = [
    "DatasetLoader",
    "EvaluationDatasetMetadata",
    "EvaluationFailure",
    "EvaluationResult",
    "EvaluationRunMetadata",
    "LoadedDataset",
    "RetrievalEvaluator",
    "RetrievalV2Evaluator",
]
