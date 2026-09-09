"""Knowledge-base chunk and retrieval-result models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KBChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    article_no: str
    content: str
    source: str
    source_url: str | None = None
    issuing_authority: str = "DEMO/SAMPLE"
    effective_date: str | None = None
    expiry_date: str | None = None
    domain: str = "contract"
    jurisdiction: str = "unknown"
    source_type: str = "demo_sample"
    version: str = "0.1-demo"
    status: str = "effective"
    is_demo_sample: bool = True
    updated_at: str | None = None


class RetrievalHit(BaseModel):
    chunk: KBChunk
    score: float = Field(ge=0.0, le=1.0)
    matched_text: str = ""
    similarity_score: float = Field(ge=0.0, le=1.0)
    keyword_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dense_score: float = Field(default=0.0, ge=0.0, le=1.0)
    fusion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rank: int = Field(default=0, ge=0)
    match_reason: str = "semantic_similarity"
    metadata: dict[str, str] = Field(default_factory=dict)
    validity_status: str = "unknown"


class RetrievalResult(BaseModel):
    hits: list[RetrievalHit] = Field(default_factory=list)
    used_fallback: bool = True
    total_candidates: int = 0
    filters_applied: list[str] = Field(default_factory=list)
    mcp_calls: list[dict[str, object]] = Field(default_factory=list)
    evidence_insufficient_reason: str | None = None
    query: str = ""
    queries: list[str] = Field(default_factory=list)
    metadata_filters: dict[str, object] = Field(default_factory=dict)
    keyword_hits: list[str] = Field(default_factory=list)
    dense_hits: list[str] = Field(default_factory=list)
    fusion_method: str = "rrf-k60"
    top_k: int = 0
    jurisdiction_assumption: str | None = None

    @property
    def is_empty(self) -> bool:
        return len(self.hits) == 0
