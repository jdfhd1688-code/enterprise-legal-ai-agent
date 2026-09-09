"""Offline Hit@K, Recall@K, and MRR evaluation for the demo Legal KB."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings, get_settings
from app.tools.knowledge_base_tool import KnowledgeBaseTool


class RetrievalEvaluator:
    def __init__(self, settings: Settings | None = None, kb_tool: KnowledgeBaseTool | None = None) -> None:
        self.settings = settings or get_settings()
        self.kb_tool = kb_tool or KnowledgeBaseTool(self.settings)

    def load_items(self, path: Path | None = None) -> list[dict]:
        source = path or Path(self.settings.eval_dir) / "legal_retrieval_eval.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        return data.get("items", data if isinstance(data, list) else [])

    def evaluate(self, items: list[dict] | None = None) -> dict[str, float | int]:
        dataset = items or self.load_items()
        hit_counts = {1: 0, 3: 0, 5: 0}
        reciprocal_rank = 0.0
        for item in dataset:
            result = self.kb_tool.search(
                item["query"],
                top_k=5,
                domain=item.get("legal_domain"),
                metadata_filter={"jurisdiction": "中国大陆", "status": ["current", "effective"], "source_type": "demo_sample"},
            )
            ranked = [(hit.chunk.title, hit.chunk.article_no) for hit in result.hits]
            expected = (item["expected_law_title"], item["expected_article_no"])
            for k in hit_counts:
                hit_counts[k] += int(expected in ranked[:k])
            if expected in ranked:
                reciprocal_rank += 1 / (ranked.index(expected) + 1)
        total = max(1, len(dataset))
        return {
            "queries": len(dataset),
            "hit_at_1": round(hit_counts[1] / total, 4),
            "hit_at_3": round(hit_counts[3] / total, 4),
            "hit_at_5": round(hit_counts[5] / total, 4),
            "recall_at_5": round(hit_counts[5] / total, 4),
            "mrr": round(reciprocal_rank / total, 4),
        }
