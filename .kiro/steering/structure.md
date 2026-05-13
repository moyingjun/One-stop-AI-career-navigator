# Project Structure

## Architecture

Three-layer backend + SPA frontend. Backend enforces separation of concerns:
- **Router** — HTTP request handling, parameter validation, calls Service
- **Service** — Core business logic (LLM orchestration, RAG, processing)
- **Database** — Data access (single `database.py` module for SQLite)

## Directory Layout

```
/                           # Project root
├── main.py                 # FastAPI app entry point, router registration, startup
├── database.py             # SQLite database module (history_records table)
├── requirements.txt        # Python dependencies
├── api_check.py            # LLM connectivity test script
├── .env                    # Environment config (API keys, model settings)
│
├── Router/                 # API route handlers (FastAPI routers)
│   ├── agent_dispatcher.py # General agent routing
│   ├── resumeDiagnosis.py  # Resume analysis endpoints
│   ├── interview.py        # Interview simulation endpoints
│   ├── careerPlan.py       # Career planning endpoints
│   ├── jobResume.py        # Job-resume matching
│   ├── ocr.py              # OCR endpoints (Tencent Cloud)
│   ├── history_router.py   # History CRUD endpoints
│   └── models/             # Pydantic request/response models
│
├── Service/                # Business logic layer
│   ├── service.py          # Core service functions
│   ├── rag_service.py      # RAG knowledge retrieval + router
│   └── Utils/              # Shared utilities
│
├── data/                   # Static data assets
│   └── system_knowledge/   # RAG knowledge base (markdown files)
│       └── 00_zhangxuefeng_core/  # Domain expert knowledge
│
└── frontend/               # Vue 3 SPA
    ├── package.json
    ├── index.html
    ├── public/             # Static assets (videos, icons)
    └── src/
        ├── main.js         # App bootstrap (Vue + Pinia + Router)
        ├── App.vue         # Root component (router-view only)
        ├── router/index.js # Route definitions + navigation guards
        ├── stores/         # Pinia stores
        │   ├── userStore.js
        │   └── knowledgeBaseStore.js
        ├── services/       # API client layer
        │   └── llm_service.js  # Backend API calls + SSE streaming
        ├── components/     # Reusable UI components
        │   ├── CyberGlassCard.vue
        │   └── CyberRadarChart.vue
        └── *.vue           # Page-level views (Landing, Dashboard, etc.)
```

## Conventions

- Page-level Vue components live directly in `src/` (not in a `views/` folder)
- Reusable components go in `src/components/`
- State stores go in `src/stores/` (Pinia composition style)
- Backend uses PascalCase folder names (`Router/`, `Service/`)
- All complex logic must have Chinese docstring comments
- Variable names must be semantic (no single-letter names)
- Route guards enforce setup completion before accessing personalized pages
