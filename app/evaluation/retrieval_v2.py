"""Retrieval v2 evaluation with corrected macro recall and explicit negatives."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.evaluation.contracts import EvaluationFailure, EvaluatorOutput
from app.evaluation.dataset_loader import LoadedDataset
from app.evaluation.dataset_models import DatasetType, QueryType, RetrievalEvalCase
from app.rag.contract_retriever import ContractRetriever
from app.skills.chunker import ChunkerSkill
from app.skills.document_parser import DocumentParserSkill
from app.tools.knowledge_base_tool import KnowledgeBaseTool


@dataclass(frozen=True)
class RetrievalCaseOutcome:
    case: RetrievalEvalCase
    retrieved_ids: list[str]


def calculate_metrics(outcomes: list[RetrievalCaseOutcome]) -> dict[str, float | int]:
    positives = [item for item in outcomes if not item.case.expected_no_relevant_result]
    negatives = [item for item in outcomes if item.case.expected_no_relevant_result]
    hit_counts = {1: 0, 3: 0, 5: 0}
    recall_at_5 = 0.0
    reciprocal_rank = 0.0
    for outcome in positives:
        expected = set(outcome.case.expected_doc_ids)
        for k in hit_counts:
            hit_counts[k] += int(bool(expected.intersection(outcome.retrieved_ids[:k])))
        recall_at_5 += len(expected.intersection(outcome.retrieved_ids[:5])) / len(expected)
        first_rank = next(
            (rank for rank, item in enumerate(outcome.retrieved_ids, 1) if item in expected),
            None,
        )
        if first_rank is not None:
            reciprocal_rank += 1 / first_rank
    positive_total = len(positives)
    correct_negatives = sum(not outcome.retrieved_ids for outcome in negatives)
    negative_total = len(negatives)
    return {
        "positive_case_count": positive_total,
        "hit_at_1": round(hit_counts[1] / positive_total, 4) if positive_total else 0.0,
        "hit_at_3": round(hit_counts[3] / positive_total, 4) if positive_total else 0.0,
        "hit_at_5": round(hit_counts[5] / positive_total, 4) if positive_total else 0.0,
        "recall_at_5": round(recall_at_5 / positive_total, 4) if positive_total else 0.0,
        "mrr": round(reciprocal_rank / positive_total, 4) if positive_total else 0.0,
        "negative_case_count": negative_total,
        "correct_no_relevant_count": correct_negatives,
        "negative_accuracy": round(correct_negatives / negative_total, 4) if negative_total else 0.0,
    }


class RetrievalV2Evaluator:
    name = "retrieval_v2"
    version = "retrieval-v2.0"

    def __init__(
        self,
        project_root: Path | None = None,
        kb_tool: KnowledgeBaseTool | None = None,
        contract_retriever: ContractRetriever | None = None,
    ) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parents[2]).resolve()
        self.kb_tool = kb_tool or KnowledgeBaseTool()
        self.contract_retriever = contract_retriever or ContractRetriever()
        self._contract_cache: dict[Path, list] = {}

    def evaluate(self, dataset: LoadedDataset) -> EvaluatorOutput:
        if dataset.metadata.dataset_type != DatasetType.retrieval:
            raise ValueError("retrieval_v2 requires a retrieval dataset")
        cases = [case for case in dataset.cases if isinstance(case, RetrievalEvalCase)]
        if len(cases) != len(dataset.cases):
            raise ValueError("retrieval_v2 dataset contains non-retrieval cases")
        outcomes = [
            RetrievalCaseOutcome(case=case, retrieved_ids=self._retrieve(case)) for case in cases
        ]
        metrics = calculate_metrics(outcomes)
        by_type: dict[str, list[RetrievalCaseOutcome]] = defaultdict(list)
        by_domain: dict[str, list[RetrievalCaseOutcome]] = defaultdict(list)
        for outcome in outcomes:
            by_type[outcome.case.query_type.value].append(outcome)
            if outcome.case.legal_domain:
                by_domain[outcome.case.legal_domain].append(outcome)
        for query_type, group in sorted(by_type.items()):
            metrics.update(self._prefixed(f"type.{query_type}", calculate_metrics(group)))
        for domain, group in sorted(by_domain.items()):
            metrics.update(self._prefixed(f"domain.{domain}", calculate_metrics(group)))
        failures = [failure for outcome in outcomes if (failure := self._failure(outcome))]
        return EvaluatorOutput(
            status="completed",
            case_count=len(outcomes),
            metrics=metrics,
            failures=failures,
            warnings=[
                "Retrieval metrics describe only this DEMO/SYNTHETIC dataset and KB.",
                "Legacy Recall@5 used Hit@5 semantics and is not directly comparable to corrected v2 Recall@5.",
            ],
        )

    def _retrieve(self, case: RetrievalEvalCase) -> list[str]:
        if case.query_type == QueryType.legal:
            result = self.kb_tool.search(
                case.query,
                top_k=5,
                domain=case.legal_domain,
                metadata_filter={
                    "jurisdiction": case.jurisdiction or "中国大陆",
                    "status": ["current", "effective"],
                    "source_type": "demo_sample",
                },
            )
            return [hit.chunk.chunk_id for hit in result.hits]
        if not case.corpus_path:
            raise ValueError(f"Contract case {case.id} requires corpus_path")
        corpus = (self.project_root / case.corpus_path).resolve()
        if self.project_root not in corpus.parents or not corpus.is_file():
            raise ValueError(f"Contract corpus path is missing or unsafe: {case.corpus_path}")
        chunks = self._contract_cache.get(corpus)
        if chunks is None:
            parsed = DocumentParserSkill().parse(corpus.name, corpus.read_bytes())
            chunks = ChunkerSkill().chunk(parsed)
            self._contract_cache[corpus] = chunks
        return [
            hit.chunk_id for hit in self.contract_retriever.retrieve(chunks, case.query, top_k=5)
        ]

    @staticmethod
    def _prefixed(prefix: str, metrics: dict[str, float | int]) -> dict[str, float | int]:
        return {f"{prefix}.{key}": value for key, value in metrics.items()}

    @staticmethod
    def _failure(outcome: RetrievalCaseOutcome) -> EvaluationFailure | None:
        case = outcome.case
        if case.expected_no_relevant_result:
            if not outcome.retrieved_ids:
                return None
            return EvaluationFailure(
                case_id=case.id,
                reason=(
                    f"negative query returned usable results; query={case.query!r}; "
                    f"retrieved={outcome.retrieved_ids[:5]}"
                ),
            )
        missing = [item for item in case.expected_doc_ids if item not in outcome.retrieved_ids[:5]]
        if not missing:
            return None
        expected = set(case.expected_doc_ids)
        first_rank = next(
            (rank for rank, item in enumerate(outcome.retrieved_ids, 1) if item in expected),
            None,
        )
        return EvaluationFailure(
            case_id=case.id,
            reason=(
                f"relevant evidence missing from top 5; query={case.query!r}; "
                f"expected={case.expected_doc_ids}; retrieved={outcome.retrieved_ids[:5]}; "
                f"first_relevant_rank={first_rank}; missing={missing}"
            ),
        )
