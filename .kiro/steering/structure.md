# 项目结构

```
/
├── main.py                          # FastAPI 应用入口点、中间件及路由注册
├── database.py                      # 向后兼容 re-export（实现已迁移至 Service/Utils/databases/）
├── requirements.txt                 # Python 依赖库列表
├── .env                             # 环境变量配置文件（API 密钥、模型配置等）
├── history.db                       # SQLite 数据库文件（自动生成）
│
├── Settings/                        # 全局配置层（唯一环境变量读取入口）
│   └── config.py                    # 统一读取所有 .env 变量，其他模块直接 import 常量
│
├── Router/                          # 路由层（仅处理 HTTP 协议层逻辑）
│   ├── agent_dispatcher.py          # 多智能体聊天接口，调用 Service/Agents/dispatcher_agent.py
│   ├── auth.py                      # 用户注册/登录，签发 JWT
│   ├── careerPlan.py                # 职业规划相关接口
│   ├── dependencies.py              # JWT 依赖注入（get_current_user / get_optional_user）
│   ├── history_router.py            # 历史记录 CRUD 接口（多租户隔离）
│   ├── interview.py                 # 模拟面试相关接口
│   ├── jobResume.py                 # 职位与简历上传接口（遗留）
│   ├── ocr.py                       # OCR 图片识别接口
│   ├── resumeDiagnosis.py           # 简历诊断相关接口
│   └── models/                      # Pydantic 请求/响应数据模型（仅存放 schemas）
│       ├── agent_model.py
│       ├── auth_model.py
│       ├── career_model.py
│       ├── history_model.py
│       ├── interview_model.py
│       ├── jobResume_model.py
│       └── resume_model.py
│
├── Service/                         # 业务层
│   ├── resume_service.py            # 简历诊断业务逻辑（调用 Agents/resume_agent.py）
│   ├── interview_service.py         # 模拟面试业务逻辑（调用 Agents/interview_agent.py）
│   ├── career_service.py            # 职业规划业务逻辑（调用 Agents/career_agent.py）
│   ├── rag_service.py               # 向后兼容 re-export（实现在 Services/rag_service.py）
│   │
│   ├── Agents/                      # Agent 定义层（角色 + Prompt + 调用规范）
│   │   ├── base_agent.py            # Agent 基类：统一流式/非流式 LLM 调用
│   │   ├── resume_agent.py          # 简历诊断 Agent
│   │   ├── interview_agent.py       # 面试对话 Agent + 评估 Agent
│   │   ├── career_agent.py          # 职业规划 Agent + 推荐问题 Agent
│   │   ├── dispatcher_agent.py      # 多专家路由 Agent（关键词路由 + RAG 注入）
│   │   └── prompts/                 # Prompt 模板层（与业务代码解耦）
│   │       ├── resume_prompts.py
│   │       ├── interview_prompts.py
│   │       ├── career_prompts.py
│   │       └── agent_prompts.py
│   │
│   ├── Services/                    # 复杂业务服务
│   │   └── rag_service.py           # RAG 真正实现：知识加载、向量嵌入、检索匹配
│   │
│   └── Utils/                       # 工具层（无业务含义的通用能力）
│       ├── llm_client.py            # DeepSeek 唯一调用入口（stream_chat / complete_chat）
│       ├── sse_utils.py             # SSE 格式化工具（统一全项目事件格式）
│       ├── pdf_parser.py            # PDF 文本提取（PyMuPDF → pdfminer.six 降级）
│       ├── ocr_sdk.py               # OCR SDK 封装（RapidOCR）
│       ├── asr.py                   # 语音识别工具
│       ├── tts_sdk.py               # 语音合成工具
│       └── databases/               # 数据库层
│           ├── db/
│           │   ├── __init__.py      # re-export 所有 CRUD 函数
│           │   └── history_db.py    # SQLite CRUD 实现（history_records + users 表）
│           └── models/              # ORM 模型预留目录（当前为空）
│
├── data/
│   └── system_knowledge/            # 预加载的 RAG 知识库文档集
│       └── 00_zhangxuefeng_core/    # "张雪峰"人设知识语料库（.md 文件）
│
└── frontend/                        # Vue 3 单页应用（SPA）
    ├── index.html
    ├── vite.config.js               # Vite 构建配置（代理设置、路径别名）
    ├── tailwind.config.js
    ├── package.json
    └── src/
        ├── main.js                  # Vue 应用启动入口（挂载 Pinia + Router）
        ├── App.vue                  # 根组件（仅含 router-view）
        ├── router/
        │   ├── index.js             # Vue Router 路由配置（含路由守卫）
        │   └── guardLogic.js        # 路由守卫逻辑（JWT 校验、Setup 门控）
        ├── stores/                  # Pinia 状态管理
        │   ├── userStore.js         # 用户画像、雷达图数据、置顶记录 ID
        │   └── knowledgeBaseStore.js
        ├── services/                # API 客户端层
        │   ├── authService.js       # JWT 存取、请求头构建
        │   └── llm_service.js       # LLM/Agent API 调用及 SSE 流式传输处理
        ├── utils/                   # 前端通用工具函数
        │   ├── fileConstants.js     # 文件类型白名单、校验函数
        │   ├── ocrHelper.js         # OCR 集成辅助工具
        │   └── dataSourceUtils.js   # 数据源工具函数
        ├── components/              # 可复用 UI 组件
        │   ├── CyberGlassCard.vue   # 统一卡片容器（Dark Cyberpunk + Glassmorphism）
        │   ├── CyberRadarChart.vue  # 六维能力雷达图（ECharts 6）
        │   ├── SetupModal.vue       # 用户信息录入弹窗
        │   ├── DataSourceModal.vue  # 数据源配置弹窗
        │   ├── ChatPreviewModal.vue # 历史对话预览弹窗
        │   └── CustomDropdown.vue   # 自定义下拉选择器
        ├── Landing.vue              # 落地页（Vanta.js 动态背景）
        ├── Auth.vue                 # 注册/登录页
        ├── GlobalSetup.vue          # 入职引导：姓名 + 简历 + 目标岗位录入
        ├── Dashboard.vue            # 主聊天界面（多智能体 LUI + Bento 布局）
        ├── ResumeDiagnosis.vue      # 简历诊断页
        ├── PremiumInterview.vue     # 模拟面试页（含实时雷达图评分）
        ├── CareerPlanning.vue       # 职业规划页
        ├── HistoryArchive.vue       # 历史记录归档页
        └── KnowledgeBase.vue        # 知识库文件管理页
```

