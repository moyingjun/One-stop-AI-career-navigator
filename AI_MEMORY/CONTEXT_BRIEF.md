# Context Brief

这是给下一位 Agent 的短上下文。开始任何任务前，先读 `AGENTS.md`、`DECISIONS.md`、`PROJECT_MAP.md` 和本文件。

## 项目一句话

AI Career Navigator 是一个 Vue / FastAPI 的 AI 职业生涯导航平台，主线是 Dashboard、ChatDock、简历诊断、职业规划、模拟面试、文档工作台、Resume Builder Beta、TTS 手动朗读、多模型切换和历史记录归档。

## 当前最重要决策

- PostgreSQL 是主数据库，SQLite 不再作为主数据库扩展。
- RAG 使用云端 embedding，不走本地 embedding 主方案。
- 阿瓦隆只保留实验性隔离规范，不进主线。
- Resume Builder 只是 Beta 辅助功能。
- ChatDock 是 Dashboard AI 助手，不替代三大主功能页。
- TTS 只做手动朗读。
- RAG / 文件上传入口冻结。
- 主题只迁移品牌装饰色，不迁移语义色。
- Provider、当前用户资料、历史记录必须解耦。
- 当前用户资料以 `userStore` 最新值为准，历史记录不能自动覆盖它。
- 小步提交，Agent 不自动 git add / commit。

## 默认禁止

- 不运行 `npm install`。
- 不运行 `pip install`。
- 不运行 `npm run build`。
- 不自动 `git add` / `git commit`。
- 不修改 `.env`。
- 不删除文件。
- 未明确要求时，不改 Provider / History / ChatDock / TTS / RAG / DB / Auth。

## 当前文档冲突

旧 steering 中的 SQLite、本地 embedding、阿瓦隆主线推进、RAG 上传主流程描述已经过期。以后按 `DECISIONS.md` 处理。

## 当前待确认

实际代码里同时存在 PostgreSQL history、legacy SQLite、`history.db`、embedding client、ChatDock、TTS、Resume Builder、Avalon 前端组件。它们的完成度和运行路径没有在本轮验证，不能写成已闭环。

## 交付偏好

每轮结束要清楚说明：

- 改了哪些文件。
- 哪些只是文档约束。
- 哪些已验证，哪些未验证。
- 待用户确认事项。
- 建议下一步。

