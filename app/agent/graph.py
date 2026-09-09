"""Agent state graph (explicit equivalent of the LangGraph START->...->END flow).

The README explains how this maps to LangGraph. The demo intentionally keeps
the graph deterministic and testable: Agent understands intent and orchestrates
skills/tools, while WorkflowRouter owns fixed business rules.
"""

from __future__ import annotations

from collections.abc import Callable

from app.config import Settings, get_settings
from app.guards.citation_guard import CitationGuard
from app.playbook.engine import PlaybookEngine
from app.schemas.kb import RetrievalResult
from app.schemas.task import AuditEvent, StageEvent, TaskRecord
from app.schemas.risk import RiskAnalysis, TaskStatus
from app.agent.review_planner import ReviewDimensionPlanner
from app.skills.chunker import ChunkerSkill
from app.skills.document_parser import DocumentParserError, DocumentParserSkill
from app.skills.report_generator import ReportGenerator
from app.skills.retrieval import RetrievalSkill
from app.skills.risk_analysis import RiskAnalysisError, RiskAnalysisSkill
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from app.workflow.router import WorkflowRoute, WorkflowRouter
from app.workflow.schema_guard import SchemaGuard


class AgentGraph:
    """Runs the deterministic MVP graph for one uploaded contract."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        kb_tool = KnowledgeBaseTool(self.settings)
        self.parser = DocumentParserSkill()
        self.planner = ReviewDimensionPlanner()
        self.chunker = ChunkerSkill()
        self.retrieval_skill = RetrievalSkill(kb_tool)
        self.risk_skill = RiskAnalysisSkill(self.settings)
        self.playbook = PlaybookEngine(self.settings)
        self.citation_guard = CitationGuard()
        self.schema_guard = SchemaGuard()
        self.router = WorkflowRouter(self.settings)
        self.report_generator = ReportGenerator()

    def execute(
        self,
        task: TaskRecord,
        content: bytes,
        on_stage: Callable[[str, str], None] | None = None,
    ) -> TaskRecord:
        preferred = task.review_dimension if task.review_dimension != "general_contract" else None
        self._event(task, "START", "Agent 已接收任务，开始解析合同。")
        try:
            task.status = TaskStatus.parsing
            self._notify(on_stage, "parsing", "正在解析合同结构与条款。")
            parsed = self.parser.parse(task.original_filename, content)
            task.parsed_document = parsed
            task.touch()
            self._event(
                task,
                "parse",
                f"解析完成：{parsed.num_pages} 页 / {parsed.text_length} 字符。",
            )

            task.status = TaskStatus.chunking
            chunks = self.chunker.chunk(parsed)
            task.chunks = chunks
            task.touch()
            self._event(task, "chunk", f"文本切分完成：共 {len(chunks)} 个带来源片段。")

            self._notify(on_stage, "planning", "正在识别本次合同的审查维度。")
            plan = self.planner.plan(task.question, preferred_dimension=preferred)
            task.review_dimension = plan.dimension

            task.status = TaskStatus.retrieving
            self._notify(on_stage, "retrieving", "正在检索与合同条款相关的法律依据。")
            retrieval = self.retrieval_skill.retrieve(
                parsed,
                chunks,
                task.question,
                review_dimension=plan.dimension,
            )
            task.retrieval = retrieval
            task.touch()
            if retrieval.is_empty:
                self._event(task, "retrieve", "未检索到知识库证据，后续将进入异常/人工路径。")
            else:
                self._event(task, "retrieve", f"检索到 {len(retrieval.hits)} 条 DEMO/SAMPLE 知识库证据。")

            playbook_result = self.playbook.evaluate(chunks, plan.dimension)
            task.playbook = playbook_result
            self._event(
                task,
                "playbook",
                f"执行 {playbook_result.rules_evaluated} 条 {playbook_result.version} 规则，识别 {len(playbook_result.deviations)} 项偏离。",
            )

            task.status = TaskStatus.analyzing
            self._notify(on_stage, "analyzing", "正在结合合同证据与法律依据分析风险。")
            risk = self.risk_skill.analyze(
                task_id=task.task_id,
                question=task.question,
                parsed_document=parsed,
                chunks=chunks,
                retrieval=retrieval,
                review_dimension=plan.dimension,
                playbook_result=playbook_result,
            )
            risk = self.citation_guard.validate(risk, retrieval)
            risk.review_dimension = plan.dimension
            task.risk = risk
            task.touch()
            self._event(task, "analyze", f"风险分析完成：{risk.risk_level.value.upper()} / 置信度 {risk.confidence:.2f}。")

            task.status = TaskStatus.validating
            self._notify(on_stage, "validating", "正在校验风险结果与证据状态。")
            validated = self.schema_guard.validate(risk, task.task_id)
            task.risk = validated
            task.original_ai_result = validated.model_copy(deep=True)
            task.touch()
            self._event(task, "validate", "Risk JSON 已通过 Pydantic schema 校验。")

            task.status = TaskStatus.routing
            route, routed_risk = self.router.route(validated, retrieval)
            task.risk = routed_risk
            task.route = route
            task.route_reason = routed_risk.review_reason
            task.touch()

            if route == WorkflowRoute.awaiting_review:
                task.status = TaskStatus.awaiting_review
                self._event(task, "human_review_started", "任务已进入人工复核队列。")
                self._event(task, "workflow_router", f"路由到人工复核：{routed_risk.review_reason or '规则要求复核'}。")
                self._notify(on_stage, "review_required", "AI 初审完成，任务需要人工复核。")
            elif route == WorkflowRoute.report:
                task.status = TaskStatus.report_ready
                self._notify(on_stage, "reporting", "正在生成结构化审查报告。")
                task.report_markdown = self._build_report(task)
                self._event(task, "report_generation", "已自动生成结构化风险报告。")
                self._notify(on_stage, "completed", "审查与报告生成完成。")
            else:
                task.status = TaskStatus.failed
                self._event(task, "workflow_router", "工作流未识别路由，任务失败。")
            task.touch()
            return task
        except (DocumentParserError, RiskAnalysisError, ValueError) as exc:
            task.status = TaskStatus.failed
            task.error = str(exc)
            task.touch()
            self._event(task, "failed", str(exc))
            self._notify(on_stage, "failed", "审查流程未完成。")
            return task
        except Exception as exc:  # noqa: BLE001 - no silent failure in the demo
            task.status = TaskStatus.failed
            task.error = f"分析流程发生未预期错误：{exc}"
            task.touch()
            self._event(task, "failed", task.error)
            self._notify(on_stage, "failed", "审查流程未完成。")
            return task

    @staticmethod
    def _notify(callback: Callable[[str, str], None] | None, stage: str, message: str) -> None:
        """Publish presentation state without letting UI failures affect analysis."""
        if callback is None:
            return
        try:
            callback(stage, message)
        except Exception:  # noqa: BLE001 - presentation hooks must never break the graph
            return

    def _build_report(self, task: TaskRecord) -> str:
        evidence_notes = [
            f"{hit.chunk.title}｜{hit.chunk.article_no}｜{hit.chunk.source}｜相似度 {hit.score:.3f}"
            for hit in task.retrieval.hits
        ]
        return self.report_generator.generate(
            task_id=task.task_id,
            filename=task.original_filename,
            question=task.question,
            risk=task.risk or RiskAnalysis(
                task_id=task.task_id,
                risk_level="low",
                legal_domain="contract",
                confidence=0,
                summary="报告未生成。",
            ),
            evidence_notes=evidence_notes,
        )

    @staticmethod
    def _event(task: TaskRecord, stage: str, message: str) -> None:
        task.events.append(StageEvent(stage=stage, message=message))
        task.audit_events.append(
            AuditEvent(
                event_type=AgentGraph._event_type(stage),
                actor="ai" if stage == "analyze" else "system",
                detail=message,
            )
        )

    @staticmethod
    def _event_type(stage: str) -> str:
        mapping = {
            "START": "task_started",
            "parse": "document_parsed",
            "chunk": "chunks_created",
            "retrieve": "retrieval_completed",
            "playbook": "playbook_evaluated",
            "analyze": "risk_analysis_completed",
            "validate": "schema_validated",
            "workflow_router": "workflow_routed",
            "human_review_started": "human_review_started",
            "report_generation": "report_generated",
            "failed": "task_failed",
        }
        return mapping.get(stage, f"stage_{stage}")
