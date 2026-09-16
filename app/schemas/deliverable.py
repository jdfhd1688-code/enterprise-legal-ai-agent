"""Final review and deliverable metadata contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ReviewItemAction(str, Enum):
    pending = "pending"
    accept = "accept"
    edit = "edit"
    reject = "reject"
    resolved = "resolved"
    escalate = "escalate"
    auto_approved = "auto_approved"


class ReviewItemDecision(BaseModel):
    risk_id: str
    action: ReviewItemAction = ReviewItemAction.pending
    final_clause: str | None = None
    comment: str = ""
    reviewer: str = "demo_reviewer"
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeliverableMetadata(BaseModel):
    task_id: str
    type: str
    filename: str
    relative_path: str
    sha256: str
    size_bytes: int
    status: str = "ready"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RedlineApplyResult(BaseModel):
    risk_id: str
    status: str
    reason: str = ""
    paragraph_index: int | None = None
