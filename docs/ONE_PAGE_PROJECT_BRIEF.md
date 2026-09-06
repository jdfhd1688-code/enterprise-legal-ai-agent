# Enterprise Legal AI Agent — 一页纸项目说明

## 项目名称

**Enterprise Legal AI Agent**  
企业法务 AI 合同审查工作台 MVP

## 一句话介绍

Enterprise Legal AI Agent 是一个面向企业法务与合规团队的 AI 合同审查工作台 MVP，演示如何通过 **Agent + RAG + Workflow + Human-in-the-loop + Audit Log** 完成合同解析、法规依据检索、风险分级、人工复核与报告生成。

## 为什么做这个项目

企业合同审查存在高重复、高风险、证据链不透明的问题。传统人工审查依赖律师逐条阅读合同、检索法规、判断风险并撰写意见，效率低且难以标准化；而纯聊天机器人虽然能生成文本，但容易出现依据不明、法律来源不可靠、责任边界不清的问题。

本项目选择“企业合同审查”作为场景，是因为它天然适合展示 AI Solution 能力：需要业务理解、法律合规边界、知识检索、结构化输出、流程分流和人工审核闭环。

## 目标用户

- 企业法务团队
- 合规团队
- 法律运营人员
- 需要做合同初筛的业务部门

## 核心痛点

- 合同审查重复性高，低价值阅读占用大量时间
- 法规依据容易遗漏或引用不透明
- 风险等级缺少结构化标准
- AI 结果不能直接替代专业法律判断
- 高风险审查需要人工复核和审计追踪

## 解决方案

系统支持用户上传合同并输入审查问题。系统会解析合同、切分条款、识别审查维度、检索合同证据与示例法规知识库，然后生成结构化 Risk JSON。Workflow 根据风险等级、置信度、证据充分性和法律依据状态决定：低风险且证据充分时自动生成报告；高风险、低置信度或证据不足时进入人工复核队列，并记录 audit log。

## 核心流程

```text
上传合同 + 输入问题
→ Review Dimension Planner 识别审查维度
→ Document Parser 解析合同
→ Chunker 切分条款并保留 metadata
→ Legal RAG 检索合同证据和示例法规依据
→ Risk Analysis 生成结构化 Risk JSON
→ Pydantic Schema 校验
→ Workflow Router 风险分流
→ Human Review 或 Report Generation
→ Audit Log 留痕
```

## 技术架构

- **Streamlit UI**：合同审查工作台、结果页、人工复核队列、报告中心
- **Service Layer**：封装任务创建、分析执行、复核和报告流程
- **Agent Orchestration**：受控状态图编排解析、检索、分析、校验、路由
- **Skills / Tools**：文档解析、Chunk、检索、风险分析、报告生成
- **Legal RAG**：基于示例知识库与 metadata filter 的检索链路
- **Pydantic Schema**：约束 Risk JSON 输出结构
- **Workflow Router**：根据风险和证据做确定性分流
- **Human-in-the-loop**：高风险/证据不足任务进入人工复核
- **MCP Mock Adapter**：模拟未来连接法规库、OA、合同管理系统等企业资源

## 我的项目角色

- 需求澄清：定义目标用户、业务痛点和产品边界
- PRD 设计：梳理页面、流程、数据结构和验收标准
- 架构设计：拆分 Agent、RAG、Workflow、HITL、MCP 的职责
- Codex Prompt 编写：以 SDD 方式驱动 AI Coding 工具实现 MVP
- 测试验收：检查 Demo 路径、自动化测试、Real / Mock 边界
- UI 产品化迭代：将工程 Demo 打磨为企业级工作台原型
- 技术增强迭代：补充 Review Planner、metadata filter、audit log、MCP mock

## Real / Mock / Not Implemented 边界

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| Streamlit UI | REAL IMPLEMENTATION | 可运行工作台界面 |
| PDF parsing / Chunking | REAL IMPLEMENTATION | 支持 PDF/TXT/DOCX 解析与条款切分 |
| RAG retrieval | REAL IMPLEMENTATION | 检索链路真实运行，但数据为 DEMO/SAMPLE |
| Risk JSON / Pydantic | REAL IMPLEMENTATION | 结构化校验真实运行 |
| Workflow routing | REAL IMPLEMENTATION | 根据风险、置信度、证据做分流 |
| Human Review / Audit Log | REAL IMPLEMENTATION | 支持复核、意见、留痕 |
| Real LLM call | REAL IMPLEMENTATION | 有 OpenAI-compatible 路径；需用户配置 Key |
| MCP adapter | MOCK IMPLEMENTATION | 演示未来企业系统集成接口 |
| External legal website integration | NOT IMPLEMENTED | 未接真实法规网站 |
| User auth / RBAC / 多租户 | NOT IMPLEMENTED | 当前版本不做企业权限体系 |

## 项目亮点

1. 不是普通聊天机器人，而是带流程控制的法律 AI 工作台。
2. 将法律场景拆成 Agent 编排、RAG 检索、Workflow 分流和人工复核。
3. 通过 metadata filter 体现法律知识库治理意识。
4. 通过 Risk JSON 和 Pydantic 降低大模型输出不可控风险。
5. 通过 audit log 明确 AI 建议与人工最终判断的责任边界。
6. 保留 Real / Mock 边界，避免夸大 Demo 能力。

## 未来演进方向

- Streamlit → React/Next.js + FastAPI
- 本地 JSON → PostgreSQL / pgvector
- Demo 知识库 → 经审核的企业法规知识库
- Mock MCP → 真实 MCP Server / 企业工具服务
- 单用户 Demo → SSO、RBAC、ABAC、多租户
- 简单测试 → RAG 评估、模型评估、Prompt 版本管理
- 本地部署 → 企业云部署、日志监控、审计回放
