"""Strict, versioned dataset contracts for offline evaluation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictEvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DatasetType(str, Enum):
    retrieval = "retrieval"
    risk = "risk"
    abstention = "abstention"
    citation = "citation"
    schema = "schema"


class DatasetSourceType(str, Enum):
    demo = "demo"
    synthetic = "synthetic"
    public_safe = "public_safe"
    public = "public"


class QueryType(str, Enum):
    contract = "contract"
    legal = "legal"


class ExpectedRisk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ExpectedRoute(str, Enum):
    auto_report = "auto_report"
    human_review = "human_review"


class AbstentionCaseType(str, Enum):
    missing_evidence = "missing_evidence"
    wrong_jurisdiction = "wrong_jurisdiction"
    expired_law = "expired_law"
    missing_context = "missing_context"
    ambiguous_clause = "ambiguous_clause"


class ExpectedSupport(str, Enum):
    supported = "supported"
    unsupported = "unsupported"
    needs_human_review = "needs_human_review"


class EvaluationDatasetMetadata(StrictEvaluationModel):
    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    dataset_type: DatasetType
    source_type: DatasetSourceType
    created_at: datetime
    description: str = Field(min_length=1)
    reviewer: str | None = None
    notes: str | None = None


class RetrievalEvalCase(StrictEvaluationModel):
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    query_type: QueryType
    expected_doc_ids: list[str]
    expected_no_relevant_result: bool = False
    jurisdiction: str | None = None
    law_status: str | None = None
    legal_domain: str | None = None
    corpus_path: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_relevance_contract(self) -> "RetrievalEvalCase":
        if any(not item.strip() for item in self.expected_doc_ids):
            raise ValueError("expected_doc_ids cannot contain blank IDs")
        if len(self.expected_doc_ids) != len(set(self.expected_doc_ids)):
            raise ValueError("expected_doc_ids cannot contain duplicates")
        if self.expected_no_relevant_result and self.expected_doc_ids:
            raise ValueError("negative retrieval cases cannot declare expected_doc_ids")
        if not self.expected_no_relevant_result and not self.expected_doc_ids:
            raise ValueError(
                "positive retrieval cases require expected_doc_ids; use "
                "expected_no_relevant_result=true for explicit negatives"
            )
        return self


class RiskEvalCase(StrictEvaluationModel):
    id: str = Field(min_length=1)
    clause: str = Field(min_length=1)
    evidence: list[str]
    expected_risk: ExpectedRisk
    expected_route: ExpectedRoute
    expected_human_review: bool
    reason: str = Field(min_length=1)


class AbstentionEvalCase(StrictEvaluationModel):
    id: str = Field(min_length=1)
    clause: str = Field(min_length=1)
    retrieval_context: list[str]
    expected_insufficient_evidence: bool
    expected_human_review: bool
    forbidden_behavior: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    case_type: AbstentionCaseType | None = None


class CitationEvalCase(StrictEvaluationModel):
    id: str = Field(min_length=1)
    finding: str = Field(min_length=1)
    retrieval_hits: list[str]
    expected_citation_ids: list[str]
    expected_support: ExpectedSupport


class SchemaEvalCase(StrictEvaluationModel):
    id: str = Field(min_length=1)
    raw_output: Any
    expected_parse_success: bool
    expected_raw_schema_pass: bool
    expected_repairable: bool
    notes: str | None = None


EvaluationCase = RetrievalEvalCase | RiskEvalCase | AbstentionEvalCase | CitationEvalCase | SchemaEvalCase

DATASET_CASE_MODELS: dict[DatasetType, type[StrictEvaluationModel]] = {
    DatasetType.retrieval: RetrievalEvalCase,
    DatasetType.risk: RiskEvalCase,
    DatasetType.abstention: AbstentionEvalCase,
    DatasetType.citation: CitationEvalCase,
    DatasetType.schema: SchemaEvalCase,
}
