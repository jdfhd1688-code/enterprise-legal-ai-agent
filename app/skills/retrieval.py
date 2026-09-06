"""RAG retrieval skill that combines contract text with KB lookups."""

from __future__ import annotations

from app.schemas.document import DocumentChunk, ParsedDocument
from app.schemas.kb import RetrievalHit, RetrievalResult
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from app.agent.review_planner import DIMENSION_DOMAIN
from app.mcp.adapters import RegistryHub


class RetrievalSkill:
    """Retrieves legal-kb references for the question and each contract chunk."""

    def __init__(self, kb_tool: KnowledgeBaseTool | None = None, top_k: int = 3) -> None:
        self.kb_tool = kb_tool or KnowledgeBaseTool()
        self.top_k = top_k

    def retrieve(
        self,
        parsed: ParsedDocument,
        chunks: list[DocumentChunk],
        question: str,
        review_dimension: str = "general_contract",
    ) -> RetrievalResult:
        queries = [question, parsed.title]
        queries.extend(chunk.text[:400] for chunk in chunks[:6])
        combined_hits: dict[str, RetrievalHit] = {}
        domain = DIMENSION_DOMAIN.get(review_dimension, "contract")
        metadata_filter = {
            "status": ["current", "effective"],
            "source_type": "demo_sample",
        }
        hub = RegistryHub()
        hub.search_all(question)  # mock-only probe, results are never injected
        for query in queries:
            if not query.strip():
                continue
            result = self.kb_tool.search(
                query,
                top_k=self.top_k,
                min_score=0.02,
                domain=domain,
                metadata_filter=metadata_filter,
            )
            for hit in result.hits:
                existing = combined_hits.get(hit.chunk.chunk_id)
                if existing is None or hit.score > existing.score:
                    combined_hits[hit.chunk.chunk_id] = hit
        hits = sorted(combined_hits.values(), key=lambda hit: hit.score, reverse=True)[:8]
        mcp_calls = [
            call for adapter in hub.adapters for call in adapter.get_tool_call_log()
        ]
        insufficient = None
        if not hits:
            insufficient = "没有命中的现行有效法规（DEMO 知识库）。"
        elif any(hit.validity_status not in {"current", "effective"} for hit in hits):
            insufficient = "存在过期/未知状态的法规命中，不能作为确定性法律结论。"
        return RetrievalResult(
            hits=hits,
            used_fallback=all(hit.chunk.is_demo_sample for hit in hits),
            total_candidates=len(hits),
            filters_applied=["status=current,effective", f"domain={domain}", "source_type=demo_sample"],
            mcp_calls=mcp_calls,
            evidence_insufficient_reason=insufficient,
        )
