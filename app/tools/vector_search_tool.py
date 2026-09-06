"""Local vector-search tool with FAISS-first and numpy fallback."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover - requirements install numpy
    np = None  # type: ignore


@dataclass
class ScoredDoc:
    index: int
    score: float


@dataclass
class VectorSearchTool:
    """Holds normalized vectors and searches by cosine similarity."""

    vectors: list[list[float]] = field(default_factory=list)
    _faiss_index: object | None = None
    used_faiss: bool = False

    def rebuild(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self._faiss_index = None
        self.used_faiss = False
        if not vectors or np is None:
            return
        try:
            import faiss  # type: ignore

            matrix = np.asarray(vectors, dtype="float32")
            dimension = matrix.shape[1]
            index = faiss.IndexFlatIP(dimension)  # type: ignore
            index.add(matrix)
            self._faiss_index = index
            self.used_faiss = True
        except Exception:  # noqa: BLE001 - numpy fallback is fully supported
            self._faiss_index = None
            self.used_faiss = False

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredDoc]:
        if not self.vectors:
            return []
        if np is None:
            return self._bruteforce_python(query_vector, top_k)
        query = np.asarray(query_vector, dtype="float32")
        if self._faiss_index is not None:
            scores, indices = self._faiss_index.search(query.reshape(1, -1), min(top_k, len(self.vectors)))
            rows = [
                ScoredDoc(index=int(indices[0][pos]), score=float(scores[0][pos]))
                for pos in range(len(indices[0]))
                if int(indices[0][pos]) >= 0
            ]
            rows.sort(key=lambda row: row.score, reverse=True)
            return rows
        matrix = np.asarray(self.vectors, dtype="float32")
        scores = matrix.dot(query)
        order = scores.argsort()[::-1][:top_k]
        return [ScoredDoc(index=int(idx), score=float(scores[idx])) for idx in order]

    def _bruteforce_python(self, query_vector: list[float], top_k: int) -> list[ScoredDoc]:
        scored: list[ScoredDoc] = []
        for index, vector in enumerate(self.vectors):
            dot = sum(a * b for a, b in zip(vector, query_vector))
            norm = math.sqrt(sum(v * v for v in vector))
            q_norm = math.sqrt(sum(v * v for v in query_vector)) or 1.0
            score = dot / (norm * q_norm) if norm else 0.0
            scored.append(ScoredDoc(index=index, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

