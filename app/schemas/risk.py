"""Structured risk-analysis JSON contract.

This contract is deliberately strict: every claim produced for a report must
either carry a controlled knowledge-base citation or be labelled as an
unverified / demo inference.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, Enum):
    submitted = "submitted"
    parsing = "parsing"
    chunking = "chunking"
    retrieving = "retrieving"
    analyzing = "analyzing"
    validating = "validating"
    routing = "routing"
    awaiting_review = "awaiting_review"
    report_ready = "report_ready"
    reviewed = "reviewed"
    failed = "failed"
    cancelled = "cancelled"


class LegalBasis(BaseModel):
    title: str
    article_no: str
    source: str
    status: str = "effective"
    jurisdiction: str = "unknown"
    effective_date: str | None = None
    expiry_date: str | None = None
    source_url: str | None = None
    domain: str = "contract"
    source_type: str = "demo_sample"
    match_reason: str = "semantic_similarity"
    is_demo_sample: bool = True

    @field_validator("effective_date", mode="before")
    @classmethod
    def empty_date_to_none(cls, value: object) -> object:
        if value in ("", None):
            return None
        return value

    @field_validator("expiry_date", mode="before")
    @classmethod
    def empty_expiry_to_none(cls, value: object) -> object:
        if value in ("", None):
            return None
        return value


class Finding(BaseModel):
    clause_id: str
    risk_type: str
    severity: Severity
    issue: str
    contract_evidence: str = ""
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    recommendation: str = ""
    evidence_page: int | None = None
    evidence_section: str | None = None
    evidence_sufficient: bool = True


class RiskAnalysis(BaseModel):
    task_id: str
    risk_level: RiskLevel
    legal_domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    review_dimension: str = "general_contract"
    evidence_sufficient: bool = True
    retrieval_summary: str = ""
    requires_human_review: bool = False
    review_reason: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_mode: str = "demo-heuristic"
    model_version: str = "demo-heuristic-v1"


class ReviewDecision(str, Enum):
    approve = "approve"
    request_changes = "request_changes"
    reject = "reject"


class ReviewSubmission(BaseModel):
    decision: ReviewDecision
    comment: str = ""
    modifications: dict[str, dict[str, str]] = Field(default_factory=dict)


class ReviewOutcome(BaseModel):
    decision: ReviewDecision
    comment: str = ""
    modifications: dict[str, dict[str, str]] = Field(default_factory=dict)
    reviewer: str = "demo-reviewer"
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    final_summary: str | None = None
    final_risk_level: RiskLevel | None = None
