# AI Career Navigator Agent Harness Rules

本文件是 One-stop-AI-career-navigator / AI Career Navigator 的跨工具 Agent 总入口。所有本地 Agent、Kiro、OpenCode、Codex、Trae、Antigravity 在执行任务前，都应先读取默认入口 5 件套：`PROJECT_BRIEF.md`、`AGENTS.md`、`DECISIONS.md`、`HERMES_TOOL_POLICY.md`、`AI_MEMORY/CURRENT_STATE.md`。

## 目标

本仓库的 Agent Harness 目标是低成本、可控、可持续地辅助开发，而不是让任何单一工具无边界地改业务代码。

- 优先保护已有产品主线：Dashboard、ChatDock、简历诊断、职业规划、模拟面试、文档工作台、Resume Builder Beta、TTS 手动朗读、多模型切换、历史记录归档。
- 优先保护用户资料、Provider、历史记录、数据库、RAG、TTS 等跨模块边界。
- 优先小步任务、小范围修改、可回滚交付。
- 任何 Agent 都不得用“看起来能跑”替代真实验证报告。

## 工具可替换原则

本项目不把 Kiro、OpenCode、Codex、Trae、Antigravity、Cursor、WorkBuddy 或任何具体工具绑定为长期固定岗位。

长期稳定的是任务角色、项目规则和 AI_MEMORY 记忆层；具体工具根据当期模型能力、套餐性价比、上下文长度、文件读写能力、执行稳定性和用户当次选择临时决定。

任何工具即使模型能力很强，也不能因此获得全仓库默认修改权。所有工具都必须遵守 AGENTS.md、DECISIONS.md、HERMES_TOOL_POLICY.md 和 AI_MEMORY/CURRENT_STATE.md。

- 工具名不决定角色，任务模式决定角色。
- 所有 vibe coding tools 进入项目后先读 5 件套：`PROJECT_BRIEF.md`、`AGENTS.md`、`DECISIONS.md`、`HERMES_TOOL_POLICY.md`、`AI_MEMORY/CURRENT_STATE.md`。
- 执行类任务完成后，除聊天窗口交付报告外，应按任务要求写入 `AI_MEMORY/INBOX/`。
- 不确定是否写入 INBOX 时，必须在交付报告中写明“建议是否更新 AI_MEMORY”。
- `AI_MEMORY/INBOX/` 中内容是待 Hermes 主导消化的交付记录，不等同于已确认事实。
- Hermes 消化后，才决定是否更新 `CURRENT_STATE.md`、`TASK_LOG.md`、`PROJECT_BRIEF.md`。

## Hermes Steward 原则

本项目的长期目标不是绑定某个 coding 工具，而是孵化 Hermes-style Project Steward。

核心理念：

- Harness Engineering 是方法论。
- Agent Harness 是底座。
- Hermes Project Steward 是长期管家型 Agent 形态。
- OpenCode 当前可承担 Hermes Steward v0.1 的部分管家执行职责，但 OpenCode 不等于 Hermes Steward 本体。
- OpenCode 当前偏向项目记忆与规则管护，不作为默认业务开发主力。
- 长期稳定的是规则、AI_MEMORY、任务角色和 Hermes Steward 的行为规范。

详见 `HERMES_STEWARD.md`。

## 信息优先级

当文档、代码、用户指令冲突时，按以下顺序裁决：

1. 用户当前明确指令。
2. `DECISIONS.md` 中的已裁决决策。
3. `AI_MEMORY/CURRENT_STATE.md` 的当前状态与待确认事项。
4. `.kiro/steering/*.md` 中未被覆盖的长期规则。
5. 实际代码与只读检查结果。

如果实际代码与文档冲突，且没有足够证据判断正确方向，必须写入 `AI_MEMORY/CURRENT_STATE.md` 的“待确认事项”，不要擅自猜测。

## 默认读取清单

每次任务开始前至少读取：

- `PROJECT_BRIEF.md`
- `AGENTS.md`
- `DECISIONS.md`
- `HERMES_TOOL_POLICY.md`
- `AI_MEMORY/CURRENT_STATE.md`

二级参考 / 按需读取：

- `PROJECT_MAP.md`
- `AI_MEMORY/CONTEXT_BRIEF.md`
- `MODEL_ROLES.md`
- `WORKFLOW.md`
- `TASK_TEMPLATES.md`
- `CHECKLISTS.md`
- `HERMES_STEWARD.md`
- `OPENCODE_USAGE.md`
- `.kiro/steering/*`

涉及工具分工时，再读取：

- `MODEL_ROLES.md`
- `OPENCODE_USAGE.md`
- `WORKFLOW.md`
- `CHECKLISTS.md`

