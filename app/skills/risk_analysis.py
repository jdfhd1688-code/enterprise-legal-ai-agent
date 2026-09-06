"""Risk analysis skill.

DEMO MODE uses a transparent keyword/rule engine so the entire pipeline runs
offline and deterministically. When ENABLE_REAL_LLM=true and an API key is
configured, the same structured JSON is requested from an OpenAI-compatible
provider and then validated by the same schema guard.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.agent.prompts import SYSTEM_PROMPT, build_analysis_user_prompt
from app.agent.review_planner import DIMENSION_DOMAIN, DIMENSION_LABELS
from app.config import Settings, get_settings
from app.schemas.document import DocumentChunk, ParsedDocument
from app.schemas.kb import RetrievalResult
from app.schemas.risk import Finding, LegalBasis, RiskAnalysis, RiskLevel, Severity
from app.tools.llm_client import LLMClientError, OpenAICompatibleClient


class RiskAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class RiskRule:
    pattern: str
    risk_type: str
    severity: Severity
    issue: str
    recommendation: str
    kb_terms: tuple[str, ...] = ()


RISK_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        pattern=r"违约金|赔偿金|逾期付款|赔偿损失",
        risk_type="payment_liability",
        severity=Severity.high,
        issue="付款/违约金条款可能显著加重违约成本，违约金比例、起算日与上限需要复核。",
        recommendation="由法务核对违约金是否超出合理预期，并明确逾期计算方式、通知顺序与上限。",
        kb_terms=("违约金", "赔偿", "违约"),
    ),
    RiskRule(
        pattern=r"全部责任|无限责任|任何损失|概不负责|不承担任何",
        risk_type="liability",
        severity=Severity.high,
        issue="一方责任范围覆盖过宽或几乎无限制，可能把不可控风险转嫁给对方。",
        recommendation="建议增加责任上限、可预见的损失限定、除外情形以及因果关系限制。",
        kb_terms=("责任", "赔偿"),
    ),
    RiskRule(
        pattern=r"单方解除|任意解除|随时解除",
        risk_type="termination",
        severity=Severity.high,
        issue="合同赋予单方或任意解除权，但未清楚约定行使条件、通知期和结算安排。",
        recommendation="建议限定解除条件、通知期限、已发生费用结算和返还义务。",
        kb_terms=("解除", "违约"),
    ),
    RiskRule(
        pattern=r"自动续期|自动续约|默认续约|到期后自动",
        risk_type="auto_renewal",
        severity=Severity.medium,
        issue="自动续期条款可能造成被动延期，未明确提醒机制、退出窗口和续期价格。",
        recommendation="建议设置明确的续期提醒、退出窗口与价格调整确认流程。",
        kb_terms=("续期", "合同期限"),
    ),
    RiskRule(
        pattern=r"不可抗力",
        risk_type="force_majeure",
        severity=Severity.medium,
        issue="不可抗力条款界定较模糊，可能影响延期或免责事件发生时的责任分担。",
        recommendation="建议明确不可抗力范围、通知时限、减损义务和合同处理方式。",
        kb_terms=("不可抗力", "免责"),
    ),
    RiskRule(
        pattern=r"知识产权|著作权|商业秘密|保密义务|保密信息",
        risk_type="ip_confidentiality",
        severity=Severity.medium,
        issue="知识产权和保密范围较宽，权利归属、使用许可、返还与例外边界不够清晰。",
        recommendation="建议逐项明确背景/前景知识产权归属、许可范围、保密例外和违约处理。",
        kb_terms=("知识产权", "保密"),
    ),
    RiskRule(
        pattern=r"由[^。\n]{0,30}(?:人民法院|法院|仲裁机构)[^。\n]{0,12}管辖|"
        r"仲裁条款|双方约定管辖",
        risk_type="jurisdiction",
        severity=Severity.medium,
        issue="争议管辖约定需要结合双方主体、交易地点和争议金额做专项复核。",
        recommendation="建议法务核对管辖条款是否明确、有效并与交易结构匹配。",
        kb_terms=("管辖", "争议"),
    ),
    RiskRule(
        pattern=r"免责条款|不承担责任|除外责任",
        risk_type="exclusion_of_liability",
        severity=Severity.medium,
        issue="免责条款覆盖范围较宽，可能与合同主要义务产生冲突或影响交易预期。",
        recommendation="建议逐项确认免责范围、适用事件和风险分配是否公平合理。",
        kb_terms=("免责", "责任"),
    ),
)


def _snip(text: str, phrase_start: int, window: int = 180) -> str:
    start = max(0, phrase_start - 40)
    end = min(len(text), phrase_start + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()


class RiskAnalysisSkill:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(
        self,
        task_id: str,
        question: str,
        parsed_document: ParsedDocument,
        chunks: list[DocumentChunk],
        retrieval: RetrievalResult,
        review_dimension: str = "general_contract",
    ) -> RiskAnalysis:
        if self.settings.demo_mode:
            return self._demo_analysis(
                task_id,
                question,
                chunks,
                retrieval,
                review_dimension,
            )
        return self._llm_analysis(
            task_id,
            question,
            parsed_document,
            chunks,
            retrieval,
            review_dimension,
        )

    def _demo_analysis(
        self,
        task_id: str,
        question: str,
        chunks: list[DocumentChunk],
        retrieval: RetrievalResult,
        review_dimension: str,
    ) -> RiskAnalysis:
        findings: list[Finding] = []
        for chunk in chunks:
            if len(findings) >= 8:
                break
            rule = self._first_match(chunk.text)
            if rule is None:
                continue
            if not self._dimension_allows(review_dimension, rule.risk_type):
                continue
            match = re.search(rule.pattern, chunk.text, flags=re.IGNORECASE)
            phrase_start = match.start() if match else 0
            evidence = _snip(chunk.text, phrase_start)
            basis = self._legal_basis_for(rule, retrieval)
            finding = Finding(
                clause_id=chunk.chunk_id,
                risk_type=rule.risk_type,
                severity=rule.severity,
                issue=rule.issue,
                contract_evidence=f"[{chunk.evidence_label}] {evidence}",
                legal_basis=basis,
                recommendation=rule.recommendation,
                evidence_page=chunk.page_no,
                evidence_section=chunk.section,
                evidence_sufficient=self._finding_evidence_ok(basis),
            )
            findings.append(finding)

        risk_level = self._level_from_findings(findings)
        if not findings:
            summary = (
                f"在 {DIMENSION_LABELS.get(review_dimension, review_dimension)} 维度未检出明显风险关键词；"
                "结果仅为规则引擎初筛，仍需法务抽查确认。"
            )
            confidence = 0.88
        else:
            high_count = sum(1 for finding in findings if finding.severity == Severity.high)
            summary = (
                f"基于 {DIMENSION_LABELS.get(review_dimension, review_dimension)} 维度，"
                f"检出 {len(findings)} 个需要关注的风险项，其中高风险 {high_count} 项。"
            )
            confidence = 0.82 if high_count else 0.86
        dimension_label = DIMENSION_LABELS.get(review_dimension, review_dimension)
        legal_domain = DIMENSION_DOMAIN.get(review_dimension, "contract")
        evidence_ok = self._overall_evidence_ok(findings, retrieval)
        retrieval_summary = (
            f"检索到 {len(retrieval.hits)} 条法规命中；"
            f"证据充分={evidence_ok}"
        )

        return RiskAnalysis(
            task_id=task_id,
            risk_level=risk_level,
            legal_domain=legal_domain,
            confidence=confidence,
            summary=summary,
            findings=findings,
            review_dimension=review_dimension,
            evidence_sufficient=evidence_ok,
            retrieval_summary=retrieval_summary,
            requires_human_review=risk_level == RiskLevel.high,
            review_reason="高风险法律事项，需要人工复核" if risk_level == RiskLevel.high else None,
            generated_at=datetime.now(timezone.utc),
            analysis_mode="demo-heuristic",
            model_version="demo-heuristic-v2-review-dimensions",
        )

    @staticmethod
    def _risk_keyword(question: str) -> str:
        return "违约、付款、责任" if not question.strip() else question.strip()[:30]

    @staticmethod
    def _dimension_allows(dimension: str, risk_type: str) -> bool:
        if dimension in {"", "general_contract"}:
            return True
        mapping = {
            "delivery_liability": {"force_majeure", "termination", "auto_renewal"},
            "payment_risk": {"payment_liability", "liability"},
            "breach_liability": {"liability", "termination", "exclusion_of_liability", "payment_liability"},
            "confidentiality": {"ip_confidentiality", "exclusion_of_liability"},
            "intellectual_property": {"ip_confidentiality"},
            "dispute_resolution": {"jurisdiction"},
            "data_compliance": set(),
            "employment": set(),
        }
        return risk_type in mapping.get(dimension, set())

    @staticmethod
    def _finding_evidence_ok(basis: list[LegalBasis]) -> bool:
        if not basis:
            return False
        return all(item.status in {"current", "effective"} for item in basis)

    def _overall_evidence_ok(
        self,
        findings: list[Finding],
        retrieval: RetrievalResult,
    ) -> bool:
        if findings:
            return bool(findings) and all(finding.evidence_sufficient for finding in findings)
        return (
            bool(retrieval.hits)
            and all(hit.validity_status in {"current", "effective"} for hit in retrieval.hits)
        )

    @staticmethod
    def _level_from_findings(findings: list[Finding]):
        severities = {finding.severity for finding in findings}
        if Severity.high in severities:
            return RiskLevel.high
        if Severity.medium in severities:
            return RiskLevel.medium
        return RiskLevel.low

    @staticmethod
    def _first_match(text: str) -> RiskRule | None:
        for rule in RISK_RULES:
            if re.search(rule.pattern, text, flags=re.IGNORECASE):
                return rule
        return None

    def _legal_basis_for(self, rule: RiskRule, retrieval: RetrievalResult) -> list[LegalBasis]:
        if not retrieval.hits:
            return []
        ordered = list(retrieval.hits)
        ordered.sort(
            key=lambda hit: -max(
                (1 if any(term in f"{hit.chunk.title}{hit.chunk.content}" for term in rule.kb_terms) else 0),
                hit.score,
            )
        )
        chosen = ordered[: min(2, len(ordered))]
        basis: list[LegalBasis] = []
        for hit in chosen:
            chunk = hit.chunk
            basis.append(
                LegalBasis(
                    title=f"{chunk.title} {chunk.article_no}",
                    article_no=chunk.article_no,
                    source=chunk.source,
                    status=chunk.status,
                    jurisdiction=chunk.jurisdiction,
                    effective_date=chunk.effective_date,
                    expiry_date=chunk.expiry_date,
                    source_url=chunk.source_url,
                    domain=chunk.domain,
                    source_type=chunk.source_type,
                    match_reason=hit.match_reason,
                    is_demo_sample=chunk.is_demo_sample,
                )
            )
        return basis

    def _llm_analysis(
        self,
        task_id: str,
        question: str,
        parsed_document: ParsedDocument,
        chunks: list[DocumentChunk],
        retrieval: RetrievalResult,
        review_dimension: str,
    ) -> RiskAnalysis:
        try:
            client = OpenAICompatibleClient(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.model_name,
                timeout_seconds=self.settings.llm_timeout_seconds,
            )
            user_prompt = build_analysis_user_prompt(
                question=question,
                contract_sections=[chunk.text for chunk in chunks],
                knowledge_hits=[f"{hit.chunk.title}：{hit.chunk.content}" for hit in retrieval.hits],
                review_dimension=review_dimension,
            )
            raw = client.chat_json(SYSTEM_PROMPT, user_prompt)
        except LLMClientError as exc:
            raise RiskAnalysisError(f"LLM API 不可用：{exc}。请检查配置或在 DEMO MODE 下运行。") from exc
        payload = self._parse_json(raw)
        payload["task_id"] = task_id
        payload["review_dimension"] = review_dimension
        payload["legal_domain"] = DIMENSION_DOMAIN.get(review_dimension, "contract")
        payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        payload.setdefault("evidence_sufficient", False)
        return RiskAnalysis.model_validate(payload)

    @staticmethod
    def _parse_json(raw: object) -> dict:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            raise RiskAnalysisError("LLM 返回了无法解析的内容。")
        cleaned = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RiskAnalysisError(f"LLM 返回内容不是合法 JSON：{exc}") from exc
