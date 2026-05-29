# Model Roles

本文件定义 AI Career Navigator 本地 Harness 中的任务角色。核心原则：稳定的是“任务角色”，不是“具体工具”。任何工具都只是可替换执行器，不是长期固定岗位。

## 角色优先原则

本项目不把任何具体工具绑定为固定岗位。长期稳定的是任务角色，具体工具根据当期性价比、可用模型、上下文能力、执行稳定性和用户偏好临时选择。

工具包括但不限于：

- Kiro
- OpenCode
- Codex
- Trae
- Antigravity
- Cursor
- WorkBuddy
- Continue
- DeepSeek / GLM 接入工具
- 未来新增的 vibe coding 工具

任何工具进入项目后，都必须先读取：

- `AGENTS.md`
- `DECISIONS.md`
- `PROJECT_MAP.md`
- `AI_MEMORY/CONTEXT_BRIEF.md`

不要因为某个工具以前常用，就默认继续使用。不要因为某个工具能写代码，就给它全仓库权限。

## 总原则

- 规划者不直接大改业务代码。
- 实现者必须先读规则和现状。
- 审计者优先报告风险，不抢修无关问题。
- 记忆维护者默认只写 Markdown 和 `AI_MEMORY`。
- 实验者必须隔离实验成果。
- 工具选择必须服从任务风险、模型能力、成本和用户当前选择。

## 任务角色

| 角色 | 适合任务 | 默认权限 | 禁止事项 | 交付物 |
|---|---|---|---|---|
| Product Steward | 产品边界、功能优先级、主线冻结裁决 | Markdown / 只读 | 直接大改业务代码、绕过用户决策 | 决策记录、需求边界、冻结说明 |
| Architecture Steward | 架构分层、模块边界、数据流审计 | Markdown / 只读 | 未验证即推进迁移、扩大重构范围 | 架构说明、风险报告、迁移建议 |
| Memory Steward | `AI_MEMORY` 更新、上下文压缩、交接摘要 | Markdown | 修改业务代码、把待确认写成事实 | `CURRENT_STATE`、`CONTEXT_BRIEF`、`TASK_LOG` 更新 |
| Markdown Rule Maintainer | Harness 规则、清单、流程文档维护 | Markdown | 顺手改业务代码、把工具绑定为固定岗位 | 规则文档补丁、冲突裁决记录 |
| Read-only Auditor | 代码与文档一致性检查、风险发现 | 只读 | 未授权修改文件、替用户做方向裁决 | 发现列表、证据、待确认事项 |
| Small Patch Implementer | 小范围低风险修复、明确 bug 修复 | 明确授权文件 | 大范围重构、触碰冻结模块、自动提交 | 补丁、验证结果、回滚建议 |
| Frontend UI Maintainer | UI polish、组件交互微调、视觉一致性修复 | 明确授权前端文件 | 改业务数据流、改 Provider / History / DB | 组件修复、截图或验收路径 |
| Backend Maintainer | API、服务、数据库小步修复 | 明确授权后端文件 | 未报告数据库/API 变化、绕过架构层级 | 后端补丁、数据风险说明、接口说明 |
| Boundary Guardian | Provider / History / ChatDock / TTS / RAG / DB / Auth 边界审计 | 只读 / Markdown | 擅自修改高风险模块、混合状态来源 | 边界风险报告、阻断建议 |
| Experiment Runner | 隔离原型、方案比较、不确定路径探索 | 实验目录 / 独立分支 | 实验污染主线、把原型当主线交付 | 原型报告、是否进入主线建议 |
| Delivery Reporter | 交付报告、验证记录、未完成事项整理 | Markdown / 报告 | 伪造验证、隐瞒未执行检查 | 交付报告、验证与未验证清单 |
| Hermes Steward | 长期项目记忆、跨工具交接、规则演进、上下文压缩、任务分发建议 | Markdown / AI_MEMORY / 只读审计 | 自动大改业务代码、绕过用户确认、把工具绑定为固定岗位 | 交接摘要、任务日志、规则演进记录、工具推荐 |

## 工具选择参考

以下不是固定分工，只是当前选择工具时的参考。具体工具可以是 Kiro、OpenCode、Codex、Trae、Antigravity、Cursor、WorkBuddy、Continue 或未来新增工具。

### 高智能 / 高成本模型工具

适合：

- 架构判断。
- 复杂只读审计。
- 跨模块任务拆解。
- 高质量规则文档生成。
- 疑难 bug 小步修复。

使用限制：

- 不做低价值重复任务。
- 不长期承担每日流水账维护。
- 不因为模型强就获得全仓库权限。

### 本地管家型工具 / 低成本记忆维护工具

适合：

- `AI_MEMORY` 更新。
- Markdown 维护。
- 只读总结。
- 文件清单核对。
- 交接摘要。
- 低风险文档维护。

使用限制：

- 不默认业务代码开发。
- 不承担跨模块修复。
- 不默认修改 Provider / History / ChatDock / TTS / RAG / DB / Auth。
- 不自动安装依赖、构建、提交。
- 不替代高质量架构判断。

业务开发主力应从 Trae / Kiro / Cursor / Codex / WorkBuddy / Antigravity 等可替换 coding tools 中按当期模型能力和性价比选择。

### 前端体验型工具

适合：

- UI polish。
- 组件交互微调。
- 视觉一致性修复。
- 响应式和可用性检查。

使用限制：

- 不改业务数据流。
- 不改 Provider / History / DB。
- 不把 ChatDock 扩成三大功能页替代品。

### 实验型工具

适合：

- 隔离原型。
- 不确定方案探索。
- 非主线方案比较。

使用限制：

- 实验不能直接污染主线。
- 实验结论必须回写为文档或待确认事项。
- 不把原型代码直接合并到主流程。

## 工具选择规则

选择工具时优先考虑：

1. 当前任务风险等级。
2. 当前工具可用模型质量。
3. 当前套餐性价比。
4. 是否需要长上下文。
5. 是否需要本地文件读写。
6. 是否需要只读审计。
7. 是否需要低成本重复执行。
8. 是否需要高质量架构判断。

不要因为某个工具以前常用，就默认继续使用。
不要因为某个工具能写代码，就给它全仓库权限。
不要让任何工具绕过 `AGENTS.md` 和 `DECISIONS.md`。

## 关键模块的推荐角色

Provider：

- 推荐由 Architecture Steward、Boundary Guardian 或 Backend Maintainer 审计。
- 未明确要求不得修改，任何工具都不能默认获得修改权。

History：

- 推荐由 Backend Maintainer、Boundary Guardian 和 Read-only Auditor 协作处理。
- 必须报告数据库变化、用户隔离风险和历史记录是否污染当前资料。

ChatDock：

- 推荐由 Frontend UI Maintainer、Small Patch Implementer 和 Boundary Guardian 协作处理。
- 必须保持 Dashboard 助手定位。

TTS：

- 推荐由 Small Patch Implementer 和 Boundary Guardian 处理。
- 必须保持手动朗读。

RAG：

- 推荐只读审计或 Architecture Steward 处理。
- 当前冻结，不接主流程。

DB：

- 推荐由 Backend Maintainer 和 Boundary Guardian 处理。
- PostgreSQL 为主，SQLite 只做兼容或待迁移说明。

Auth：

- 默认高风险模块。
- 未明确要求不得修改。

## 输出风格

所有角色都必须：

- 说明做了什么。
- 说明没做什么。
- 说明哪些判断来自文档，哪些来自只读检查。
- 不把待确认写成事实。
- 不自动提交。
