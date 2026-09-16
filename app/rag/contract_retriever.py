"""Deterministic lexical ranking over chunks from one parsed contract."""

from __future__ import annotations

import math
import re
from collections import Counter

from pydantic import BaseModel, Field

from app.schemas.document import DocumentAnchor, DocumentChunk


class ContractRetrievalHit(BaseModel):
    chunk_id: str
    section: str
    page_no: int | None = None
    anchor: DocumentAnchor | None = None
    score: float = Field(ge=0.0, le=1.0)
    text: str


class ContractRetriever:
    """A small BM25-style retriever with no model or expected-answer lookup."""

    @classmethod
    def retrieve(
        cls,
        chunks: list[DocumentChunk],
        query: str,
        top_k: int = 5,
    ) -> list[ContractRetrievalHit]:
        if not chunks or not query.strip() or top_k <= 0:
            return []
        query_terms = cls._tokens(query)
        if not query_terms:
            return []
        documents = [cls._tokens(f"{chunk.section} {chunk.text}") for chunk in chunks]
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
        hits: list[ContractRetrievalHit] = []
        for index, score in raw_scores[:top_k]:
            chunk = chunks[index]
            hits.append(
                ContractRetrievalHit(
                    chunk_id=chunk.chunk_id,
                    section=chunk.section,
                    page_no=chunk.page_no,
                    anchor=chunk.anchor,
                    score=round(score / maximum, 4),
                    text=chunk.text,
                )
            )
        return hits

    @staticmethod
    def _tokens(text: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for run in re.findall(r"[\u4e00-\u9fff]+", text):
            tokens.extend(run[index : index + 2] for index in range(max(0, len(run) - 1)))
            tokens.extend(run[index : index + 3] for index in range(max(0, len(run) - 2)))
        tokens.extend(re.findall(r"\d+日|第\d+条", text))
        return tokens
