# Task Templates

这些模板用于日常复制给 Kiro / OpenCode / Codex / Trae / WorkBuddy / DeepSeek / GLM 或其他可替换工具。使用前按当前任务删减范围，默认遵守 `AGENTS.md`、`DECISIONS.md`、`PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md`。

## 1. 新工具进入项目自检模板

请先只读本项目规则，不修改文件。读取 `AGENTS.md`、`DECISIONS.md`、`PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md`，输出：你理解的任务边界、禁止事项、当前待确认事项、适合承担的任务角色。

## 2. OpenCode 只读自检模板

你是本轮只读 Harness Runner。请读取 `AGENTS.md`、`OPENCODE_USAGE.md`、`DECISIONS.md`、`PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md`，只做总结，不改文件，不安装、不构建、不提交。

## 3. AI_MEMORY 更新模板

请只更新 `AI_MEMORY` 下相关 Markdown。记录本轮任务目标、已处理范围、未处理范围、验证情况、待确认事项和下一步建议。不要修改业务代码。

## 4. 高智能模型只读审计模板

请作为 Read-only Auditor 审计指定模块。只读代码和文档，重点找架构边界、数据流、Provider / History / userStore 污染风险。输出证据、风险等级和建议，不直接修复。

## 5. 小范围代码修复模板

请只修复以下明确问题：`[填写问题]`。允许修改文件：`[填写文件]`。禁止扩大重构、禁止安装、禁止构建、禁止提交。完成后说明改动、验证、未验证和回滚方式。

## 6. 前端 UI polish 模板

请只做前端 UI polish：`[填写页面/组件]`。保持暗黑赛博风格，优先复用现有组件，不改业务数据流，不改 Provider / History / DB。输出视觉改动和人工验收路径。

## 7. 后端接口小改模板

请只做后端接口小改：`[填写接口/问题]`。遵守 Router / Service / Utils 分层，报告请求响应变化、数据库影响、兼容性和验证结果。禁止顺手改无关接口。

## 8. diff review 模板

请 review 当前 diff，不修改文件。优先报告 bug、回归风险、数据污染、边界破坏和缺失测试。按严重程度排序，给出文件和证据，最后列出开放问题。

## 9. 每日收工报告模板

请整理今日收工报告：已完成、已验证、未验证、未提交文件、风险、待用户确认、明日第一步。不得把未验证内容写成已完成。

## 10. 上下文压缩模板

请把当前上下文压缩为下一轮可接手摘要。包括项目目标、当前决策、最近改动、未完成任务、禁止事项、关键文件和待确认事项。优先短、准、可执行。

## 11. 交付报告增强模板

请按以下结构输出交付报告：

- 本轮任务目标
- 修改文件
- 未修改范围
- 已执行验证
- 未执行验证
- 是否涉及数据库变化
- 是否涉及 API / 数据流变化
- 是否涉及前端状态 / localStorage / store
- untracked 文件说明
- 用户可见验收路径
- 风险与回滚建议
- 是否建议更新 AI_MEMORY
- 下一步建议

## 12. 执行器任务模板

请按以下结构执行：

- 本轮角色
- 读取文件
- 允许修改
- 禁止修改
- 是否需要写 `AI_MEMORY/INBOX/`
- INBOX 文件名建议
- 交付报告格式

如需写入 INBOX，优先参考 `AI_MEMORY/INBOX/TEMPLATE.md`。
