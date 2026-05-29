# Skill Registry

本文件登记本地 Agent Harness 可复用技能。这里的“技能”不是业务功能，而是不同 Agent 可以复用的任务能力与边界。

## Markdown Rule Maintainer

用途：

- 创建、更新、整理 Harness 规则文件。
- 裁决旧文档与当前决策冲突。
- 保持规则可读、可交接、可执行。

允许文件：

- `AGENTS.md`
- `PROJECT_MAP.md`
- `DECISIONS.md`
- `CHECKLISTS.md`
- `WORKFLOW.md`
- `MODEL_ROLES.md`
- `OPENCODE_USAGE.md`
- `AI_MEMORY/*.md`

禁止：

- 顺手修改业务代码。
- 把未验证代码状态写成事实。

## Memory Steward

用途：

- 更新当前状态。
- 压缩上下文。
- 记录任务流水。
- 维护待确认事项。

允许文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/CONTEXT_BRIEF.md`
- `AI_MEMORY/CHANGELOG_AI.md`
- `AI_MEMORY/TASK_LOG.md`
- `AI_MEMORY/SKILL_REGISTRY.md`

输出：

- 本轮记忆更新说明。
- 下一轮 Agent 需要知道的最短上下文。

## Read-only Auditor

用途：

- 对照规则读取代码或文件清单。
- 找出文档与实际代码不一致处。
- 输出风险，不直接修。

默认允许：

- 文件清单。
- 只读搜索。
- 只读查看 Markdown 和代码片段。

默认禁止：

- 修改文件。
- 安装依赖。
- 构建。
- 提交。

## Small Patch Implementer

用途：

- 在用户明确授权时做小范围低风险修复。

前置条件：

- 已读取 `AGENTS.md`、`DECISIONS.md`、`PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md`。
- 已确认修改文件范围。
- 已确认不触碰冻结模块，或任务明确要求触碰。

交付要求：

- 文件清单。
- 数据流说明。
- 验证与未验证。
- 回滚建议。

## Boundary Guardian

用途：

- 审计 Provider / History / ChatDock / TTS / RAG / DB / Auth 边界。
- 阻止历史记录污染当前用户资料。
- 阻止 RAG / 上传入口误接回主流程。

重点规则：

- Provider 只管模型与供应商。
- `userStore` 是当前资料来源。
- History 只管归档与恢复上下文。
- TTS 手动朗读。
- RAG 冻结。
- PostgreSQL 主库。

## Delivery Reporter

用途：

- 把每轮工作变成可交接报告。

必须包含：

- 任务目标。
- 实际范围。
- 修改文件。
- 未处理范围。
- 已执行验证。
- 未执行验证。
- 风险与待确认。
- 建议下一步。

