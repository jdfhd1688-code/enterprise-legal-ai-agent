# Project Retrospective — 项目复盘

## 最初需求

最初目标是做一个适合 AI Solution 岗位展示的项目，不是单纯练前端，也不是纯聊天机器人。项目需要结合用户的法律/合规背景，展示需求澄清、AI 架构设计、Vibe Coding、测试验收和面试讲解能力。

## 为什么选择法律合同审查场景

法律合同审查同时具备高频、重复、专业、风险敏感和证据链要求，适合展示 AI 应用系统的完整设计：文档解析、知识检索、结构化分析、风险分流和人工复核。

## 为什么不用普通聊天机器人

普通聊天机器人容易出现三个问题：输出结构不稳定、依据来源不透明、责任边界不清。企业法务场景需要系统化流程，而不是只让模型自由回答。

## 为什么采用 Agent + RAG + Workflow + HITL

- **Agent**：编排多步骤任务。
- **RAG**：提供可追溯证据和知识依据。
- **Workflow**：用确定性规则控制风险路由。
- **HITL**：高风险或证据不足时由人类复核，保留责任边界。

## 第一版 MVP 的问题

第一版已经能跑通主链路，但存在明显短板：UI 像工程 Demo，Agent 决策感弱，RAG 偏普通相似度检索，人工复核留痕不充分，MCP 说明不够清晰。

## UI 为什么需要产品化

作品集项目首先需要让人看懂和愿意继续看。将界面改成工作台、任务队列、结果卡片、报告中心和技术细节折叠区，可以让项目更像真实企业应用。

## 技术上为什么增强 Review Planner / metadata filter / audit log

- **Review Planner**：让系统理解用户审查意图，区分交付、付款、违约、保密、知识产权等维度。
- **Metadata filter**：法律 RAG 不能只看相似度，还要看法规状态、领域、辖区和有效期。
- **Audit log**：法律场景必须区分 AI 建议、人工修改和最终决策。

## 当前真实实现了什么

当前项目真实实现了 Streamlit UI、合同解析、Chunk 切分、RAG 检索、Review Dimension Planner、Risk JSON / Pydantic 校验、Workflow 路由、Human Review、Audit Log、报告生成、Demo Mode 和自动化测试。

## 哪些仍然是 demo / mock

示例法规知识库是 DEMO/SAMPLE；MCP adapter 是 mock；真实 LLM 需要用户配置 API Key；没有真实法规网站接入、登录、权限、多租户、企业数据库和生产级部署。

## 如果进入企业生产环境，下一步如何演进

需要接入经过审核的法规知识库，增加法规版本治理、PostgreSQL/pgvector、对象存储、队列、SSO/RBAC、审计日志持久化、模型评估、Prompt 版本管理、企业 MCP Server 和监控系统。

## 体现的 AI Solution 能力

- 业务问题拆解
- AI 架构设计
- Agent/RAG/Workflow/HITL 组合设计
- 合规边界意识
- 产品原型落地
- 测试验收
- 真实与 mock 边界管理

## 体现的 Vibe Coding / SDD 能力

- 先写规范再开发
- 用 Codex 辅助生成而不是无约束生成
- 通过测试和人工验收迭代
- 能把 Demo 包装成可投递作品
- 能诚实说明项目边界与未来路线
