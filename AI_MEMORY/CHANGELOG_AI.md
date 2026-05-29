# AI Changelog

本文件记录 AI Agent 对规则、记忆和 Harness 文档的变更。业务代码变更应在任务交付报告中另行说明。

## 2026-05-29

任务：收紧 OpenCode 定位措辞。

变更：

- 更新 `OPENCODE_USAGE.md`，将 OpenCode 从 “Harness Runner” 收紧为“本地项目管家控制台 / Harness Caretaker”。
- 更新 `HERMES_STEWARD.md`，明确 OpenCode 只承担部分管家执行职责，不是 Hermes 本体，也不是默认业务开发执行器。
- 更新 `MODEL_ROLES.md`，将“本地 / 低成本 Runner”改为“本地管家型工具 / 低成本记忆维护工具”。
- 更新 `WORKFLOW.md`，明确开发执行器和管家工具分离。
- 更新 `AGENTS.md`，补充 OpenCode 偏向项目记忆与规则管护，不作为默认业务开发主力。

验证：

- 未修改业务代码。
- 未运行安装、构建、测试或提交。

## 2026-05-29

任务：Hermes Project Steward 概念纠偏。

变更：

- 新增 `HERMES_STEWARD.md`：定义 Hermes Project Steward 的定位、能力、路线和与工具的关系。
- 更新 `AGENTS.md`：新增"Hermes Steward 原则"，明确长期目标是孵化 Hermes-style Project Steward。
- 更新 `PROJECT_MAP.md`：在 Harness 文档列表中加入 `HERMES_STEWARD.md`。
- 更新 `WORKFLOW.md`：说明跨工具交接、上下文压缩、项目记忆维护属于 Hermes Steward 任务。
- 更新 `MODEL_ROLES.md`：新增 Hermes Steward 角色。
- 更新 `OPENCODE_USAGE.md`：说明 OpenCode 不等于 Hermes Steward 本体。

概念修正：

- Harness Engineering 是方法论。
- Agent Harness 是底座。
- Hermes Project Steward 是长期管家型 Agent 形态。
- OpenCode 当前可承担 Hermes Steward v0.1 的部分管家执行职责，但 OpenCode 不等于 Hermes Steward。
- 长期稳定的是规则、AI_MEMORY、任务角色和 Hermes Steward 的行为规范。

验证：

- 未修改业务代码。
- 未运行安装、构建或提交。

## 2026-05-29

任务：补充工具可替换原则与日常任务模板。

变更：

- 更新 `AGENTS.md`，新增“工具可替换原则”小节。
- 新增 `TASK_TEMPLATES.md`，提供十个可复制的日常任务模板。
- 更新 `AI_MEMORY/TASK_LOG.md`，记录本轮极小 Markdown 补丁。

验证：

- 未修改业务代码。
- 未运行安装、构建或提交。

## 2026-05-29

任务：将工具固定分工改为角色优先、工具可替换策略。

变更：

- 更新 `MODEL_ROLES.md`，明确稳定的是任务角色，不是具体工具。
- 保留并优化 Product Steward、Architecture Steward、Memory Steward、Markdown Rule Maintainer、Read-only Auditor、Small Patch Implementer、Frontend UI Maintainer、Backend Maintainer、Boundary Guardian、Experiment Runner、Delivery Reporter 等角色。
- 将“推荐工具匹配”改为“工具选择参考”，覆盖高智能 / 高成本模型工具、本地管家型工具 / 低成本记忆维护工具、前端体验型工具、实验型工具。
- 增加工具选择规则：按任务风险、模型质量、套餐性价比、上下文、本地读写、只读审计、低成本重复执行和架构判断需求选择工具。
- 更新 `WORKFLOW.md`，将 Kiro / OpenCode / Codex / Trae / Antigravity 等固定描述改为当前可选工具示例。
- 更新 `OPENCODE_USAGE.md`，保留 OpenCode 第一阶段定位，同时说明它不是唯一管家工具。

验证：

- 未修改业务代码。
- 未运行安装、构建或提交。

## 2026-05-29

任务：创建本地 Agent Harness 规则与 AI_MEMORY。

变更：

- 新增 `AGENTS.md`：跨工具 Agent 总规则。
- 新增 `PROJECT_MAP.md`：项目地图与模块边界。
- 新增 `DECISIONS.md`：当前已裁决产品 / 架构决策。
- 新增 `CHECKLISTS.md`：任务前后检查清单。
- 新增 `WORKFLOW.md`：跨 Kiro / OpenCode / Codex / Trae / Antigravity 协作流程。
- 新增 `MODEL_ROLES.md`：角色分工。
- 新增 `OPENCODE_USAGE.md`：OpenCode 第一阶段使用边界。
- 新增 `AI_MEMORY/CURRENT_STATE.md`：当前状态与待确认事项。
- 新增 `AI_MEMORY/CONTEXT_BRIEF.md`：下一轮上下文摘要。
- 新增 `AI_MEMORY/CHANGELOG_AI.md`：AI 文档变更记录。
- 新增 `AI_MEMORY/TASK_LOG.md`：任务日志。
- 新增 `AI_MEMORY/SKILL_REGISTRY.md`：本地 Harness 可复用技能登记。

文档冲突裁决：

- SQLite 主库描述被 PostgreSQL 主库决策覆盖。
- 本地 embedding 主方案被云端 embedding 决策覆盖。
- 阿瓦隆主线推进被实验性隔离规范覆盖。
- RAG / 文件上传主流程被冻结决策覆盖。
- OpenCode 第一阶段禁止安装、构建、自动提交。

验证：

- 读取了四份 Kiro steering 文件。
- 读取了只读文件清单。
- 未运行安装、构建或提交。
