"""Deterministic lexical ranking over chunks from one parsed contract."""

from __future__ import annotations

import math
import re
from collections import Counter

from pydantic import BaseModel, Field

from app.rag.relevance_gate import RelevanceGate
from app.schemas.document import DocumentAnchor, DocumentChunk


class ContractRetrievalHit(BaseModel):
    chunk_id: str
    section: str
    page_no: int | None = None
    anchor: DocumentAnchor | None = None
    score: float = Field(ge=0.0, le=1.0)
    raw_bm25_score: float = Field(ge=0.0)
    query_coverage: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
    is_usable: bool
    relevance_status: str
    text: str


class ContractRetrievalResult(BaseModel):
    candidates: list[ContractRetrievalHit] = Field(default_factory=list)
    hits: list[ContractRetrievalHit] = Field(default_factory=list)
    rejection_count: int = 0


class ContractRetriever:
    """A small BM25-style retriever with an explainable relevance gate."""

    def __init__(self, relevance_gate: RelevanceGate | None = None) -> None:
        self.relevance_gate = relevance_gate or RelevanceGate()

    def search(
        self,
        chunks: list[DocumentChunk],
        query: str,
        top_k: int = 5,
    ) -> ContractRetrievalResult:
        if not chunks or not query.strip() or top_k <= 0:
            return ContractRetrievalResult()
        query_terms = self._tokens(query)
        if not query_terms:
            return ContractRetrievalResult()
        indexed_texts = [self._indexed_text(chunk, chunks) for chunk in chunks]
        documents = [self._tokens(text) for text in indexed_texts]
        average_length = sum(map(len, documents)) / max(1, len(documents))
        document_frequency = Counter(term for terms in documents for term in set(terms))
        raw_scores: list[tuple[int, float]] = []
        for index, terms in enumerate(documents):
            counts = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                inverse = math.log(
                    1 + (len(documents) - document_frequency[term] + 0.5)
                    / (document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.5 * (
                    1 - 0.75 + 0.75 * len(terms) / max(1.0, average_length)
                )
                score += inverse * frequency * 2.5 / denominator
            if score > 0:
                raw_scores.append((index, score))
        raw_scores.sort(key=lambda item: (-item[1], item[0]))
        maximum = raw_scores[0][1] if raw_scores else 1.0
        candidates: list[ContractRetrievalHit] = []
        usable: list[ContractRetrievalHit] = []
        for index, score in raw_scores:
            chunk = chunks[index]
            decision = self.relevance_gate.evaluate(
                query,
                indexed_texts[index],
                score,
                self._tokens,
            )
            hit = ContractRetrievalHit(
                chunk_id=chunk.chunk_id,
                section=chunk.section,
                page_no=chunk.page_no,
                anchor=chunk.anchor,
                score=round(score / maximum, 4),
                raw_bm25_score=round(score, 6),
                query_coverage=round(decision.query_coverage, 6),
                matched_terms=list(decision.matched_terms),
                is_usable=decision.is_usable,
                relevance_status=decision.status,
                text=chunk.text,
            )
            candidates.append(hit)
            if hit.is_usable and len(usable) < top_k:
                usable.append(hit)
        return ContractRetrievalResult(
            candidates=candidates,
            hits=usable,
            rejection_count=sum(not hit.is_usable for hit in candidates),
        )

    def retrieve(
        self,
        chunks: list[DocumentChunk],
        query: str,
        top_k: int = 5,
    ) -> list[ContractRetrievalHit]:
        """Backward-compatible convenience method returning usable hits only."""
        return self.search(chunks, query, top_k).hits

    @classmethod
    def _indexed_text(cls, chunk: DocumentChunk, chunks: list[DocumentChunk]) -> str:
        context = [chunk.section]
        anchor = chunk.anchor
        if anchor and anchor.anchor_type == "table_cell" and anchor.row_index and anchor.row_index > 0:
            header = next(
                (
                    item.text
                    for item in chunks
                    if item.anchor
                    and item.anchor.anchor_type == "table_cell"
                    and item.anchor.table_index == anchor.table_index
                    and item.anchor.row_index == 0
                    and item.anchor.cell_index == anchor.cell_index
                ),
                "",
            )
            if header:
                context.append(header)
        context.append(chunk.text)
        return " ".join(context)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for run in re.findall(r"[\u4e00-\u9fff]+", text):
            tokens.extend(run[index : index + 2] for index in range(max(0, len(run) - 1)))
            tokens.extend(run[index : index + 3] for index in range(max(0, len(run) - 2)))
        tokens.extend(re.findall(r"\d+日|第\d+条", text))
        return tokens
