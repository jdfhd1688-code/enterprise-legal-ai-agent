"""Data-driven DEMO enterprise playbook evaluation."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.document import DocumentChunk
from app.schemas.playbook import PlaybookDeviation, PlaybookResult, PlaybookRule
from app.schemas.risk import PlaybookEvidence, RedlineSuggestion


CHINESE_NUMBERS = {"一": 1, "三": 3, "五": 5, "十": 10, "十五": 15, "二十": 20, "三十": 30, "四十五": 45, "六十": 60, "九十": 90}


class PlaybookEngine:
    """Load versioned rules from JSON and evaluate contract chunks deterministically."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.rules = self._load_rules()

    def _load_rules(self) -> list[PlaybookRule]:
        directory = Path(self.settings.playbook_dir)
        rules: list[PlaybookRule] = []
        if not directory.exists():
            return rules
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            records = data.get("rules", []) if isinstance(data, dict) else data
            rules.extend(PlaybookRule.model_validate(item) for item in records)
        return rules

    def evaluate(self, chunks: list[DocumentChunk], review_dimension: str = "general_contract") -> PlaybookResult:
        relevant = [rule for rule in self.rules if review_dimension == "general_contract" or rule.dimension == review_dimension]
        deviations: list[PlaybookDeviation] = []
        for chunk in chunks:
            for rule in relevant:
                evaluation = self._evaluate_rule(rule, chunk.text)
                if evaluation is None:
                    continue
                actual, deviation = evaluation
                evidence = PlaybookEvidence(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    version=rule.version,
                    expected=rule.preferred,
                    actual=actual,
                    deviation=deviation,
                    severity=rule.severity,
                    source_type=rule.source_type,
                )
                redline = None
                if rule.suggested_clause:
                    redline = RedlineSuggestion(
                        original_clause=" ".join(chunk.text.split())[:600],
                        suggested_clause=rule.suggested_clause,
                        change_reason=f"偏离 {rule.rule_id}（{rule.version}）：{deviation}",
                        change_type="replace",
                        confidence=0.84,
                    )
                deviations.append(
                    PlaybookDeviation(
                        rule_id=rule.rule_id,
                        chunk_id=chunk.chunk_id,
                        evidence=evidence,
                        redline=redline,
                        recommendation=rule.recommendation,
                    )
                )
        version = self.rules[0].version if self.rules else "demo-v1"
        return PlaybookResult(version=version, rules_evaluated=len(relevant), deviations=deviations)

    def _evaluate_rule(self, rule: PlaybookRule, text: str) -> tuple[str, str] | None:
        if rule.trigger_terms and not any(term in text for term in rule.trigger_terms):
            return None
        if rule.evaluator == "prohibited_terms":
            matched = next((term for term in rule.risk_terms if term in text), None)
            return (matched, f"出现企业规则禁止或需升级审查的表述“{matched}”") if matched else None
        if rule.evaluator == "required_terms":
            if len("".join(text.split())) < 50:
                return None
            if rule.rule_id == "DELIVERY_ACCEPTANCE_001" and "采购清单" in text:
                return None
            if any(term in text for term in rule.required_terms):
                return None
            return ("未发现必要限定", f"缺少：{'、'.join(rule.required_terms)}")
        if rule.evaluator == "max_days":
            match = re.search(r"(?:发票|验收)[^。；]{0,35}?([一二三四五六七八九十百\d]+)个?(?:工作)?日", text)
            if not match:
                return None
            raw = match.group(1)
            days = int(raw) if raw.isdigit() else CHINESE_NUMBERS.get(raw)
            if days is None or rule.threshold is None or days <= rule.threshold:
                return None
            return (f"{days} 天", f"超过企业首选上限 {int(rule.threshold)} 天")
        return None
