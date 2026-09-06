"""FastAPI service boundary.

Run with:
    uvicorn app.api:app --reload
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402

from app.schemas.risk import ReviewSubmission  # noqa: E402
from app.schemas.task import TaskRecord  # noqa: E402
from app.services.analysis_service import AnalysisService, InvalidFileError  # noqa: E402
from app.services.task_store import TaskNotFoundError  # noqa: E402

app = FastAPI(title="Enterprise Legal AI Agent API", version="0.1.0")
service = AnalysisService()


def task_payload(task: TaskRecord) -> dict:
    return task.model_dump(mode="json")


@app.get("/api/health")
def health() -> dict:
    return service.health()


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    question: str = Form("这份合同有哪些高风险条款？"),
    review_dimension: str = Form("general_contract"),
) -> dict:
    try:
        data = await file.read()
        task = service.create_task(
            file.filename or "upload.pdf",
            data,
            question,
            review_dimension=review_dimension,
        )
    except InvalidFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return task_payload(task)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    try:
        return task_payload(service.get_task(task_id))
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/review/{task_id}")
def review_task(task_id: str, submission: ReviewSubmission) -> dict:
    try:
        task = service.submit_review(
            task_id=task_id,
            decision=submission.decision,
            comment=submission.comment,
            modifications=submission.modifications,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return task_payload(task)
