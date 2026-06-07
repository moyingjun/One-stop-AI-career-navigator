# Decisions

本文件记录 AI Career Navigator 当前已裁决的产品、架构与 Harness 决策。若旧 steering、旧代码注释或历史对话与本文件冲突，以本文件为准。

更新时间：2026-05-29

## D001 PostgreSQL 是主数据库

状态：已裁决

决策：

- 项目主数据库使用 PostgreSQL。
- SQLite 不作为主数据库继续扩展。
- 旧 SQLite 文件或兼容实现只能用于迁移、兼容、回退参考，不得成为新功能主路径。

影响：

- History、用户、知识记录等持久化主线应以 PostgreSQL 为准。
- 任何新增表、字段、索引、migration 必须报告。
- 若实际代码仍依赖 SQLite，必须标为待确认或迁移任务。

冲突裁决：

- 覆盖 `.kiro/steering/tech.md` 中“SQLite 为数据库”的旧描述。

## D002 RAG 使用云端 embedding

状态：已裁决

决策：

- RAG 使用云端 embedding。
- 不使用本地 embedding 作为主方案，避免 2C4G 服务器内存或 CPU 压力失控。

影响：

- 不新增本地 HuggingFace embedding 主流程。
- 不把大模型、向量模型、批量分块索引任务压到低配服务器。
- RAG 相关代码若仍存在本地 embedding 入口，需要作为待确认事项处理。

冲突裁决：

- 覆盖 `.kiro/steering/tech.md` 中 HuggingFace 本地 embedding 主方案描述。

## D003 阿瓦隆只保留实验性隔离模块规范

状态：已裁决

决策：

- 阿瓦隆 / 职场情商对抗模拟器当前不进入主线开发。
- 可保留实验性隔离模块规范，不能牵动 Dashboard、History、RAG、Auth、Provider 等主线边界。

影响：

- 不新增阿瓦隆主线入口。
- 不为了阿瓦隆改核心 Router、Auth、RAG、DB。
- 若未来重启，必须单独立项并重新确认资源预算。

冲突裁决：

- 覆盖 `.kiro/steering/product.md`、`structure.md`、`tech.md` 中把阿瓦隆作为详细专项实现推进的倾向。

## D004 Resume Builder 保持 Beta 辅助功能

状态：已裁决

决策：

- Resume Builder 是 Beta 辅助功能。
- 不继续深挖高级模板、AI 美工、复杂排版系统。

影响：

- 允许做稳定性、数据保护、导出基础能力修复。
- 不做大规模模板市场、视觉生成、复杂主题编辑器。

## D005 ChatDock 是 Dashboard AI 助手

状态：已裁决

决策：

- ChatDock 是 Dashboard 的 AI 助手和轻量问答入口。
- 不承诺完整替代简历诊断、职业规划、模拟面试三大功能页。

影响：

- ChatDock 可以总结、引导、辅助跳转。
- 深度简历诊断、系统职业规划、模拟面试仍由对应页面承担。
- ChatDock 的历史归档不能混淆三大功能页的正式结果。

## D006 TTS 先做手动朗读

状态：已裁决

决策：

- TTS 初期只做手动朗读。
- 不做默认自动朗读。

影响：

- 页面不得默认播放 AI 回复。
- 朗读按钮、加载态、失败提示必须可控。
- 不引入强侵入式音频状态。

## D007 RAG / 文件上传主入口冻结

状态：已裁决（2026-05-29 修正）

决策：

- RAG / 文件上传主入口冻结，不作为当前用户可见主功能承诺。
- 旧坏入口必须禁用或返回 410。
- 后端 `/api/kb/*` 可作为 JWT 保护的实验性接口保留，但前端不得主动暴露为主功能入口。
- `KnowledgeBase` 当前定位为文档工作台，不接 RAG。
- 后续是否恢复"文档加入个人知识库 / ChatDock 引用文档"需要重新立项。

影响：

- 旧 `/api/knowledge/upload` 已返回 410 Gone。
- 前端 `ChatComposer.vue` 附件按钮已禁用（disabled）。
- Dashboard 不再触发 `KnowledgePanel` 悬浮面板。
- `KnowledgePanel.vue` 和 `kbService.js` 保留以便后续复用，但无用户入口激活。
- `/api/kb/upload`、`/api/kb/list`、`/api/kb/source` 作为 JWT 保护的实验性后端保留。
- 不把 ChatDock 或主流程强绑定到上传知识库。

## D008 主题系统只迁移品牌装饰色

状态：已裁决

决策：

- 主题系统只迁移品牌装饰色。
- 不迁移语义色。

影响：

- 不改成功、警告、错误、信息等语义色逻辑。
- 品牌色只影响装饰、强调、边框、辉光等视觉表达。

## D009 Provider / 当前用户资料 / 历史记录边界清楚

状态：已裁决

决策：

- Provider 选择、当前用户资料、历史记录必须分离。
- 不允许一个 store 或 payload 同时承担三类职责。

影响：

- Provider 只处理模型供应商、模型 ID、显示名、可用性。
- 当前用户资料只处理最新画像、目标岗位、简历相关当前状态。
- 历史记录只处理归档、恢复上下文、查看与对比。

## D010 当前用户资料以 userStore 最新值为准

状态：已裁决

决策：

- 当前用户资料以 `userStore` 最新值为准。
- 历史记录不能反向污染当前资料。

影响：

- 从历史记录恢复会话时，只能恢复会话上下文或展示历史快照。
- 若需要将历史资料应用为当前资料，必须由用户显式确认。
- 任何自动覆盖姓名、目标岗位、简历、雷达图、画像的行为都应视为高风险。

## D011 小步提交，避免大改

状态：已裁决

决策：

- 每轮任务保持小范围、可审计、可回滚。
- Agent 不得自动 `git add`、`git commit`。
- 提交动作必须由用户明确触发。

影响：

- 任务报告必须说明变更文件。
- 新增未跟踪文件必须提示。
- 大型重构必须拆阶段。

## D012 Vibe Coding Tool Pool 与可替换执行器

状态：已裁决（2026-06-06 修正，覆盖原 D012）

决策：

- Codex / OpenCode / Trae / Kiro / Antigravity / Cursor / Qoder / WorkBuddy / Claude Code / 未来新工具，统一视为可替换 Vibe Coding Tools，没有永久固定职责。
- 每轮角色由任务提示词临时指定（Implementer / Auditor / Reviewer / Memory Maintainer / Rule Maintainer 等）。
- 工具名不决定角色，任务模式决定角色。
- OpenCode 当前常用于 Memory Maintainer / Rule Maintainer，但不是永久固定岗位，不是 Hermes 本体，也不是默认业务开发主力。

影响：

- 任何 Vibe Coding Tool 都禁止自动 git add / commit。
- 任何 Vibe Coding Tool 都禁止 npm install / npm run build。
- 任何 Vibe Coding Tool 都禁止修改 Provider / History / ChatDock / TTS / RAG / DB / Auth，除非任务明确要求。
- 固定角色只有 Hermes（Project Steward）和 CCSwitch（Provider 路由 / 配置管理中枢）。

冲突裁决：

- 覆盖原 D012 中"OpenCode 是本地 Harness Runner"的固定岗位表述。

