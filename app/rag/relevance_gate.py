"""Deterministic relevance gate shared by legal and contract retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


Tokenize = Callable[[str], list[str]]


@dataclass(frozen=True)
class RelevanceDecision:
    is_usable: bool
    status: str
    raw_score: float
    query_coverage: float
    matched_terms: tuple[str, ...]
    meaningful_terms: tuple[str, ...]
    reason: str


class RelevanceGate:
    """Reject candidates supported only by negligible or generic lexical overlap.

    The score floor is calibrated below the minimum positive relevant raw BM25
    observed in retrieval_v2 (0.462265) and above the ambiguous legal negative
    top score (0.012866). Contract negatives overlap positive raw scores, so a
    second signal requires at least one non-generic matched term.
    """

    minimum_raw_bm25 = 0.2
    generic_terms = frozenset({"合同", "条款", "期限"})

    def evaluate(
        self,
        query: str,
        candidate_text: str,
        raw_score: float,
        tokenizer: Tokenize,
    ) -> RelevanceDecision:
        query_terms = set(tokenizer(query))
        candidate_terms = set(tokenizer(candidate_text))
        matched = tuple(sorted(query_terms & candidate_terms))
        meaningful = tuple(term for term in matched if term not in self.generic_terms)
        coverage = len(matched) / len(query_terms) if query_terms else 0.0
        if raw_score < self.minimum_raw_bm25:
            return RelevanceDecision(
                False,
                "rejected_low_score",
                raw_score,
                coverage,
                matched,
                meaningful,
                f"raw_bm25={raw_score:.6f} below calibrated floor {self.minimum_raw_bm25:.6f}",
            )
        if not meaningful:
            return RelevanceDecision(
                False,
                "rejected_generic_overlap",
                raw_score,
                coverage,
                matched,
                meaningful,
                "candidate matches only generic retrieval terms",
            )
        return RelevanceDecision(
            True,
            "usable",
            raw_score,
            coverage,
            matched,
            meaningful,
            "raw score and meaningful lexical overlap passed",
        )
