"""Explainable hybrid Legal RAG retrieval skill."""

from __future__ import annotations

from app.agent.review_planner import DIMENSION_DOMAIN
from app.mcp.adapters import RegistryHub
from app.rag.query_builder import LegalRetrievalQueryBuilder
from app.schemas.document import DocumentChunk, ParsedDocument
from app.schemas.kb import RetrievalHit, RetrievalResult
from app.tools.knowledge_base_tool import KnowledgeBaseTool


class RetrievalSkill:
    """Run metadata filtering, BM25-like keyword search, dense search and RRF."""

    def __init__(self, kb_tool: KnowledgeBaseTool | None = None, top_k: int = 5) -> None:
        self.kb_tool = kb_tool or KnowledgeBaseTool()
        self.top_k = top_k
        self.query_builder = LegalRetrievalQueryBuilder()

    def retrieve(
        self,
        parsed: ParsedDocument,
        chunks: list[DocumentChunk],
        question: str,
        review_dimension: str = "general_contract",
        jurisdiction: str = "中国大陆",
    ) -> RetrievalResult:
        contract_excerpt = " ".join(chunk.text[:320] for chunk in chunks[:5]) or parsed.title
        built = self.query_builder.build(question, contract_excerpt, review_dimension, jurisdiction)
        query_variants = [built.query]
        for chunk in chunks[:4]:
            variant = self.query_builder.build(question, chunk.text[:420], review_dimension, jurisdiction).query
            if variant not in query_variants:
                query_variants.append(variant)

        combined_hits: dict[str, RetrievalHit] = {}
        keyword_hits: list[str] = []
        dense_hits: list[str] = []
        domain = None if review_dimension == "general_contract" else DIMENSION_DOMAIN.get(review_dimension, "contract")
        for query in query_variants:
            result = self.kb_tool.search(
                query,
                top_k=self.top_k,
                min_score=0.02,
                domain=domain,
                metadata_filter=built.metadata_filters,
            )
            keyword_hits.extend(result.keyword_hits)
            dense_hits.extend(result.dense_hits)
            for hit in result.hits:
                existing = combined_hits.get(hit.chunk.chunk_id)
                if existing is None or hit.fusion_score > existing.fusion_score:
                    combined_hits[hit.chunk.chunk_id] = hit

        hits = sorted(combined_hits.values(), key=lambda hit: hit.fusion_score, reverse=True)[:8]
        for rank, hit in enumerate(hits, 1):
            hit.rank = rank
        hub = RegistryHub()
        hub.search_all(built.query)  # mock-only probe; results are never injected
        mcp_calls = [call for adapter in hub.adapters for call in adapter.get_tool_call_log()]
        insufficient = None if hits else "没有命中的现行有效法规（DEMO/SAMPLE 知识库）。"
        filters = ["status=current,effective", "jurisdiction=中国大陆", "source_type=demo_sample"]
        if domain:
            filters.append(f"domain={domain}")
        return RetrievalResult(
            hits=hits,
            used_fallback=True,
            total_candidates=len(self.kb_tool.chunks),
            filters_applied=filters,
            mcp_calls=mcp_calls,
            evidence_insufficient_reason=insufficient,
            query=built.query,
            queries=query_variants,
            metadata_filters=built.metadata_filters,
            keyword_hits=list(dict.fromkeys(keyword_hits))[: self.top_k],
            dense_hits=list(dict.fromkeys(dense_hits))[: self.top_k],
            fusion_method="rrf-k60",
            top_k=len(hits),
            jurisdiction_assumption="中国大陆（DEMO 默认辖区，未由用户确认）",
        )
