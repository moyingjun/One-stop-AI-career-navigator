# Current State

更新时间：2026-05-29（开发收工记录）

本文件记录当前 Agent Harness 视角下的项目状态。它不是业务代码真相源；若与实际代码冲突，以只读检查和后续验证为准，并把冲突放入“待确认事项”。

## 当前任务状态

本轮任务：Hermes Project Steward v0.1 阶段收工记录。

本轮范围：

- 只修改 AI_MEMORY 文件。
- 不修改业务代码。
- 不运行依赖安装。
- 不运行构建。
- 不执行 git add / commit。

## 已读取来源

- `.kiro/steering/product.md`
- `.kiro/steering/structure.md`
- `.kiro/steering/tech.md`
- `.kiro/steering/delivery-report.md`
- 只读文件清单。

## 当前已裁决事实

- PostgreSQL 是主数据库。
- SQLite 不作为主数据库继续扩展。
- RAG 使用云端 embedding，不使用本地 embedding 作为主方案。
- 阿瓦隆 / 职场情商对抗模拟器只保留实验性隔离模块规范，当前不进入主线开发。
- Resume Builder 是 Beta 辅助功能。
- ChatDock 是 Dashboard AI 助手，不替代三大主功能页。
- TTS 先做手动朗读。
- RAG / 文件上传主入口冻结，不作为当前用户可见主功能承诺。
- 主题系统只迁移品牌装饰色。
- Provider / 当前用户资料 / 历史记录必须边界清楚。
- 当前用户资料以 `userStore` 最新值为准，历史记录不能反向污染当前资料。
- 小步提交，Agent 不自动 git add / commit。

## 只读观察到的代码线索

文件清单显示：

- 后端存在 `Service/Utils/databases/db/pg_history_db.py`。
- 后端存在 `Service/Utils/databases/db/legacy_sqlite_history_db.py`。
- 工作区根目录存在 `history.db`。
- 前端存在 `frontend/src/components/chat/ChatDock.vue`。
- 前端存在 `frontend/src/stores/chatSessionStore.js`。
- 前端存在 `frontend/src/stores/llmProviderStore.js`。
- 前端存在 `frontend/src/stores/resumeBuilderStore.js`。
- 前端存在 `frontend/src/components/TTSButton.vue`。
- 后端存在 `Router/tts.py` 与 `Service/tts_service.py`。
- 后端存在 `Service/Utils/embedding_client.py`。
- 后端存在 `Service/Utils/celery_app.py`。
- 前端存在 `frontend/src/components/Games/Avalon/GameLobbyModal.vue`。

这些只代表文件存在，不代表功能已完成或运行路径已验证。

## 工作区状态提醒

本轮写入 Markdown 后，`git status --short` 显示工作区除本轮新增 Harness 文档外，还有多项业务代码 modified / untracked 文件，例如 `Settings/config.py`、`main.py`、多处 `frontend/src/*`、TTS 相关文件等。

这些业务代码改动不是本轮 Markdown 规则任务产生的，本轮未修改它们。下一位 Agent 在处理 git 状态时，应先区分“本轮 Harness 文档新增”和“历史遗留或用户已有业务改动”，不要回滚用户改动。

## 已裁决的文档冲突

- `.kiro/steering/tech.md` 写 SQLite 主库；当前裁决为 PostgreSQL 主库。
- `.kiro/steering/tech.md` 写 HuggingFace 本地 embedding；当前裁决为云端 embedding。
- `.kiro/steering/product.md`、`structure.md`、`tech.md` 详细推进阿瓦隆；当前裁决为实验性隔离规范，不进入主线。
- `.kiro/steering` 中知识库 / RAG 上传主流程描述与当前 D007 冲突；以 D007 修正版为准。
- `.kiro/steering/tech.md` 中允许 npm install / pip install 的常用命令说明，不适用于 OpenCode 第一阶段和当前 Harness 默认规则。

## 旧 CTO 审计结论（2026-05-29）

- Harness 第一阶段方向被认可。
- OpenCode 继续作为低风险本地 Harness Runner / AI_MEMORY 管家。
- 暂不允许 OpenCode 修改高风险业务代码。
- PostgreSQL 主路径判断可信。
- SQLite 测试路径列为 P1 风险。
- `history.db` / 旧 steering SQLite 描述列为 P2 风险。
- 下一步：只读核对 RAG embedding 路径。

## 已确认事项（数据库路径核对）

