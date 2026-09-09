"""End-to-end analysis and human-review service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agent.graph import AgentGraph
from app.agent.review_planner import REVIEW_DIMENSIONS
from app.config import Settings, get_settings
from app.schemas.risk import ReviewDecision, ReviewOutcome, RiskLevel, Severity, TaskStatus
from app.schemas.task import AuditEvent, TaskRecord
from app.skills.report_generator import ReportGenerator
from app.services.task_store import TaskNotFoundError, TaskStore


class InvalidFileError(ValueError):
    pass


class AnalysisService:
    """Clean service boundary shared by Streamlit and FastAPI."""

    allowed_extensions = {".pdf", ".txt", ".docx"}

    def __init__(
        self,
        settings: Settings | None = None,
        task_store: TaskStore | None = None,
        graph: AgentGraph | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self.store = task_store or TaskStore(self.settings)
        self.graph = graph or AgentGraph(self.settings)
        self.report_generator = ReportGenerator()

    def validate_file(self, filename: str, data: bytes) -> None:
        extension = Path(filename).suffix.lower()
        if extension not in self.allowed_extensions:
            raise InvalidFileError(
                f"不支持的文件类型：{extension or '无扩展名'}。MVP 以 PDF 为首要格式，同时支持 TXT/DOCX。"
            )
        if not data:
            raise InvalidFileError("上传文件为空。")
        if len(data) > self.settings.max_upload_bytes:
            raise InvalidFileError(
                f"文件超过 {self.settings.max_upload_mb} MB 限制，请压缩后重试。"
            )

    def create_task(
        self,
        filename: str,
        data: bytes,
        question: str,
        review_dimension: str | None = None,
        on_stage: Callable[[str, str], None] | None = None,
    ) -> TaskRecord:
        task = self.prepare_task(filename, data, question, review_dimension)
        if on_stage is not None:
            on_stage("received", "合同文件已接收。")
        return self.execute_task(task.task_id, data, on_stage=on_stage)

    def prepare_task(
        self,
        filename: str,
        data: bytes,
        question: str,
        review_dimension: str | None = None,
    ) -> TaskRecord:
        """Validate and persist a submitted task before the workflow starts."""
        self.validate_file(filename, data)
        if review_dimension is not None and review_dimension not in REVIEW_DIMENSIONS:
            raise InvalidFileError(f"未知审查维度：{review_dimension}")
        task_id = f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"
        dimension = review_dimension or "general_contract"
        task = TaskRecord(
            task_id=task_id,
            original_filename=Path(filename).name,
            question=(question or "这份合同有哪些高风险条款？").strip(),
            review_dimension=dimension,
            status=TaskStatus.submitted,
        )
        task.audit_events.append(
            AuditEvent(event_type="task_created", actor="system", detail="任务已创建，等待 Agent 执行。")
        )
        self.store.save(task)
        upload_path = self.settings.upload_dir / f"{task_id}{Path(filename).suffix.lower()}"
        upload_path.write_bytes(data)
        return task

    def execute_task(
        self,
        task_id: str,
        data: bytes,
        on_stage: Callable[[str, str], None] | None = None,
    ) -> TaskRecord:
        """Execute a task that has already passed file intake."""
        task = self.get_task(task_id)
        executed = self.graph.execute(task, data, on_stage=on_stage)
        return self.store.save(executed)

    def get_task(self, task_id: str) -> TaskRecord:
        return self.store.load(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return self.store.list_tasks()

    def list_review_tasks(self) -> list[TaskRecord]:
        return [task for task in self.list_tasks() if task.status == TaskStatus.awaiting_review]

    def submit_review(
        self,
        task_id: str,
        decision: ReviewDecision,
        comment: str = "",
        modifications: dict[str, dict[str, str]] | None = None,
        reviewer: str = "demo-reviewer",
    ) -> TaskRecord:
        task = self.get_task(task_id)
        if task.status != TaskStatus.awaiting_review:
            raise InvalidFileError("该任务当前不在人工复核队列中。")
        if task.risk is None:
            raise InvalidFileError("该任务没有可复核的风险结果。")

        modifications = modifications or {}
        if task.original_ai_result is None:
            task.original_ai_result = task.risk.model_copy(deep=True)
        applied = self._apply_modifications(task, modifications)
        task.reviewed_result = applied
        final_level = applied.risk_level
        outcome = ReviewOutcome(
            decision=decision,
            comment=comment.strip(),
            modifications=modifications,
            reviewer=reviewer,
            reviewed_at=datetime.now(timezone.utc),
            final_summary=applied.summary,
            final_risk_level=final_level,
        )
        task.risk = applied
        task.review = outcome
        task.status = TaskStatus.reviewed
        task.route = "reviewed"
        task.route_reason = f"人工复核决定：{decision.value}"
        task.audit_events.append(
            AuditEvent(
                event_type="human_review_completed",
                actor="reviewer",
                detail=f"decision={decision.value}; comment={comment.strip() or '无'}",
            )
        )
        task.report_markdown = self.report_generator.generate(
            task_id=task.task_id,
            filename=task.original_filename,
            question=task.question,
            risk=applied,
            review=outcome,
            evidence_notes=[
                f"{hit.chunk.title}｜{hit.chunk.article_no}｜{hit.chunk.source}"
                for hit in task.retrieval.hits
            ],
        )
        task.audit_events.append(
            AuditEvent(event_type="report_generated", actor="system", detail="最终报告已生成。")
        )
        task.touch()
        return self.store.save(task)

    def _apply_modifications(self, task: TaskRecord, modifications: dict[str, dict[str, str]]):
        risk = task.risk.model_copy(deep=True)
        for finding in risk.findings:
            change = modifications.get(finding.clause_id) or {}
            if change.get("issue"):
                finding.issue = change["issue"]
            if change.get("recommendation"):
                finding.recommendation = change["recommendation"]
            severity = change.get("severity")
            if severity in {Severity.low.value, Severity.medium.value, Severity.high.value}:
                finding.severity = Severity(severity)
        severities = {finding.severity for finding in risk.findings}
        if Severity.high in severities:
            risk.risk_level = RiskLevel.high
        elif Severity.medium in severities:
            risk.risk_level = RiskLevel.medium
        else:
            risk.risk_level = RiskLevel.low
        return risk

    def health(self) -> dict:
        return {
            "status": "ok",
            "demo_mode": self.settings.demo_mode,
            "analysis_mode": self.settings.demo_mode_label,
            "knowledge_base_records": len(self.graph.retrieval_skill.kb_tool.chunks),
            "task_store": str(self.settings.task_dir),
        }
