"""Pydantic contracts used by the analysis pipeline."""

from app.schemas.document import DocumentChunk, DocumentPage, ParsedDocument
from app.schemas.kb import KBChunk, RetrievalHit, RetrievalResult
from app.schemas.playbook import PlaybookDeviation, PlaybookResult, PlaybookRule
from app.schemas.risk import (
    CitationStatus,
    EvidenceStatus,
    Finding,
    LegalBasis,
    PlaybookEvidence,
    RedlineSuggestion,
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
    "CitationStatus",
    "EvidenceStatus",
    "KBChunk",
    "LegalBasis",
    "PlaybookDeviation",
    "PlaybookEvidence",
    "PlaybookResult",
    "PlaybookRule",
    "RedlineSuggestion",
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
