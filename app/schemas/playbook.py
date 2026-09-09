"""Versioned enterprise contract playbook models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.risk import PlaybookEvidence, RedlineSuggestion, Severity


class PlaybookRule(BaseModel):
    rule_id: str
    dimension: str
    title: str
    description: str = ""
    evaluator: str
    trigger_terms: list[str] = Field(default_factory=list)
    risk_terms: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    preferred: str = ""
    acceptable: str = ""
    high_risk: str = ""
    threshold: float | None = None
    severity: Severity = Severity.medium
    recommendation: str = ""
    suggested_clause: str | None = None
    version: str = "demo-v1"
    source_type: str = "demo_sample"


class PlaybookDeviation(BaseModel):
    rule_id: str
    chunk_id: str
    evidence: PlaybookEvidence
    redline: RedlineSuggestion | None = None
    recommendation: str = ""


class PlaybookResult(BaseModel):
    version: str = "demo-v1"
    rules_evaluated: int = 0
    deviations: list[PlaybookDeviation] = Field(default_factory=list)
    source_type: str = "demo_sample"