- 已确认：当前主运行路径使用 PostgreSQL。证据包括 `Service/Utils/databases/db/pg_history_db.py`、`Service/Utils/databases/models/`、`Service/Settings/config.py`、`database.py`、`main.py`、`Router/history_router.py`、`Service/Services/rag_service.py`。
- 部分确认：`legacy_sqlite_history_db.py` 疑似仅为遗留兼容；`db/__init__.py` 注释说明旧 SQLite 实现不再被主路径 import。但仍建议后续只读搜索全仓库是否存在直接 import。

## 已确认事项（RAG embedding 路径核对）

- 已确认：当前 RAG embedding 主路径使用云端 API。证据包括 `Service/Utils/embedding_client.py`（使用 httpx 调用外部 API）、`Service/Settings/config.py`（EMBEDDING_API_URL 默认值为 `https://tokenrai.com/v1`）。
- 已确认：`embedding_client.py` 和 `rag_service.py` 均明确禁止引入 torch、sentence-transformers 等重型 ML 库。
- 已确认：`requirements.txt` 中不存在 sentence-transformers、transformers、torch 依赖。
- 已确认：旧 `/api/knowledge/upload` 端点已返回 410 Gone，强制使用新 `/api/kb/upload`（需登录）。
- 发现残留：`Settings/config.py` 中存在 `RAG_EMBEDDING_MODEL` 配置（默认值为 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`），但该配置未被 `embedding_client.py` 使用，疑似历史残留。

## 已确认事项（RAG / 文件上传入口暴露面核对）

- 已确认：旧 `/api/knowledge/upload` 端点返回 410 Gone（`rag_service.py:486`）。
- 已确认：新 `/api/kb/upload` 端点需 JWT 登录（`knowledge_base.py:54`），后端仍可用。
- 已确认：前端 `ChatComposer.vue` 附件按钮已禁用（disabled），显示"文档引用功能稍后开放"。
- 已确认：Dashboard 中 `showKnowledgePanel` 不再被任何按钮触发（`Dashboard.vue:879` 注释说明）。
- 已确认：`KnowledgePanel.vue` 组件仍存在，但未被用户可点击的入口激活。
- 已确认：`KnowledgeBase.vue` 是文档工作台（纯本地 localStorage），不调用 /api/*。
- 发现残留：`KnowledgePanel.vue`、`kbService.js` 仍存在，`/api/kb/upload` 后端仍暴露。

## 已确认事项（ChatDock / History / userStore / Provider 边界核对）

- 已确认：ChatDock / History / userStore / Provider 边界符合 D009 / D010。
- 证据：
  - `Dashboard.restoreChatContext()` 只调用 `chatStore.restoreFromHistory()`，不修改 userStore。
  - `chatSessionStore.restoreFromHistory()` 只更新 messages、currentSessionId、archivedRecordId、isDirty。
  - `userStore.updateUserProfile()` 未被 history 恢复逻辑调用。
  - `llmProviderStore` 只管理 Provider，不直接写 userStore / history。
  - ChatDock 归档 record_type = `dashboard_chat`，与三功能页记录类型分离。
- 未发现 History 反向污染 userStore。
- 未发现 Provider / History / User Profile 混用。
- 未发现 ChatDock 越权替代三大功能页。

## 已确认事项（TTS 手动朗读核对）

- 已确认：TTS 保持手动朗读，符合 D006 决策。
- 证据：
  - `TTSButton.vue` 中 `handleClick()` 只由 `@click` 触发，没有自动触发逻辑。
  - `ttsClient.synthesizeAudio()` 只在用户点击后的 `fetchOrCacheBlob()` 路径中调用。
  - `ChatMessageList.vue` 在流式输出中通过 `isLastStreamingAI()` 禁用 TTSButton。
  - 搜索 `autoplay`、`autoPlay`、`auto.*speak`、`auto.*read` 未发现 TTS 相关自动播放逻辑。
  - 搜索 `onMounted.*TTS`、`onComplete.*TTS`、`finish.*speak`、`response.*play` 未发现每条 AI 回复自动请求 TTS。
- 未发现默认自动播放。
- 未发现流式 chunk 自动朗读。
- 未发现每条 AI 回复自动请求 TTS。

## 待确认事项

- `pg_history_db.py` 的连接配置、表结构、用户隔离是否已验证。
- `Settings/config.py` 中 `RAG_EMBEDDING_MODEL` 配置是否应清理（当前未被使用）。
- Resume Builder Beta 是否存在继续扩张高级模板或 AI 美工的未裁决需求。
- 前端 Avalon 组件是否仅为残留或实验入口，是否需要隐藏 / 标记实验。
- `Service/Utils/celery_app.py` 是否仍被主流程使用；若用于低配服务器任务，需要评估资源风险。
- 测试文件仍使用 SQLite，可能无法覆盖 PostgreSQL async session、SQLAlchemy 2.0、asyncpg、事务与 JSON 字段差异。
- 根目录 `history.db` 疑似残留文件，后续需要确认是否应加入清理计划或标记为 legacy artifact。
- `.kiro/steering/tech.md` 中 SQLite 主库描述已过期，后续可以选择更新 steering 或在 `SKILL_REGISTRY.md` 标记过期。

## 风险记录

- P1：测试环境仍使用 SQLite，而生产主路径为 PostgreSQL。
- P2：`history.db` 残留可能误导后续 Agent。
- P2：旧 steering 文档仍写 SQLite，可能误导后续 Agent。
- P2：`Settings/config.py` 中 `RAG_EMBEDDING_MODEL` 配置为本地模型名称，但实际未使用，疑似历史残留。

## 工具治理状态

- `HERMES_TOOL_POLICY.md` 已建立。
- Hermes / OpenCode / Codex / Claude Code / CCSwitch 的工具分层已明确。
- Hermes 当前只允许低风险 Skills / MCP 边界，暂不授予数据库写入、全盘文件写入、GitHub push/merge/release、Secrets、SSH 高权限等能力。
- Hermes 已成功接入 MiMo，但不强行走 CCSwitch local router。

## Hermes Steward v0.1 阶段收口（2026-05-29）

**阶段状态：**

- Agent Harness v1.2：稳定。规则、记忆、模板、检查清单和执行边界已建立。
- Hermes Project Steward v0.1：定版。开始孵化，由用户人工触发。
- OpenCode：本地项目管家控制台 / Harness Caretaker。

**已确认事实：**

1. PostgreSQL 主路径：当前主运行路径使用 PostgreSQL，legacy_sqlite_history_db.py 疑似仅为遗留兼容。
2. RAG 云端 embedding：embedding_client.py 使用 httpx 调用外部 API，requirements.txt 中无重型 ML 依赖。
3. ChatDock / History / userStore / Provider 边界：符合 D009 / D010，未发现反向污染或越权。
4. TTS 手动朗读：符合 D006，未发现自动播放或流式 chunk 自动朗读。

**后续可回到业务开发任务，但所有工具仍需先读 AGENTS.md / DECISIONS.md / PROJECT_MAP.md / AI_MEMORY/CONTEXT_BRIEF.md。**

## 开发收工记录（2026-05-29）

**已完成事项：**

1. Agent Harness v1.2 已落地：规则、记忆、模板、检查清单和执行边界已建立。
2. Hermes Project Steward v0.1 已定版：长期项目管家型 Agent 形态开始孵化。
3. OpenCode 定位为 Harness Caretaker / Memory Steward：偏向项目记忆与规则管护，不作为默认业务开发主力。
4. TTS 手动朗读 Beta 完成：TTSButton.vue、ttsClient.js、Router/tts.py、Service/tts_service.py 已实现。
5. TTSButton Polish v1 完成：暗黑赛博风格、单例 Audio、Blob 缓存、streaming 中禁用。
6. Dashboard 下一步行动 + Layout Polish 完成：actionSuggestions.js、Bento 栏优化。
7. PremiumInterview Voice Input MVP 审计完成：接入点、状态管理、冲突分析已完成。

**当前禁止继续扩展：**

- 不做全局自动朗读（D006 决策：TTS 先做手动朗读）。
- 不做自动发送（避免误发送和隐私问题）。
- 不做 RAG 主流程（D007 决策：RAG/文件上传主入口冻结）。
- 不做大规模业务重构（D011 决策：小步提交，避免大改）。

**下一步候选：**

- 模拟面试评分解释增强。
- 职业规划导出增强。
- Dashboard 第二轮体验优化。
- Voice Mode 语音输入实现（需用户明确授权）。

## PremiumInterview Feedback Coach v1 收工（2026-05-29）

**已完成：**

- 模拟面试结束评估已增强。
- 新增六维评分解释（`*_explanation` 字段）。
- 新增 3 条下一轮改进动作（`improvement_suggestions` 数组）。
- 保留 `radarScores` 数字结构不变。
- 旧历史记录缺失 explanation/suggestions 时降级隐藏，不报错。

**未做：**

- 未做扣分原因数组。
- 未做参考回答。
- 未做总分。
- 未改 `record_type`（仍为 `interview_session`）。
- 未改 History 主路径。
- 未改 Provider。
- 未改 TTS。
- 未改 VoiceInput。

**涉及文件：**

- `Service/Agents/prompts/interview_prompts.py`：Prompt 新增 explanation + improvement_suggestions。
- `Service/Agents/interview_agent.py`：解析、clamp、兜底、写入 history。
- `frontend/src/PremiumInterview.vue`：结果弹窗新增维度解释和改进建议展示。
