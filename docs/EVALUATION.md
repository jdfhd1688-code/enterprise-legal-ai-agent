# Evaluation Foundation

## Architecture

Phase B1 adds shared, offline contracts for versioned datasets, evaluator registration, run metadata, results, and JSON/Markdown reports. Evaluator failures are recorded as errors; missing evaluators and malformed or empty datasets fail loudly.

The generated run directory is `artifacts/evaluation/runs/` and is ignored by Git.

## Dataset contract

Every JSON dataset contains:

- `metadata`: name, version, type, approved source type, creation time, and description.
- `cases`: one or more cases matching the declared dataset type.

Supported types are `retrieval`, `risk`, `abstention`, `citation`, and `schema`. Approved source types are `demo`, `synthetic`, `public_safe`, and `public`. Private cases and real-client data are not accepted source types.

B1 fixtures under `data/eval/fixtures/` are synthetic contract tests. They are not performance datasets or project results.

## Run

```bash
python scripts/run_evaluation.py
```

Optional paths:

```bash
python scripts/run_evaluation.py --evaluator retrieval_v2
python scripts/run_evaluation.py --evaluator retrieval_v2 --dataset data/eval/retrieval_v2.json --output-dir artifacts/evaluation/runs
```

The CLI retains `foundation_validation` and now also registers `retrieval_v2`. Foundation validation remains a wiring check, not a quality score.

Retrieval v2 evaluates Legal Retrieval over the DEMO/SAMPLE Legal KB and Contract Retrieval over chunks parsed from one synthetic DOCX. Positive-case Hit@K, corrected macro Recall@5, and MRR are reported separately from negative retrieval accuracy. Metrics are also split by query type and domain, and failures retain expected and retrieved IDs.

The legacy evaluator identifies gold evidence by title/article pair and labels Hit@5 directly as Recall@5. Retrieval v2 computes each positive query's retrieved-relevant count divided by all expected relevant IDs, then macro-averages it. Therefore legacy and v2 Recall@5 are not a historical trend and must not be compared as the same metric.

The existing formal retrieval evaluation remains:

```bash
python scripts/evaluate_legal_rag.py
```

## Current scope and limitations

- The only formal performance result remains the legacy 24-query Legal Retrieval evaluation.
- Retrieval v2 is a separate baseline over `data/eval/retrieval_v2.json`; it includes migrated legacy seeds, synthetic multi-relevant cases, explicit negatives, and synthetic contract cases.
- B1 established shared contracts without adding performance evaluator logic or thresholds.
- B2 implements only E1 Retrieval v2. Citation, routing, structured-output, abstention, direct-LLM, and Golden Case evaluation remain unavailable.
- No network or model provider is required.
- Run metadata records only an explicit, secret-redacted configuration snapshot; it does not capture environment variables.
- High retrieval scores mean expected evidence was retrieved within this limited DEMO/SYNTHETIC dataset and KB. They do not measure legal conclusion accuracy, whole-system accuracy, production-law coverage, commercial readiness, or hallucination rate.
- Contract Retrieval is a minimal lexical BM25-style ranker over one parsed contract. It is not cross-contract search or a production search engine.
