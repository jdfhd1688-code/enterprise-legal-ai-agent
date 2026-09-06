"""Pydantic contracts used by the analysis pipeline."""

from app.schemas.document import DocumentChunk, DocumentPage, ParsedDocument
from app.schemas.kb import KBChunk, RetrievalHit, RetrievalResult
from app.schemas.risk import (
    Finding,
    LegalBasis,
    ReviewDecision,
    ReviewOutcome,
    ReviewSubmission,
    RiskAnalysis,
    RiskLevel,
    Severity,
    TaskStatus,
)

__all__ = [
    "DocumentChunk",
    "DocumentPage",
    "Finding",
    "KBChunk",
    "LegalBasis",
    "ParsedDocument",
    "RetrievalHit",
    "RetrievalResult",
    "ReviewDecision",
    "ReviewOutcome",
    "ReviewSubmission",
    "RiskAnalysis",
    "RiskLevel",
    "Severity",
    "TaskStatus",
]
