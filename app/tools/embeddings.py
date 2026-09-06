"""Deterministic local embeddings and optional provider interface.

The hashing embedder keeps the demo fully offline. FAISS/numpy cosine search
then operates on those vectors. If a real embedding endpoint is configured,
the service may replace this embedder without changing the pipeline.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

Vector = list[float]

_LETTER_NUMBER = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")


class HashingEmbedder:
    """Feature-hash embedder suitable for Chinese and English demo text."""

    dimension = 256

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def _features(self, text: str) -> list[str]:
        lowered = text.lower()
        features: list[str] = []
        features.extend(_LETTER_NUMBER.findall(lowered))
        for run in _CJK_RUN.findall(lowered):
            features.extend(list(run))
            for size in (2, 3, 4):
                features.extend(
                    run[index : index + size] for index in range(max(0, len(run) - size + 1))
                )
        return features

    def embed(self, text: str) -> Vector:
        vector = [0.0] * self.dimension
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[Vector]:
        return [self.embed(text) for text in texts]


def default_token_vector(text: str, dimension: int = 512) -> list[float]:
    """Small lexical vector used for keyword overlap without numpy."""
    counts: dict[int, float] = defaultdict(float)
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    for token in tokens:
        for size in (1, 2):
            for index in range(max(0, len(token) - size + 1)):
                piece = token[index : index + size]
                bucket = int(hashlib.blake2b(piece.encode("utf-8"), digest_size=4).hexdigest(), 16)
                counts[bucket % dimension] += 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return [counts.get(index, 0.0) / norm for index in range(dimension)]

