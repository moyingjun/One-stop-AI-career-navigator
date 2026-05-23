# 技术栈与构建系统

## 后端 (Python)

- **框架**：FastAPI（配合 Uvicorn ASGI 服务器）
- **LLM 提供商**：DeepSeek API（模型：deepseek-v4-flash），通过 `Service/Utils/llm_client.py` 统一封装，使用 httpx 进行流式调用
- **数据库**：SQLite（文件：`history.db`），使用原生 `sqlite3` 模块（无 ORM），CRUD 实现在 `Service/Utils/databases/db/history_db.py`
- **RAG**：自定义实现，位于 `Service/Services/rag_service.py`，支持向量检索（HuggingFace Embeddings）和关键词降级检索
- **OCR**：RapidOCR（本地推理，无需云服务）
- **PDF 解析**：PyMuPDF（优先）→ pdfminer.six（降级），封装在 `Service/Utils/pdf_parser.py`
- **鉴权**：JWT（python-jose），bcrypt 密码哈希（passlib），7天有效期
- **环境配置**：python-dotenv，统一在 `Settings/config.py` 读取
- **数据校验**：Pydantic v2，模型定义在 `Router/models/`

## 前端 (Vue 3 + Vite)

- **框架**：Vue 3（Composition API，严格使用 `<script setup>` 语法糖）
- **构建工具**：Vite 8
- **状态管理**：Pinia（Composition 风格）
- **路由**：Vue Router 5（History 模式）
- **样式**：Tailwind CSS 4（通过 PostCSS 插件集成）
- **图表**：ECharts 6 + vue-echarts（雷达图、数据可视化）
- **3D 特效**：Three.js + Vanta.js（落地页背景）
- **HTTP 客户端**：axios + 原生 fetch（SSE 流式请求使用原生 fetch）
- **UI 图标**：lucide-vue-next
- **工具库**：@vueuse/core、@formkit/auto-animate
- **文档解析（客户端）**：mammoth（DOCX）、pdfjs-dist（PDF）
- **Markdown 渲染**：marked

## 常用命令

```bash
# 后端
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 前端（需切换至 /frontend 目录执行）
npm install
npm run dev      # 启动开发服务器，访问 http://127.0.0.1:5173
npm run build    # 构建生产环境代码至 /frontend/dist 目录
npm run preview  # 预览生产环境构建结果
```

## 环境变量（`.env`）

- `DEEPSEEK_API_KEY` — LLM API 密钥
- `DEEPSEEK_BASE_URL` — LLM 端点 URL（默认：`https://tokenrai.com/v1/chat/completions`）
- `DEEPSEEK_MODEL_NAME` — 模型标识符（默认：`deepseek-v4-flash`）
- `JWT_SECRET_KEY` — JWT 签名密钥（至少 32 字符，必填）
- `RAG_EMBEDDING_MODEL` — Embedding 模型路径（默认：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`）
- `RAG_EMBEDDING_DEVICE` — 推理设备（默认：`cpu`）
- `RAG_CHUNK_SIZE` — RAG 分块大小（默认：`800`）
- `RAG_CHUNK_OVERLAP` — RAG 分块重叠（默认：`120`）
- `RAG_MAX_UPLOAD_MB` — 知识库上传文件大小限制（默认：`20`）

## API 通信

- 前端开发服务器通过 Vite 代理将 `/api` 路径转发至 `http://127.0.0.1:8000`
- 流式响应采用 Server-Sent Events (SSE) 协议，全项目统一事件格式（通过 `Service/Utils/sse_utils.py` 生成）：
  - `event: meta` — 元信息（Agent 类型、知识库状态等）
  - `event: reply` — 正常内容片段（流式输出）
  - `event: warning` — 非致命警告（如 RAG 降级）
  - `event: error` — 错误信息
  - `event: done` — 流结束标志（始终发送，携带 `record_id`）
- 非流式接口返回标准 JSON 格式数据

## AI 安全与执行规范（重要）

禁止运行以下命令，以防止系统卡死或内存溢出：
- **禁止**：`vue-tsc`、`tsc`（类型检查）
- **禁止**：`vite build`、`npm run build`（生产构建，除非用户明确要求）
- 遇到类型错误时，直接修改代码，不运行类型检查命令

允许运行的安全命令：
- 后端启动：`uvicorn main:app --reload --port 8000`
- 前端启动：`npm run dev`
- 包管理：`npm install/uninstall <pkg>`、`pip install -r requirements.txt`
- 格式化：`black .`、`prettier --write .`、`npm run lint`

---

## 阿瓦隆游戏引擎专项技术规范

### 存储架构：动静分离

游戏状态存储严格遵循"热数据 Redis、冷数据 PostgreSQL"原则：

| 数据类型 | 存储介质 | 数据结构 | 说明 |
|---|---|---|---|
| 房间实时状态（Room State） | Redis | Hash（`room:{room_id}`） | 玩家列表、当前回合、角色分配、任务结果等动态字段 |
| 玩家动作队列 | Redis | List（`room:{room_id}:actions`） | 按时序入队，speaking_token 调度器消费 |
| 房间 TTL | Redis | Key 过期（默认 2 小时） | 无人房间自动清理，防止 Redis 内存泄漏 |
| 对局摘要（Game History） | PostgreSQL | `game_history` 表 | 仅在游戏正常结束时异步落库，不阻塞游戏流程 |

**禁止**将游戏房间状态写入 SQLite `history.db`（该库专属于对话历史，不得混用）。

### WebSocket 通信协议标准

