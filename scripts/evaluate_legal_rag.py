"""Run the offline DEMO/SAMPLE Legal RAG evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.retrieval_eval import RetrievalEvaluator


if __name__ == "__main__":
    print(json.dumps(RetrievalEvaluator().evaluate(), ensure_ascii=False, indent=2))
