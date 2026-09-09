"""Knowledge-base loader and semantic lookup tool."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.kb import KBChunk, RetrievalHit, RetrievalResult
from app.tools.embeddings import HashingEmbedder
from app.tools.vector_search_tool import VectorSearchTool


class KnowledgeBaseTool:
    """Loads controlled KB chunks and searches them with source metadata.

    The demo KB is stored under data/legal_kb and every record is marked
    is_demo_sample=True so downstream consumers cannot mistake it for a
    verified legal source.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        embedder: HashingEmbedder | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedder = embedder or HashingEmbedder()
        self.chunks: list[KBChunk] = []
        self.search_tool = VectorSearchTool()
        self.load_warnings: list[str] = []
        self.loaded_paths: list[str] = []
        self.reload()

    def reload(self) -> None:
        self.load_warnings.clear()
        self.loaded_paths.clear()
        records = self._load_files()
        self.chunks = records
        if not self.chunks:
            self.load_warnings.append("data/legal_kb 中没有可用知识库记录。")
        vectors = self.embedder.embed_batch([chunk.content for chunk in self.chunks])
        self.search_tool.rebuild(vectors)

    def _load_files(self) -> list[KBChunk]:
        kb_dir = Path(self.settings.legal_kb_dir)
        if not kb_dir.exists():
            return []
        records: list[KBChunk] = []
        for path in sorted(kb_dir.glob("*")):
            suffix = path.suffix.lower()
            if suffix not in {".json", ".jsonl"}:
                continue
            raw_records = self._parse_file(path)
            for index, raw in enumerate(raw_records):
                try:
                    record = self._to_kb_chunk(raw, path, index)
                    records.append(record)
                except Exception as exc:  # noqa: BLE001 - record-level validation issue
                    self.load_warnings.append(f"{path.name} 第 {index + 1} 条元数据不完整：{exc}")
            self.loaded_paths.append(str(path))
        return records

    @staticmethod
    def _parse_file(path: Path) -> list[dict]:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"无法读取 {path.name}：{exc}") from exc
        if path.suffix.lower() == ".jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        data = json.loads(text)
        if isinstance(data, dict):
            return data.get("records", [])
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _to_kb_chunk(raw: dict, path: Path, index: int) -> KBChunk:
        document_id = str(raw.get("document_id") or raw.get("id") or f"{path.stem}-{index + 1}")
        article_no = str(raw.get("article_no") or f"示例第{index + 1}条")
        content = str(raw.get("content") or raw.get("article_text") or "").strip()
        if not content:
            raise ValueError("content 为空")
        chunk_id = f"{document_id}-{article_no}"
        return KBChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            title=str(raw.get("title") or raw.get("law_title") or f"DEMO/SAMPLE {path.stem}"),
            article_no=article_no,
            content=content,
            source=str(raw.get("source") or raw.get("issuing_authority") or "DEMO/SAMPLE"),
            source_url=str(raw["source_url"]) if raw.get("source_url") else None,
            issuing_authority=str(raw.get("issuing_authority") or "DEMO/SAMPLE（非官方发布机关）"),
            effective_date=str(raw["effective_date"]) if raw.get("effective_date") else None,
            expiry_date=str(raw["expiry_date"]) if raw.get("expiry_date") else None,
            domain=str(raw.get("domain") or raw.get("legal_domain") or "contract"),
            jurisdiction=str(raw.get("jurisdiction") or "unknown"),
            source_type=str(raw.get("source_type") or "demo_sample"),
            version=str(raw.get("version") or "0.1-demo"),
            status=str(raw.get("status") or "effective"),
            is_demo_sample=bool(raw.get("is_demo_sample", True)),
            updated_at=str(raw["updated_at"]) if raw.get("updated_at") else None,
        )

    def search(
        self,
        query: str,
        top_k: int = 4,
        domain: str | None = None,
        min_score: float = 0.02,
        metadata_filter: dict[str, object] | None = None,
    ) -> RetrievalResult:
        candidates = self.chunks
        filters_applied: list[str] = []
        metadata_filter = metadata_filter or {}
        allowed_status = metadata_filter.get("status")
        if allowed_status:
            allowed = set(allowed_status) if isinstance(allowed_status, (list, tuple, set)) else {allowed_status}
            allowed = {item.value if hasattr(item, "value") else str(item) for item in allowed}
            candidates = [chunk for chunk in candidates if chunk.status in allowed]
            filters_applied.append(f"status={','.join(sorted(allowed))}")
        source_type = metadata_filter.get("source_type")
        if source_type:
            source_types = (
                set(source_type)
                if isinstance(source_type, (list, tuple, set))
                else {source_type}
            )
            source_types = {item.value if hasattr(item, "value") else str(item) for item in source_types}
            candidates = [chunk for chunk in candidates if chunk.source_type in source_types]
            filters_applied.append("source_type filter")
        jurisdiction = metadata_filter.get("jurisdiction")
        if jurisdiction:
            jurisdiction_value = jurisdiction.value if hasattr(jurisdiction, "value") else str(jurisdiction)
            candidates = [chunk for chunk in candidates if chunk.jurisdiction == jurisdiction_value]
            filters_applied.append(f"jurisdiction={jurisdiction_value}")
        if domain:
            domain_value = domain.value if hasattr(domain, "value") else str(domain)
            candidates = [chunk for chunk in candidates if chunk.domain == domain_value]
            filters_applied.append(f"domain={domain_value}")
        candidates = [chunk for chunk in candidates if self._usable(chunk)]
        if filters_applied:
            filters_applied.append("validity=effective-not-expired")
        if not candidates:
            return RetrievalResult(
                hits=[],
                used_fallback=not self.search_tool.used_faiss,
                total_candidates=0,
                filters_applied=filters_applied,
                evidence_insufficient_reason="metadata filter 后无可用知识库候选。",
            )
        query_vector = self.embedder.embed(query)
        all_vectors = self.embedder.embed_batch([chunk.content for chunk in candidates])
        temp_tool = VectorSearchTool()
        temp_tool.rebuild(all_vectors)
        dense_scored = temp_tool.search(query_vector, top_k=len(candidates))
        dense_scores = {item.index: max(0.0, min(1.0, item.score)) for item in dense_scored}
        keyword_raw = self._bm25_scores(query, candidates)
        max_keyword = max(keyword_raw.values(), default=0.0) or 1.0
        keyword_scores = {index: value / max_keyword for index, value in keyword_raw.items()}
        dense_rank = {item.index: rank for rank, item in enumerate(dense_scored, 1)}
        keyword_order = sorted(keyword_scores, key=keyword_scores.get, reverse=True)
        keyword_rank = {index: rank for rank, index in enumerate(keyword_order, 1)}
        rrf_k = 60
        fusion_raw = {
            index: (1 / (rrf_k + dense_rank[index])) + (1 / (rrf_k + keyword_rank[index]))
            for index in range(len(candidates))
        }
        max_fusion = max(fusion_raw.values(), default=1.0)
        fused = sorted(fusion_raw, key=fusion_raw.get, reverse=True)[:top_k]
        hits: list[RetrievalHit] = []
        for rank, index in enumerate(fused, 1):
            score = fusion_raw[index] / max_fusion
            if score < min_score:
                continue
            chunk = candidates[index]
            keyword_score = keyword_scores.get(index, 0.0)
            dense_score = dense_scores.get(index, 0.0)
            reason = self._match_reason(query, chunk, keyword_score, dense_score)
            validity = self._validity_status(chunk)
            hits.append(
                RetrievalHit(
                    chunk=chunk,
                    score=round(score, 4),
                    similarity_score=round(dense_score, 4),
                    keyword_score=round(keyword_score, 4),
                    dense_score=round(dense_score, 4),
                    fusion_score=round(score, 4),
                    rank=rank,
                    matched_text=chunk.content[:180],
                    match_reason=reason,
                    metadata={
                        "document_id": chunk.document_id,
                        "article_no": chunk.article_no,
                        "legal_domain": chunk.domain,
                        "jurisdiction": chunk.jurisdiction,
                        "effective_date": chunk.effective_date or "unknown",
                        "expiry_date": chunk.expiry_date or "none",
                        "source_type": chunk.source_type,
                        "version": chunk.version,
                    },
                    validity_status=validity,
                )
            )
        insufficient = None
        if not hits:
            insufficient = "没有高于阈值的法规命中。"
        elif any(hit.validity_status not in {"current", "effective"} for hit in hits):
            insufficient = "部分/全部依据已过期、失效或状态不明，不能作为强证据。"
        return RetrievalResult(
            hits=hits,
            used_fallback=not temp_tool.used_faiss,
            total_candidates=len(candidates),
            filters_applied=filters_applied,
            evidence_insufficient_reason=insufficient,
            query=query,
            queries=[query],
            metadata_filters=metadata_filter,
            keyword_hits=[candidates[index].chunk_id for index in keyword_order[:top_k]],
            dense_hits=[candidates[item.index].chunk_id for item in dense_scored[:top_k]],
            fusion_method="rrf-k60",
            top_k=top_k,
        )

    @staticmethod
    def _validity_status(chunk: KBChunk) -> str:
        if chunk.expiry_date:
            try:
                if date.fromisoformat(chunk.expiry_date) < date.today():
                    return "expired"
            except ValueError:
                pass
        if chunk.status in {"current", "effective"}:
            return chunk.status
        if chunk.status in {"expired", "deprecated"}:
            return chunk.status
        return "unknown"

    @staticmethod
    def _usable(chunk: KBChunk) -> bool:
        return KnowledgeBaseTool._validity_status(chunk) in {"current", "effective"}

    @staticmethod
    def _match_reason(query: str, chunk: KBChunk, keyword_score: float, dense_score: float) -> str:
        text = f"{chunk.title} {chunk.article_no} {chunk.content}".lower()
        article_exact = bool(chunk.article_no and chunk.article_no.lower() in query.lower())
        if article_exact:
            return f"精确命中条款编号 {chunk.article_no}，并通过 metadata 有效性过滤"
        terms = [token for token in KnowledgeBaseTool._tokens(query) if len(token) > 1]
        matched = [token for token in terms if token in text][:3]
        if keyword_score >= dense_score and matched:
            return f"关键词命中：{'、'.join(dict.fromkeys(matched))}；经 BM25 + dense RRF 融合"
        if matched:
            return f"语义与关键词共同匹配：{'、'.join(dict.fromkeys(matched))}"
        return "dense 语义匹配；经 RRF 与关键词结果融合"

    @staticmethod
    def _tokens(text: str) -> list[str]:
        tokens: list[str] = re.findall(r"[a-z0-9]+", text.lower())
        for run in re.findall(r"[\u4e00-\u9fff]+", text):
            tokens.extend(run[index : index + 2] for index in range(max(0, len(run) - 1)))
            tokens.extend(run[index : index + 3] for index in range(max(0, len(run) - 2)))
        tokens.extend(re.findall(r"第\d+条", text))
        return tokens

    @classmethod
    def _bm25_scores(cls, query: str, candidates: list[KBChunk]) -> dict[int, float]:
        documents = [cls._tokens(f"{chunk.title} {chunk.article_no} {chunk.content}") for chunk in candidates]
        query_terms = cls._tokens(query)
        if not query_terms:
            return {index: 0.0 for index in range(len(candidates))}
        average_length = sum(map(len, documents)) / max(1, len(documents))
        document_frequency = Counter(term for terms in documents for term in set(terms))
        scores: dict[int, float] = {}
        for index, terms in enumerate(documents):
            counts = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                inverse = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
                denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(terms) / max(1.0, average_length))
                score += inverse * frequency * 2.5 / denominator
            chunk = candidates[index]
            if chunk.article_no and chunk.article_no.lower() in query.lower():
                score += 8.0
            scores[index] = score
        return scores


class KnowledgeBaseLookupError(RuntimeError):
    pass