涉及现状交接时，再读取：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`
- `AI_MEMORY/CHANGELOG_AI.md`
- `AI_MEMORY/SKILL_REGISTRY.md`

## 当前硬性决策

- PostgreSQL 是主数据库；SQLite 不能作为主数据库继续扩展。
- RAG 使用云端 embedding；不使用本地 embedding 作为主方案，避免 2C4G 服务器崩溃。
- 阿瓦隆 / 职场情商对抗模拟器只保留实验性隔离模块规范，当前不进入主线开发。
- Resume Builder 是 Beta 辅助功能，不继续深挖高级模板或 AI 美工。
- ChatDock 是 Dashboard AI 助手，不承诺完整替代简历诊断、职业规划、模拟面试三功能页。
- TTS 先做手动朗读，不做默认自动朗读。
- RAG / 文件上传入口冻结，暂不接知识库主流程。
- 主题系统只迁移品牌装饰色，不迁移语义色。
- Provider、当前用户资料、历史记录必须边界清楚。
- 当前用户资料以 `userStore` 最新值为准，历史记录不能反向污染当前资料。
- 小步提交，避免大改；Agent 不得自动 `git add` 或 `git commit`。

## Python 运行环境规则

- 本项目 Python 环境固定为项目根目录 `.venv`。
- 禁止 Agent 在本项目中裸运行 `python`、`pip`、`uvicorn`、`celery`。
- 禁止把项目依赖安装到 Hermes venv。
- PowerShell 启动后端必须调用：
  `.\scripts\start-backend.ps1`
- Git Bash / Hermes Desktop 启动后端必须调用：
  `bash scripts/start-backend.sh`
- 安装依赖必须通过项目 `.venv\Scripts\python.exe -m pip`。
- 若检测到解释器或 `sys.path` 包含 `hermes-agent`，必须停止。
- 项目启动脚本会在自身执行范围内清理外部 Agent 注入的 `PYTHONPATH` / `PYTHONHOME`；不得因此修改用户级或系统级环境变量。

## 禁止事项

除非用户在当前任务中明确要求，否则禁止：

- 修改 Router、Service、frontend、`main.py`、`requirements.txt`、`package.json`、`.env` 等业务或配置文件。
- 运行 `npm install`、`pip install`、`npm run build`、`vite build`、`tsc`、`vue-tsc`。
- 自动执行 `git add`、`git commit`、`git push`。
- 删除文件或执行大范围不可逆清理。
- 打印 `.env`、API Key、JWT Secret、数据库密码等敏感信息。
- 把历史记录数据写回当前用户资料。
- 把 Provider 选择、用户资料快照、历史记录 payload 混成同一状态源。

## 允许的低风险任务

在没有额外授权时，Agent 可以做：

- 只读审计、规则总结、文件清单检查。
- 创建或维护 Markdown 规则文件。
- 更新 `AI_MEMORY` 中的当前状态、任务日志、交接摘要。
- 小范围、明确、可回滚的低风险修复，但必须先确认不触碰冻结模块。

## 架构边界

后端长期边界：

- `Router/` 只处理 HTTP 协议层、参数校验和响应。
- `Service/` 负责业务编排。
- `Service/Agents/` 负责 Agent 角色、Prompt 与 LLM 调用规范。
- `Service/Utils/` 负责通用工具、数据库访问、LLM/Embedding/TTS SDK 封装。
- 配置入口应统一收敛，不在业务代码里散落读取环境变量。

前端长期边界：

- Vue / Vite / Pinia / Tailwind 暗黑赛博 UI。
- 页面级 SFC 保持清晰，复用组件优先放入 `frontend/src/components/`。
- 弹窗优先复用 `BaseModal.vue`。
- Toast 优先复用 `Toast.vue`。
- SSE / AI 等待态优先复用 `StreamingLoader.vue`。
- 图标优先使用既有图标库。

状态边界：

- `llmProviderStore` 或 Provider 客户端只负责模型/供应商选择。
- `userStore` 只负责当前用户资料与最新画像。
- `chatSessionStore` / history 客户端只负责会话与历史归档。
- 历史记录可用于“查看、恢复上下文、对比”，不能自动覆盖当前资料。

## 交付要求

每次任务结束必须说明：

- 创建或修改了哪些文件。
- 哪些规则或代码已实现，哪些只是文档约束。
- 实际执行了哪些验证，哪些没有执行。
- 是否涉及数据库、API、前端状态、Provider、RAG、TTS、History。
- 待用户确认事项。
- 建议下一步。

不得把未验证内容写成“已闭环”。
