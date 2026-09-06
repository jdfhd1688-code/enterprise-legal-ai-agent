"""State definitions for the demo agent state graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.document import DocumentChunk, ParsedDocument
from app.schemas.kb import RetrievalResult
from app.schemas.risk import RiskAnalysis


@dataclass
class AgentState:
    """Mutable state passed from node to node in the explicit state machine."""

    task_id: str
    original_filename: str
    question: str
    stage: str = "START"
    parsed_document: ParsedDocument | None = None
    chunks: list[DocumentChunk] = field(default_factory=list)
    retrieval: RetrievalResult = field(default_factory=RetrievalResult)
    risk: RiskAnalysis | None = None
    route: str | None = None
    events: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None

    def add_event(self, stage: str, message: str) -> None:
        self.events.append({"stage": stage, "message": message})
        self.stage = stage

