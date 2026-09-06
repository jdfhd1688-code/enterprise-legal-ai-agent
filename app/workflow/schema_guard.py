"""JSON schema guard and one-shot repair for LLM output."""

from __future__ import annotations

import json
import re

from app.schemas.risk import RiskAnalysis


class SchemaGuard:
    """Validates that output matches RiskAnalysis, with one repair attempt."""

    def validate(self, value: RiskAnalysis | dict | str, task_id: str) -> RiskAnalysis:
        if isinstance(value, RiskAnalysis):
            return value
        payload = self._as_dict(value)
        if isinstance(payload, dict):
            payload.setdefault("task_id", task_id)
        try:
            return RiskAnalysis.model_validate(payload)
        except Exception as original_error:  # noqa: BLE001 - one repair path
            repaired = self._repair(payload, task_id, str(original_error))
            if repaired is None:
                raise ValueError(f"Risk JSON 不符合 schema：{original_error}") from original_error
            return repaired

    def repair_if_needed(self, payload: dict, task_id: str, error: str) -> RiskAnalysis | None:
        return self._repair(payload, task_id, error)

    def _repair(self, payload: dict, task_id: str, error: str) -> RiskAnalysis | None:
        payload = dict(payload)
        payload["task_id"] = task_id
        # Fill empty-but-required scalar defaults rather than inventing citations.
        if not payload.get("summary"):
            payload["summary"] = "AI 初筛未生成有效摘要，结果需要人工复核。"
        if "risk_level" not in payload:
            payload["risk_level"] = "high"
        if "legal_domain" not in payload:
            payload["legal_domain"] = "contract"
        if "confidence" not in payload:
            payload["confidence"] = 0.4
        payload["requires_human_review"] = True
        payload["review_reason"] = "schema 自动修复后仍建议人工复核"
        try:
            return RiskAnalysis.model_validate(payload)
        except Exception:  # noqa: BLE001 - repair has one attempt by design
            return None

    @staticmethod
    def _as_dict(value: object) -> dict:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            raise ValueError("Risk JSON 必须是对象或 JSON 字符串。")
        cleaned = value.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
        if fenced:
            cleaned = fenced.group(1).strip()
        return json.loads(cleaned)