## 架构规范

1. **四层分离**（强制执行）：
   - `Router/` — HTTP 请求处理、参数校验，调用 Service 层，不含任何业务逻辑
   - `Service/` — 业务编排层，调用 Agents 层，不直接操作 LLM 或数据库
   - `Service/Agents/` — Agent 定义层，调用 `Utils/llm_client.py`，不关心 HTTP 格式
   - `Service/Utils/` — 工具层，无业务含义，可被任意层调用

2. **路由处理器中禁止包含业务逻辑** — 路由层应将具体任务委托给 Service 层处理

3. **LLM 调用唯一入口** — 所有 Agent 必须通过 `Service/Utils/llm_client.py` 调用 DeepSeek，禁止在其他文件中直接使用 httpx 调用 LLM 接口

4. **SSE 格式统一** — 所有流式响应必须通过 `Service/Utils/sse_utils.py` 生成事件字符串，禁止在业务代码中手写 SSE 格式字符串

5. **配置唯一入口** — 所有环境变量必须从 `Settings/config.py` 导入常量，禁止在其他文件中直接调用 `os.getenv()`

6. **Prompt 与代码解耦** — 所有 System Prompt 字符串必须存放在 `Service/Agents/prompts/` 目录下，禁止在 Agent 或 Router 文件中硬编码 Prompt

7. **前端页面结构扁平化** — Vue 单文件组件（SFCs）直接置于 `src/` 目录下，不进行子目录嵌套；可复用组件放 `src/components/`
