"""Real LLM connectivity test for the Enterprise Legal AI Agent.

Run:
    python scripts/test_real_llm.py

Without OPENAI_API_KEY it only reports DEMO MODE and never prints keys.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent.prompts import SYSTEM_PROMPT, build_analysis_user_prompt
from app.config import get_settings
from app.schemas.risk import RiskAnalysis
from app.tools.llm_client import LLMClientError, OpenAICompatibleClient


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    return json.loads(cleaned)


def main() -> int:
    settings = get_settings()
    if settings.demo_mode:
        print("当前为 DEMO MODE，未执行真实 LLM 测试。请配置 OPENAI_API_KEY 和 ENABLE_REAL_LLM=true。")
        return 0
    print("检测到 OPENAI_API_KEY，开始真实 LLM 连通性测试...")
    try:
        client = OpenAICompatibleClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.model_name,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        prompt = build_analysis_user_prompt(
            question="测试问题：违约金条款是否合理？",
            contract_sections=[
                "第五条 甲方逾期付款应按每日千分之五支付违约金。",
            ],
            knowledge_hits=[
                "DEMO/SAMPLE 违约金与赔偿参考样例：违约金应当与实际损失大体相当。",
            ],
            review_dimension="breach_liability",
        )
        raw = client.chat_json(SYSTEM_PROMPT, prompt)
        payload = _extract_json(raw)
        payload.setdefault("task_id", "LLM-CONNECT-TEST")
        payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        risk = RiskAnalysis.model_validate(payload)
        print(f"真实 LLM 测试成功：模型 {settings.model_name}，返回 Risk JSON 通过 Pydantic 校验。")
        print(f"risk_level={risk.risk_level.value}, confidence={risk.confidence}")
        return 0
    except (LLMClientError, ValueError, json.JSONDecodeError) as exc:
        print(f"真实 LLM 测试失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
