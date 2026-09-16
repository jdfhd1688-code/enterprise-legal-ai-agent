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
python scripts/run_evaluation.py --dataset data/eval/fixtures/risk_foundation.json --output-dir artifacts/evaluation/runs
```

The B1 CLI registers only `foundation_validation`. Its `validated_cases` count proves that loading, runner execution, and report serialization worked; it is not a quality score.

The existing formal retrieval evaluation remains:

```bash
python scripts/evaluate_legal_rag.py
```

## Current scope and limitations

- The only formal performance result remains the legacy 24-query Legal Retrieval evaluation.
- B1 does not implement E1-E5 evaluator logic, thresholds, CI gating, Golden Cases, or a direct LLM baseline.
- No network or model provider is required.
- Run metadata records only an explicit, secret-redacted configuration snapshot; it does not capture environment variables.
