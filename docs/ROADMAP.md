# Roadmap — 未来演进路线

## V1：当前作品集 MVP

目标：展示可运行的 AI Solution 原型和 SDD/Vibe Coding 流程。

- Streamlit UI
- Demo Mode
- 规则引擎 + mock/fallback LLM 路径
- Demo 法规知识库
- 合同上传与解析
- Chunk 切分
- Review Dimension Planner
- Legal RAG metadata filter
- Risk JSON / Pydantic
- Workflow 风险路由
- Human Review
- Audit Log
- MCP mock adapter
- 本地 JSON 任务记录
- 自动化测试

## V2：可试点企业原型

目标：从作品集 Demo 升级为可在小范围试点的内部工具。

- FastAPI 后端服务化
- React / Next.js 前端
- SQLite / PostgreSQL
- pgvector / Milvus
- 真实 LLM 接入和调用监控
- 企业文档上传与对象存储
- 审计日志持久化
- 基础用户权限
- 更完善的 RAG 评估集
- Prompt 版本管理
- 人工复核结果结构化保存

## V3：生产级法律 AI 平台

目标：满足企业级安全、合规、集成、审计和可观测要求。

- SSO / RBAC / ABAC
- 多租户隔离
- 合同管理系统集成
- OA / 审批系统集成
- 法规知识库治理流程
- 真实 MCP Server
- 增量知识库更新
- 法规版本控制
- 集中式日志与监控
- 模型评估与回归测试
- Prompt / Chain / Agent 版本管理
- 人工复核闭环数据回流
- 审计回放与合规报告

## 不建议在 V1 过早实现的内容

- 真实外部法律网站实时抓取
- 复杂多租户
- 支付系统
- 大规模 OCR
- 完整企业权限体系
- 复杂微服务化

这些能力更适合进入 V2/V3 阶段后再做。
