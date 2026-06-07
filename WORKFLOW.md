# Workflow

本文件定义 AI Career Navigator 的本地 Agent Harness 协作流程。目标是让不同可替换工具在同一个仓库内交接任务，而不会互相覆盖、扩大范围或污染主线。当前可选工具示例包括 Kiro、OpenCode、Codex、Trae、Antigravity、Cursor、WorkBuddy、Continue 和未来新增的 vibe coding 工具，但它们都不是长期固定岗位。

## 标准流程

### 1. 进入任务

Agent 先读取：

- `PROJECT_BRIEF.md`
- `AGENTS.md`
- `DECISIONS.md`
- `HERMES_TOOL_POLICY.md`
- `AI_MEMORY/CURRENT_STATE.md`

然后判断任务类型：

- 只读审计
- Markdown 规则维护
- AI_MEMORY 更新
- 小范围低风险修复
- 业务功能实现
- 高风险迁移

如果任务类型不明确，先按更保守的类型处理。

### 2. 明确范围

任务开始前必须确认：

- 本轮允许修改哪些文件。
- 本轮禁止修改哪些文件。
- 是否涉及 Provider / History / ChatDock / TTS / RAG / DB / Auth。
- 是否允许运行服务、测试、安装、构建、提交。
- 是否需要更新 AI_MEMORY。

### 3. 小步执行

推荐节奏：

1. 只读检查项目现状。
2. 记录冲突和待确认事项。
3. 做最小必要修改。
4. 执行允许范围内的验证。
5. 更新任务日志和记忆。
6. 输出交付报告。

禁止把多个高风险变更合并成一次“大修”。

### 4. 验证策略

默认可做：

- 文件存在性检查。
- Markdown 内容检查。
- 只读搜索。
- 局部单元测试，前提是不会触发依赖安装或构建。

默认不做：

- `npm install`
- `pip install`
- `npm run build`
- `vite build`
- `tsc`
- `vue-tsc`
- 自动提交。

未执行的验证必须如实报告。

### 5. 交付报告

每次结束输出：

- 创建 / 修改文件清单。
- 各文件用途。
- 已裁决的文档冲突。
- 待用户确认事项。
- 建议下一步。

如果是代码任务，还必须补充：

- 数据库变化。
- API 变化。
- 前端状态变化。
- 用户可见验收路径。
- 回滚建议。

## 工具选择流程

本项目不做固定工具分工。工具只是执行器，最终以任务风险、可用模型能力、上下文长度、成本、用户当前套餐和用户当次选择为准。

### 当前可选工具示例

可选工具包括但不限于：

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

### 选择步骤

1. 先确定任务角色：Product Steward、Architecture Steward、Memory Steward、Read-only Auditor、Small Patch Implementer、Frontend UI Maintainer、Backend Maintainer、Boundary Guardian、Experiment Runner 或 Delivery Reporter。
2. 再判断任务风险：只读、Markdown、低风险小补丁、高风险业务改动、实验原型。
3. 再选择工具：看当前模型质量、套餐性价比、上下文能力、本地文件读写能力、执行稳定性和用户偏好。
4. 最后设置权限：任何工具都只获得本轮任务所需的最小权限。

### 参考类别

高智能 / 高成本模型工具适合架构判断、复杂只读审计、跨模块任务拆解、高质量规则文档生成和疑难 bug 小步修复；不适合低价值重复维护。

本地管家型工具 / 低成本记忆维护工具适合 `AI_MEMORY` 更新、Markdown 维护、只读总结、文件清单核对、交接摘要和低风险文档维护；不得默认承担业务代码开发，不得自动安装依赖、构建或提交。

前端体验型工具适合 UI polish、组件交互微调和视觉一致性修复；不得改业务数据流、Provider、History 或 DB。

实验型工具适合隔离原型和不确定方案探索；实验不能直接污染主线，结论必须回写为文档或待确认事项。

### 统一约束

- 不要因为某个工具过去常用，就默认继续使用。
- 不要因为某个工具能写代码，就给它全仓库权限。
- 不要让任何工具绕过 `AGENTS.md` 和 `DECISIONS.md`。
- 开发执行器和管家工具分离。OpenCode 默认偏管家任务；业务开发任务应单独选择最合适的 coding tool。
- Kiro、Codex、Trae、Antigravity、Cursor、WorkBuddy 等都只能作为当前可选执行器，不是长期组织岗位。

## 记忆更新规则

每轮任务后，视情况更新：

- `AI_MEMORY/CURRENT_STATE.md`：当前状态、冲突、待确认。
- `AI_MEMORY/CONTEXT_BRIEF.md`：给下一位 Agent 的短摘要。
- `AI_MEMORY/CHANGELOG_AI.md`：文档或规则变更记录。
- `AI_MEMORY/TASK_LOG.md`：任务日志。
- `AI_MEMORY/SKILL_REGISTRY.md`：可复用任务能力。

如果没有更新，交付报告里说明原因。

## Hermes Steward 任务

跨工具交接、上下文压缩、项目记忆维护、规则演进属于 Hermes Steward 任务范畴。详见 `HERMES_STEWARD.md`。

具体管家执行器可临时选择 OpenCode / Codex / WorkBuddy / 其他工具；业务开发执行器应另按任务风险、模型能力和性价比选择，并必须遵守 Hermes Steward 的行为规范。

## 任务交付记录流

用户 / GPT-5.5 CTO / Hermes 生成任务
→ Vibe Coding Tool 执行
→ 输出聊天交付报告
→ 如任务重要，写入 `AI_MEMORY/INBOX/`
→ Hermes 主导消化，或由用户指定的 Vibe Coding Tool 辅助整理
→ 更新 `CURRENT_STATE.md` / `TASK_LOG.md` / `PROJECT_BRIEF.md`