前后端所有 WebSocket 消息必须遵循统一 JSON 信封格式：

```json
{
  "type": "EVENT_NAME",
  "payload": {},
  "timestamp": 1716000000000
}
```

**事件类型常量清单（强制使用，禁止魔法字符串）**：

| 方向 | type 常量 | 说明 |
|---|---|---|
| S→C | `SYNC_STATE` | 断线重连后下发完整房间快照 |
| S→C | `PLAYER_SPEECH` | AI 玩家公开发言（已剥离 scratchpad） |
| S→C | `VOTE_RESULT` | 投票结果广播 |
| S→C | `MISSION_RESULT` | 任务成功/失败结果 |
| S→C | `GAME_OVER` | 游戏结束，携带胜负方及角色揭示 |
| S→C | `WATCHDOG_TIMEOUT` | 通知客户端某 AI 超时，已强制交出麦克风 |
| C→S | `PLAYER_ACTION` | 人类玩家动作（投票、选人等） |
| C→S | `RECONNECT` | 携带 JWT，请求重连并同步状态 |

### AI 动作抽象契约（Pydantic Contract）

所有游戏 AI Agent 的 LLM 返回结果必须强制解析为 `AIAvalonResponse` 模型（定义在 `Service/Games/Avalon/models/avalon_models.py`）：

```
AIAvalonResponse:
  scratchpad: str      # 思维链暗牌（内心草稿，绝对禁止广播至前端）
  speech:     str      # 公开言论（广播给所有玩家）
  action:     str      # 动作常量（枚举值，如 VOTE_APPROVE / VOTE_REJECT / NOMINATE）
  target:     str | None  # 动作目标（玩家 ID 或 None）
```

- 若 LLM 返回无法解析为此模型，watchdog 必须捕获异常并生成兜底动作，不得抛出至游戏主循环
- `scratchpad` 字段在任何情况下都不得出现在 WebSocket 广播消息中（见"防作弊载荷清洗"）

### 多 Agent 麦克风令牌（Speaking Token）

- `speaking_token.py` 维护一个基于 Redis List 的全局发言队列，每个房间独立一条队列
- 同一时刻只有持有令牌的 Agent 可以调用 LLM，其余 Agent 必须等待入队
- 令牌持有超时（默认 15 秒）后由 watchdog 强制回收，防止单个 API 卡死全房间
- **禁止**在游戏交互环中使用 `asyncio.gather` 并发调用多个 AI 的 LLM 接口

### 核心防线与灾难恢复

**1. 防作弊载荷清洗（Payload Stripping）**
- 网关层（`Router/game_avalon.py`）在向前端广播任何 WebSocket 消息前，必须硬性剔除 `AIAvalonResponse.scratchpad` 字段
- 此操作在路由层执行，不依赖 Agent 层的自觉性，作为最后一道防线
- 禁止将 `scratchpad` 写入 Redis 广播队列，只允许写入 `god_mode_logger.py` 的调试日志

**2. 幽灵卡麦防线（Watchdog）**
- `watchdog.py` 使用 `asyncio.wait_for` 对每次 LLM 调用设置强制超时（默认 15 秒，可通过 `AVALON_AI_TIMEOUT_SEC` 环境变量配置）
- 超时后自动生成兜底动作（随机合法动作 + 固定兜底发言），强制交出麦克风令牌
- 向房间内所有客户端广播 `WATCHDOG_TIMEOUT` 事件，前端展示"AI 思考超时"提示

**3. 断线快照重载**
- 玩家重连时携带 JWT，后端验证身份后从 Redis 读取 `room:{room_id}` Hash 的完整快照
- 立即下发 `SYNC_STATE` 事件，payload 包含：当前回合、剩余倒计时、所有公开信息、本人角色
- 重连恢复延迟目标：< 500ms（Redis 读取 + WebSocket 推送）

**4. 上下文滑动窗口（Context Window 管控）**
- **严禁**将全量对局历史日志直接投喂给 AI，防止 Token 爆炸
- 每个 AI Agent 的上下文构成：系统 Prompt（角色设定）+ 最近 N 轮摘要（默认 N=5）+ 当前回合完整信息
- 每轮结束后，`avalon_service.py` 必须异步生成本轮摘要并写入 Redis，替换原始日志
- `N` 值通过 `AVALON_CONTEXT_WINDOW` 环境变量配置，默认 5

**5. 资源红线（2C4G 服务器约束）**
- 游戏 AI 调用必须使用纯 `asyncio` + `httpx.AsyncClient`，与主站 LLM 调用共享同一客户端实例
- **禁止**在游戏核心交互环中引入 Celery、线程池或任何阻塞式任务队列
- 单房间最大 AI 玩家数：6（防止单局游戏占用过多并发 LLM 配额）
- Redis 连接池大小上限：10（通过 `REDIS_MAX_CONNECTIONS` 环境变量配置）

### 新增环境变量（`.env`）

- `REDIS_URL` — Redis 连接地址（默认：`redis://127.0.0.1:6379/0`）
- `POSTGRES_URL` — PostgreSQL 连接字符串（游戏历史落库，可选）
- `AVALON_AI_TIMEOUT_SEC` — AI 单次调用超时秒数（默认：`15`）
- `AVALON_CONTEXT_WINDOW` — AI 上下文保留回合数（默认：`5`）
- `REDIS_MAX_CONNECTIONS` — Redis 连接池上限（默认：`10`）
- `DEBUG_MODE` — 上帝视角日志开关（`true`/`false`，生产环境必须为 `false`）
