"""Persistent task-record models used by the local JSON store."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.document import DocumentChunk, ParsedDocument
from app.schemas.kb import RetrievalResult
from app.schemas.playbook import PlaybookResult
from app.schemas.risk import ReviewOutcome, RiskAnalysis, TaskStatus


class StageEvent(BaseModel):
    stage: str
    message: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEvent(BaseModel):
    event_type: str
    actor: str = "system"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""


class TaskRecord(BaseModel):
    task_id: str
    original_filename: str
    question: str
    review_dimension: str = "general_contract"
    status: TaskStatus = TaskStatus.submitted
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parsed_document: ParsedDocument | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    retrieval: RetrievalResult = Field(default_factory=RetrievalResult)
    playbook: PlaybookResult = Field(default_factory=PlaybookResult)
    risk: RiskAnalysis | None = None
    route: str | None = None
    route_reason: str | None = None
    events: list[StageEvent] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    original_ai_result: RiskAnalysis | None = None
    reviewed_result: RiskAnalysis | None = None
    report_markdown: str | None = None
    report_html_ready: bool = False
    review: ReviewOutcome | None = None
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    @property
    def terminal(self) -> bool:
        return self.status in {TaskStatus.reviewed, TaskStatus.report_ready, TaskStatus.failed}
