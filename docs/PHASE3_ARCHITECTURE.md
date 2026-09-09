# Phase 3 — Evidence-first Legal Review Architecture

## Scope

Phase 3 在既有确定性工作流上增加 Legal KB、Hybrid RAG、Enterprise Playbook、Citation Guard、Redline 与评测。四阶段审查视觉和核心后端边界保持不变。

```text
Contract → Parser → Clause Chunks → Review Planner
                                    ↓
          Contract Evidence + Legal RAG + Enterprise Playbook
                                    ↓
                       Evidence-first Risk Reasoning
                                    ↓
                    Redline → Citation Guard → Router
                                    ↓
                    Human Review（按需）→ Report
```

## Key decisions

- Legal RAG 不能只靠向量：精确法言法语和条款编号需要 BM25，改写后的自然语言需要 dense；RRF 避免直接比较不同分数尺度。
- Metadata 先过滤辖区、领域与有效状态，防止无关或失效材料进入证据链。
- Playbook 独立于法律依据：它表达企业风险偏好，并通过版本字段支持未来客户规则。
- Citation Guard 只承认当前 KB / retrieval hits 中可追溯的引用。不存在的引用标记 unverified，不作为充分证据。
- High severity、low confidence、evidence insufficient、citation unverified、high Playbook deviation 和 jurisdiction uncertainty 复用现有 Human Review。
- 所有内置法律与 Playbook 数据均为 DEMO/SAMPLE，不代表实时、权威或官方法律数据库。

## Offline evaluation

`data/eval/legal_retrieval_eval.json` 包含 24 条 DEMO 查询。运行 `python scripts/evaluate_legal_rag.py` 输出 Hit@1 / Hit@3 / Hit@5 / Recall@5 / MRR。固定 demo-v1 数据当前结果为 0.875 / 1.0 / 1.0 / 1.0 / 0.9375。
