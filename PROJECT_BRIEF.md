# Project Brief

给当前执行者的项目简报。开始任务前先读默认入口 5 件套：`PROJECT_BRIEF.md`、`AGENTS.md`、`DECISIONS.md`、`HERMES_TOOL_POLICY.md`、`AI_MEMORY/CURRENT_STATE.md`。`PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md` 等属于二级参考 / 按需读取。重要任务交付报告进入 `AI_MEMORY/INBOX/`，由 Hermes 主导消化，或由用户指定的 Vibe Coding Tool 辅助整理。

更新时间：2026-06-05

## 当前目标

AI Career Navigator 是 Vue / FastAPI 全栈 AI 职业生涯导航平台，面向求职者、学生和跨行转职者。

主线产品功能：

- Dashboard：主工作台与 AI 辅助入口。
- ChatDock：Dashboard AI 助手（轻量问答，不替代三大功能页）。
- 简历诊断：独立主功能页。
- 职业规划：独立主功能页。
- 模拟面试：独立主功能页（最新完成：PremiumInterview Feedback Coach v1，含六维评分解释与改进建议）。
- 文档工作台：文档解析与辅助处理。
- Resume Builder Beta：辅助功能，保持 Beta 范围。
- TTS 手动朗读：用户手动触发，不默认自动朗读。
- 多模型切换：Provider 与用户资料 / 历史记录解耦。
- 历史记录归档：查看、恢复上下文，不反向污染当前资料。

冻结 / 后置功能：

- RAG / 文件上传主入口冻结（后端 /api/kb/* 保留为 JWT 保护的实验性接口）。
- 阿瓦隆只保留实验性隔离模块规范，不进入主线开发。
- Resume Builder 不继续深挖高级模板或 AI 美工。
- 主题系统只迁移品牌装饰色，不迁移语义色。

元目标：建立 Agent Harness 体系（v1.2 已稳定），孵化 Hermes Project Steward 作为长期项目管家（v0.1 已定版）。

## 已确认决策

| 编号 | 决策 | 状态 |
|------|------|------|
| D001 | PostgreSQL 是主数据库；SQLite 不再作为主数据库扩展 | 已裁决，已核对 |
| D002 | RAG 使用云端 embedding；不使用本地 embedding 作为主方案 | 已裁决，已核对 |
| D003 | 阿瓦隆只保留实验性隔离模块规范，当前不进入主线开发 | 已裁决 |
| D004 | Resume Builder 保持 Beta 辅助功能，不深挖高级模板或 AI 美工 | 已裁决 |
| D005 | ChatDock 是 Dashboard AI 助手，不替代简历诊断、职业规划、模拟面试三大功能页 | 已裁决，已核对 |
| D006 | TTS 先做手动朗读，不做默认自动朗读 | 已裁决，已核对 |
| D007 | RAG / 文件上传主入口冻结；后端 /api/kb/* 保留为 JWT 保护的实验性接口 | 已裁决，已核对 |
| D008 | 主题系统只迁移品牌装饰色，不迁移语义色 | 已裁决 |
| D009 | Provider / 当前用户资料 / 历史记录必须边界清楚 | 已裁决，已核对 |
| D010 | 当前用户资料以 userStore 最新值为准，历史记录不能反向污染 | 已裁决，已核对 |
| D011 | 小步提交，避免大改；Agent 不得自动 git add / commit | 已裁决 |
| D012 | Vibe Coding Tool Pool 与可替换执行器；OpenCode 不是固定岗位 | 已裁决，已核对 |

## 已完成核对

以下事项已通过只读代码核对，有完整证据链：

1. **PostgreSQL 主路径**：主运行路径使用 PostgreSQL。证据包括 pg_history_db.py、database.py、main.py、Router/history_router.py。legacy_sqlite_history_db.py 疑似仅为遗留兼容，db/__init__.py 注释说明旧 SQLite 实现不再被主路径 import。

2. **RAG 云端 embedding**：embedding_client.py 使用 httpx 调用外部 API（默认 https://tokenrai.com/v1）。embedding_client.py 和 rag_service.py 均明确禁止 torch / sentence-transformers。requirements.txt 中无重型 ML 依赖。

3. **RAG / 文件上传入口冻结**：旧 /api/knowledge/upload 已返回 410 Gone。新 /api/kb/upload 需 JWT 登录。前端 ChatComposer.vue 附件按钮已禁用。Dashboard 中 showKnowledgePanel 不再被任何按钮触发。KnowledgePanel.vue 和 kbService.js 仍存在但无用户入口激活。

4. **ChatDock / History / userStore / Provider 边界**：符合 D009 / D010。Dashboard.restoreChatContext() 只调用 chatStore.restoreFromHistory()，不修改 userStore。llmProviderStore 只管理 Provider。ChatDock 归档 record_type = dashboard_chat，与三功能页记录类型分离。未发现 History 反向污染 userStore。

5. **TTS 手动朗读**：符合 D006。TTSButton.vue 中 handleClick() 只由 @click 触发。搜索 autoplay / autoPlay / auto.*speak 等未发现 TTS 自动播放逻辑。流式输出中通过 isLastStreamingAI() 禁用 TTSButton。

## 待确认事项

| 编号 | 事项 | 风险 |
|------|------|------|
| U001 | pg_history_db.py 的连接配置、表结构、用户隔离是否已完整验证 | 中 |
| U002 | Settings/config.py 中 RAG_EMBEDDING_MODEL 配置（默认值为 sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2）未被使用，疑似历史残留，是否应清理 | 低 |
| U003 | 前端 Avalon 组件（Games/Avalon/）是否仅为残留或实验入口，是否需要隐藏或标记实验 | 低 |
| U004 | celery_app.py 是否仍被主流程使用；若用于低配服务器任务，需要评估资源风险 | 中 |
| U005 | 测试文件仍使用 SQLite，可能无法覆盖 PostgreSQL async session、SQLAlchemy 2.0、asyncpg、事务与 JSON 字段差异 | 高 |
| U006 | 根目录 history.db 疑似残留文件，需确认是否应加入清理计划或标记为 legacy artifact | 低 |
| U007 | .kiro/steering/tech.md 中 SQLite 主库 / 本地 embedding 描述已过期，是否需要更新或标记过期 | 低 |

## 下一步优先级

按风险和产品价值排序：

1. **（P1 + 产品价值）模拟面试评分解释增强**：PremiumInterview Feedback Coach v1 已完成六维评分解释和改进建议。下一步可考虑扣分原因数组、参考回答、总分。需用户明确授权范围。

2. **（P1 风险修复）测试环境 PostgreSQL 对齐**：U005 是当前最高风险项。测试文件仍使用 SQLite，无法覆盖 PostgreSQL async session 差异。建议优先评估迁移测试环境的工作量。

3. **（产品价值）职业规划导出增强**：当前职业规划页结果导出能力有限，可增强 PDF / 分享链接导出。

4. **（产品价值）Dashboard 第二轮体验优化**：actionSuggestions.js 和 Bento 栏优化已完成第一轮，可进行第二轮体验打磨。

5. **（低风险清理）历史残留清理**：U002 RAG_EMBEDDING_MODEL 配置清理、U006 history.db 残留清理、U003 Avalon 组件标记。可合并为一次低风险清理任务。

6. **（待用户决策）Voice Mode 语音输入**：PremiumInterview Voice Input MVP 审计已完成，实现需用户明确授权。

---

本文件由 Hermes Agent 于 2026-06-05 生成，基于 AGENTS.md、DECISIONS.md、AI_MEMORY/CURRENT_STATE.md 的只读分析。未修改任何业务代码或其他文件。
