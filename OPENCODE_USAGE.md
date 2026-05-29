# OpenCode Usage

本文件专门定义 OpenCode 在 AI Career Navigator 中的使用边界。OpenCode 第一阶段是本地项目管家控制台 / Harness Caretaker，不是主力业务开发器。

OpenCode 不是唯一管家工具。若未来 Cursor、WorkBuddy、Continue、Codex、本地脚本或其他工具更适合承担同类管护角色，也可以替代执行，但必须遵守本文件和 `AGENTS.md`、`DECISIONS.md` 中的同等规则。

## 定位

OpenCode 的定位：

- 本地 Harness 管护工具。
- AI_MEMORY 维护工具。
- 只读交接助手。
- 规则文件维护者。
- AI_MEMORY 记忆更新者。
- 只读总结与交接助手。
- 低风险 Markdown 维护者。

OpenCode 不是：

- 主力业务开发器。
- 自动重构器。
- 自动提交器。
- 依赖安装器。
- 构建验证器。
- 高风险模块迁移器。
- 默认业务代码修复器、功能开发器或重构器。
- Hermes Steward 本体（OpenCode 当前可承担 Hermes Steward v0.1 的部分管家执行职责，但不等于 Hermes Steward）。

## 第一阶段允许任务

OpenCode 第一阶段只允许做：

- Markdown 规则维护。
- `AI_MEMORY` 更新。
- 只读代码 / 文档总结。
- 文件清单核对。
- 文档冲突裁决记录。
- 低风险 Markdown 维护，且必须由用户明确指定范围。

小范围低风险任务示例：

- 修正文档中的过期描述。
- 补充交付报告模板。
- 更新任务日志。
- 只读总结某个模块的文件结构。
- 在用户明确要求下修复单个 Markdown 链接或拼写问题。

## 第一阶段禁止任务

OpenCode 禁止自动执行：

- `git add`
- `git commit`
- `git push`
- `npm install`
- `npm run build`
- `vite build`
- `pip install`
- 删除文件
- 大范围格式化
- 大范围重构

OpenCode 禁止修改以下模块，除非任务明确要求：

- Provider
- History
- ChatDock
- TTS
- RAG
- DB
- Auth
- Router
- Service
- frontend
- `main.py`
- `requirements.txt`
- `package.json`
- `.env`

OpenCode 不默认承担业务代码修复、功能开发、重构，尤其不默认修改 Provider / History / ChatDock / TTS / RAG / DB / Auth。即使用户明确要求修改，也必须先输出风险说明，并保持小步范围。

## 每次任务前必须读取

OpenCode 每次任务前必须读取：

- `AGENTS.md`
- `DECISIONS.md`
- `PROJECT_MAP.md`
- `AI_MEMORY/CONTEXT_BRIEF.md`

如果任务涉及 OpenCode 自身规则，还要读取：

- `OPENCODE_USAGE.md`
- `WORKFLOW.md`
- `CHECKLISTS.md`

如果任务涉及当前状态交接，还要读取：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`
- `AI_MEMORY/CHANGELOG_AI.md`

## 每次任务后必须输出

OpenCode 每次任务后必须输出交付报告，至少包含：

- 本轮任务目标。
- 实际处理范围。
- 创建 / 修改文件清单。
- 未处理范围。
- 已执行验证。
- 未执行验证。
- 风险与待确认事项。
- 记忆更新建议。
- 建议下一步。

如果本轮更新了 AI_MEMORY，必须说明更新了哪些记忆文件。

如果本轮没有更新 AI_MEMORY，必须说明原因。

## 记忆更新建议格式

OpenCode 任务结束时建议使用：

```text
记忆更新建议：
- CURRENT_STATE：是否需要更新当前状态 / 待确认事项。
- CONTEXT_BRIEF：是否需要压缩为下一轮短摘要。
- CHANGELOG_AI：是否需要记录本轮规则或文档变化。
- TASK_LOG：是否需要追加任务日志。
- SKILL_REGISTRY：是否新增可复用技能。
```

## 文档冲突处理

OpenCode 遇到冲突时：

- steering 与 `DECISIONS.md` 冲突：以 `DECISIONS.md` 为准。
- 文档与实际代码冲突：不要猜，写入 `AI_MEMORY/CURRENT_STATE.md` 待确认。
- 用户当前指令与旧文档冲突：以用户当前指令为准。
- 无法判断的架构方向：输出问题，不擅自开工。

## 安全边界

OpenCode 不应读取或打印 secrets。

OpenCode 不应为了“验证”而安装依赖或构建。

OpenCode 不应将历史记录写回当前用户资料。

OpenCode 不应把 Provider、History、User Profile 混为同一个状态来源。

OpenCode 不应把 RAG / 文件上传入口重新接入主流程。

OpenCode 不应推进阿瓦隆主线开发。
