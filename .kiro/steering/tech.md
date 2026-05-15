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
