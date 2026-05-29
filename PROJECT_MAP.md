# Project Map

本文件是 AI Career Navigator 的可交接项目地图。它合并了 `.kiro/steering` 中的长期结构说明、本次只读文件清单，以及当前已裁决的产品边界。

更新时间：2026-05-29

## 产品定位

AI Career Navigator 是一个全栈 AI 职业生涯导航平台，面向求职者、学生和跨行转职者，核心体验是用 AI 辅助简历、职业规划、面试训练和职业资料沉淀。

当前主线功能：

- Dashboard：主工作台与 AI 辅助入口。
- ChatDock：Dashboard AI 助手，负责轻量问答和上下文辅助。
- 简历诊断：独立主功能页。
- 职业规划：独立主功能页。
- 模拟面试：独立主功能页。
- 文档工作台：文档解析、展示与辅助处理。
- Resume Builder Beta：辅助功能，保持 Beta 范围。
- TTS 手动朗读：用户手动触发，不默认自动朗读。
- 多模型切换：Provider 选择必须与用户资料、历史记录解耦。
- 历史记录归档：保存、查看、恢复历史上下文，但不反向污染当前用户资料。

冻结或后置功能：

- RAG / 文件上传入口冻结，暂不接知识库主流程。
- 阿瓦隆 / 职场情商对抗模拟器只保留实验性隔离模块规范，当前不进入主线开发。
- Resume Builder 不继续深挖高级模板或 AI 美工。
- 主题系统只迁移品牌装饰色，不迁移语义色。

## 根目录

关键根目录文件：

- `main.py`：FastAPI 应用入口与路由注册。
- `database.py`：数据库兼容入口，具体实现以当前数据库层为准。
- `requirements.txt`：Python 依赖清单，Agent 默认不得修改。
- `.env`：本地环境变量，Agent 不得读取、打印或修改敏感值。
- `history.db`：旧 SQLite 文件存在于仓库工作区，但 PostgreSQL 已裁决为主数据库；是否仍被运行时依赖需要确认。
- `project_tree.txt`：项目树快照。
- `workflow.json`：工作流配置文件，除非任务明确要求，否则不修改。

新增 Harness 文档：

- `AGENTS.md`：所有 Agent 的总规则入口。
- `PROJECT_MAP.md`：项目结构与边界地图。
- `DECISIONS.md`：已裁决架构与产品决策。
- `CHECKLISTS.md`：任务前后检查清单。
- `WORKFLOW.md`：跨工具协作流程。
- `MODEL_ROLES.md`：不同 Agent / 模型的职责分工。
- `OPENCODE_USAGE.md`：OpenCode 使用边界。
- `HERMES_STEWARD.md`：Hermes Project Steward 长期项目管家定义。
- `TASK_TEMPLATES.md`：可复制的日常任务模板。
- `AI_MEMORY/`：短期记忆、交接摘要、任务日志和技能注册。

## 后端地图

主要技术栈：

- FastAPI / Uvicorn。
- PostgreSQL 作为主数据库。
- LLM Provider 统一封装。
- TTS SDK 与手动朗读流程。
- History 持久化。
- RAG 当前冻结主流程，embedding 决策为云端 embedding。

主要目录：

- `Settings/`：全局配置读取入口。
- `Router/`：HTTP 路由层。
- `Router/models/`：Pydantic 请求 / 响应模型。
- `Service/`：业务服务层。
- `Service/Agents/`：Agent、Prompt、LLM 角色层。
- `Service/Agents/prompts/`：Prompt 模板。
- `Service/Services/`：复杂业务服务，如 RAG。
- `Service/Utils/`：LLM、Embedding、TTS、OCR、PDF、SSE、数据库等工具层。
- `Service/Utils/databases/db/`：数据库访问实现；当前文件清单中存在 `pg_history_db.py` 与 `legacy_sqlite_history_db.py`。
- `tests/`：后端和属性测试。

后端重点边界：

- Router 不写业务逻辑。
- Service 不直接散落操作 HTTP 细节。
- Agent 不绕过统一 LLM Provider。
- History 使用 PostgreSQL 主路径；旧 SQLite 只能作为兼容或迁移参考，不能继续扩展为主方案。
- RAG 不使用本地 embedding 作为主方案。
- TTS 只做手动触发朗读。

## 前端地图

主要技术栈：

- Vue / Vite / Pinia。
- Tailwind 暗黑赛博 UI。
- ECharts / vue-echarts。
- lucide 图标体系。
- 原生 fetch / axios，SSE 流式请求。

主要目录：

- `frontend/src/`：页面级 Vue SFC。
- `frontend/src/components/`：可复用 UI 组件。
- `frontend/src/components/chat/`：ChatDock、ChatComposer、ChatMessageList。
- `frontend/src/components/Games/Avalon/`：实验性游戏相关前端组件；当前不进入主线开发。
- `frontend/src/stores/`：Pinia 状态。
- `frontend/src/services/`：前端 API 客户端。
- `frontend/src/utils/`：前端工具。
- `frontend/src/__tests__/`、`frontend/src/components/__tests__/`、`frontend/src/services/__tests__/`：前端测试与检查。

前端重点边界：

- `userStore` 是当前用户资料最新值来源。
- `llmProviderStore` 只处理 Provider / 模型选择。
- `chatSessionStore` 只处理会话上下文与归档辅助。
- `resumeBuilderStore` 只服务 Resume Builder Beta。
- 历史记录不能自动覆盖 `userStore` 当前资料。
- ChatDock 不替代简历诊断、职业规划、模拟面试三大主功能页。

## 文档来源

已读取 steering 文件：

- `.kiro/steering/product.md`
- `.kiro/steering/structure.md`
- `.kiro/steering/tech.md`
- `.kiro/steering/delivery-report.md`

本文件对 steering 的继承原则：

- 保留产品定位、四层架构、交付报告、暗黑赛博 UI、Prompt 解耦、SSE 统一等不冲突规则。
- 覆盖 SQLite 主库、本地 embedding、阿瓦隆主线开发等已过期描述。
- 对代码实际状态与文档不一致处，不做主观判断，统一放入 `AI_MEMORY/CURRENT_STATE.md` 待确认。

## 当前观察到的潜在不一致

- steering 中写 SQLite 为数据库，但当前决策要求 PostgreSQL 为主数据库；文件清单中同时存在旧 SQLite 文件与 PostgreSQL history 实现。
- steering 中写 RAG 使用 HuggingFace 本地 embedding，但当前决策要求云端 embedding。
- steering 中详细展开阿瓦隆模块，但当前决策要求仅保留实验性隔离规范，不进入主线。
- steering 中提到知识库上传主流程，但当前决策要求 RAG / 文件上传入口冻结。
- 实际文件清单显示 ChatDock、TTS、Resume Builder Beta、Provider Store 已出现；具体完成度需要按任务单独验证。

