# Checklists

本文件提供跨 Kiro / OpenCode / Codex / Trae / Antigravity 的任务检查清单。每个 Agent 可以按任务类型摘取对应清单，但不得跳过红线检查。

## 任务前总检查

- 已读取 `AGENTS.md`。
- 已读取 `DECISIONS.md`。
- 已读取 `PROJECT_MAP.md`。
- 已读取 `AI_MEMORY/CONTEXT_BRIEF.md`。
- 已确认本轮任务是否允许修改业务代码。
- 已确认是否触碰 Provider、History、ChatDock、TTS、RAG、DB、Auth。
- 已确认是否涉及 `.env`、依赖文件、构建命令、数据库迁移。
- 已确认是否需要只读审计而不是直接修改。

## 红线检查

默认禁止：

- `npm install`
- `pip install`
- `npm run build`
- `vite build`
- `tsc`
- `vue-tsc`
- 自动 `git add`
- 自动 `git commit`
- 删除文件
- 打印 secrets
- 修改 `.env`

除非用户明确要求并说明范围，否则不得修改：

- `Router/`
- `Service/`
- `frontend/`
- `main.py`
- `requirements.txt`
- `package.json`
- Provider
- History
- ChatDock
- TTS
- RAG
- DB
- Auth

## Markdown 规则维护检查

- 只修改用户指定的 Markdown 文件。
- 不借规则维护顺手修改业务代码。
- 不把未验证的代码状态写成事实。
- steering 与当前决策冲突时，以 `DECISIONS.md` 为准。
- 实际代码与文档冲突时，写入 `AI_MEMORY/CURRENT_STATE.md` 待确认。
- 更新 `AI_MEMORY/CHANGELOG_AI.md`。
- 更新 `AI_MEMORY/TASK_LOG.md`。

## 后端任务检查

- Router 是否只处理 HTTP 协议层。
- Service 是否负责业务编排。
- Agent 是否通过统一 LLM Provider 调用。
- Prompt 是否集中在 prompts 层。
- SSE 是否复用统一工具。
- TTS 是否保持手动触发。
- RAG 是否未接回冻结主流程（D007：主入口冻结，后端 /api/kb/* 仅作 JWT 保护的实验性接口）。
- 数据库是否以 PostgreSQL 为主路径。
- 是否新增或修改 migration。
- 是否影响旧 SQLite 兼容路径。
- 是否打印或暴露敏感配置。

## 前端任务检查

- 是否符合 Vue / Vite / Pinia / Tailwind 暗黑赛博 UI。
- 是否复用 `BaseModal.vue`、`Toast.vue`、`StreamingLoader.vue`。
- 是否保持页面和组件边界清楚。
- 是否避免引入冲突 UI 库。
- ChatDock 是否仍是 Dashboard 助手，而非替代三大功能页。
- Resume Builder 是否保持 Beta 范围。
- TTS 是否为手动朗读。
- 主题是否只迁移品牌装饰色。
- 文案是否为简体中文。

## 状态与数据边界检查

- Provider 选择是否独立。
- 当前用户资料是否以 `userStore` 最新值为准。
- 历史记录是否只归档、查看、恢复上下文。
- 历史记录是否没有自动覆盖当前用户资料。
- ChatDock 会话状态是否与正式功能结果区分。
- Resume Builder 状态是否不污染用户主画像。
- RAG 上传或知识库状态是否未接入冻结主流程。

## 数据库检查

- 是否涉及 PostgreSQL。
- 是否仍依赖 SQLite。
- 是否新增表、字段、索引。
- 是否需要手动 SQL。
- 是否需要备份。
- 是否影响旧数据兼容。
- 是否涉及用户隔离。
- 是否报告了数据迁移风险。

## 交付报告检查

每次任务结束必须输出：

- 本轮实际处理范围。
- 创建或修改文件清单。
- 未处理范围。
- 已执行验证。
- 未执行验证。
- 数据库变化。
- API / 数据流变化。
- 风险与待确认事项。
- 回滚建议。
- 建议下一步。

不得输出：

- “已完成”但没有说明验证。
- “功能闭环”但没有实际验收。
- “无风险”但未检查状态边界。

## 交付前必报检查

- 是否报告 untracked 文件。
- 是否报告数据库变化。
- 是否报告 API / 数据流变化。
- 是否报告前端状态 / localStorage / store 变化。
- 是否明确未执行验证。
- 是否给出用户可见验收路径。
- 是否说明回滚建议。
- 是否避免“已写代码 = 已完成”的假闭环。
