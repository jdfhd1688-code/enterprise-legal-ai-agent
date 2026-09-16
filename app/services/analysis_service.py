"""End-to-end analysis and human-review service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from uuid import uuid4

from app.agent.graph import AgentGraph
from app.agent.review_planner import REVIEW_DIMENSIONS
from app.config import Settings, get_settings
from app.schemas.risk import ReviewDecision, ReviewOutcome, RiskLevel, Severity, TaskStatus
from app.schemas.deliverable import ReviewItemAction, ReviewItemDecision
from app.schemas.task import AuditEvent, TaskRecord
from app.deliverables import DocumentRedlineEngine, ReportDocxGenerator
from app.persistence import DeliverableRepository
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
        self.report_docx_generator = ReportDocxGenerator()
        self.redline_engine = DocumentRedlineEngine()
        self.deliverable_repository = DeliverableRepository(self.settings)

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
            source_extension=Path(filename).suffix.lower(),
            upload_sha256=hashlib.sha256(data).hexdigest(),
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
        if executed.status == TaskStatus.report_ready:
            self._auto_approve_low_risk_redlines(executed)
            self._generate_deliverables(executed, data)
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
        action_default = {
            ReviewDecision.approve: ReviewItemAction.accept,
            ReviewDecision.request_changes: ReviewItemAction.edit,
            ReviewDecision.reject: ReviewItemAction.reject,
        }[decision]
        for finding in task.risk.findings:
            change = modifications.setdefault(finding.clause_id, {})
            if not change.get("redline_action"):
                change["redline_action"] = (
                    action_default.value if finding.redline else ReviewItemAction.resolved.value
                )
            if change["redline_action"] == ReviewItemAction.edit.value and not change.get("human_final_clause"):
                change["human_final_clause"] = (
                    finding.redline.suggested_clause if finding.redline else finding.recommendation
                )
        if task.original_ai_result is None:
            task.original_ai_result = task.risk.model_copy(deep=True)
        applied = self._apply_modifications(task, modifications)
        review_items = self._build_review_items(task, applied, modifications, reviewer)
        task.review_items = review_items
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
        task.status = TaskStatus.awaiting_review
        task.route = "review_finalization"
        task.route_reason = f"人工复核决定：{decision.value}"
        task.audit_events.append(
            AuditEvent(
                event_type="human_review_completed",
                actor="reviewer",
                detail=f"decision={decision.value}; comment={comment.strip() or '无'}",
            )
        )
        for item in review_items:
            previous = next((f.redline.suggested_clause for f in task.original_ai_result.findings if f.clause_id == item.risk_id and f.redline), "")
            current = item.final_clause or item.action.value
            task.audit_events.append(AuditEvent(
                event_type="human_review_action", actor=reviewer,
                detail=(f"risk_id={item.risk_id}; action={item.action.value}; "
                        f"previous_value_hash={self._hash_value(previous)}; new_value_hash={self._hash_value(current)}; source=human_review"),
            ))
        return self.finalize_review(task.task_id, task=task)

    def finalize_review(self, task_id: str, task: TaskRecord | None = None) -> TaskRecord:
        task = task or self.get_task(task_id)
        if task.risk is None:
            raise InvalidFileError("任务没有可最终确认的风险结果。")
        decisions = {item.risk_id: item.action for item in task.review_items}
        unresolved = [
            finding.clause_id for finding in task.risk.findings
            if finding.severity == Severity.high
            and decisions.get(finding.clause_id) not in {
                ReviewItemAction.accept, ReviewItemAction.edit,
                ReviewItemAction.reject, ReviewItemAction.resolved,
            }
        ]
        if unresolved:
            raise InvalidFileError("仍有高风险事项未完成复核：" + "、".join(unresolved))
        task.final_status = "completed"
        task.report_markdown = self.report_generator.generate(
            task_id=task.task_id,
            filename=task.original_filename,
            question=task.question,
            risk=task.risk,
            review=task.review,
            evidence_notes=[
                f"{hit.chunk.title}｜{hit.chunk.article_no}｜{hit.chunk.source}"
                for hit in task.retrieval.hits
            ],
        )
        source_path = self.settings.upload_dir / f"{task.task_id}{task.source_extension}"
        source_bytes = source_path.read_bytes() if source_path.exists() else None
        self._generate_deliverables(task, source_bytes)
        task.review_finalized = True
        task.status = TaskStatus.reviewed
        task.route = "completed"
        task.route_reason = "人工复核已最终确认，交付文件已生成。"
        task.audit_events.append(
            AuditEvent(event_type="report_generated", actor="system", detail="最终报告已生成。")
        )
        task.audit_events.append(AuditEvent(event_type="review_finalized", actor="reviewer", detail="Finalization Guard 通过，任务已完成。"))
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
            if finding.redline:
                action = change.get("redline_action", "pending")
                finding.redline.human_action = action
                finding.redline.approved_by_human = action in {"accept", "edit"}
                if action == "edit":
                    finding.redline.human_final_clause = change.get("human_final_clause", "").strip()
                elif action == "accept":
                    finding.redline.human_final_clause = finding.redline.suggested_clause
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

    def _build_review_items(self, task: TaskRecord, risk, modifications, reviewer: str) -> list[ReviewItemDecision]:
        items: list[ReviewItemDecision] = []
        for finding in risk.findings:
            change = modifications.get(finding.clause_id, {})
            action = ReviewItemAction(change.get("redline_action", "pending"))
            final_clause = change.get("human_final_clause")
            if action == ReviewItemAction.accept and finding.redline:
                final_clause = finding.redline.suggested_clause
            items.append(ReviewItemDecision(
                risk_id=finding.clause_id, action=action, final_clause=final_clause,
                comment=change.get("comment", ""), reviewer=reviewer,
            ))
        return items

    def _auto_approve_low_risk_redlines(self, task: TaskRecord) -> None:
        if task.risk is None or task.risk.requires_human_review:
            return
        for finding in task.risk.findings:
            if finding.redline:
                finding.redline.human_action = ReviewItemAction.auto_approved.value
                finding.redline.approved_by_human = True
                finding.redline.human_final_clause = finding.redline.suggested_clause

    def _generate_deliverables(self, task: TaskRecord, source_bytes: bytes | None) -> None:
        metadata = [item for item in task.deliverables if item.status == "ready"]
        report_bytes = self.report_docx_generator.generate(task)
        metadata = [item for item in metadata if item.type != "final_report"]
        metadata.append(self.deliverable_repository.write(task.task_id, "final_report", "final_review_report.docx", report_bytes))
        if task.source_extension == ".docx" and source_bytes and task.risk:
            clean, marked, results = self.redline_engine.generate(source_bytes, task.risk.findings)
            task.redline_apply_results = results
            metadata = [item for item in metadata if item.type not in {"reviewed_contract", "redline_contract"}]
            metadata.append(self.deliverable_repository.write(task.task_id, "reviewed_contract", "reviewed_contract.docx", clean))
            metadata.append(self.deliverable_repository.write(task.task_id, "redline_contract", "redline_contract.docx", marked))
        task.deliverables = metadata
        for item in metadata:
            task.audit_events.append(AuditEvent(event_type="deliverable_generated", actor="system", detail=f"type={item.type}; filename={item.filename}; sha256={item.sha256}"))

    def get_deliverable(self, task_id: str, kind: str) -> tuple[str, bytes]:
        task = self.get_task(task_id)
        item = next((item for item in task.deliverables if item.type == kind and item.status == "ready"), None)
        if item is None:
            raise InvalidFileError("交付文件尚未生成。")
        return item.filename, self.deliverable_repository.read(item)

    @staticmethod
    def _hash_value(value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()

    def health(self) -> dict:
        return {
            "status": "ok",
            "demo_mode": self.settings.demo_mode,
            "analysis_mode": self.settings.demo_mode_label,
            "knowledge_base_records": len(self.graph.retrieval_skill.kb_tool.chunks),
            "task_store": str(self.settings.task_dir),
        }
