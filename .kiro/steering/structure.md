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


# 🏗️ Architecture, Decoupling & Clean Code Standards

You are an expert Software Architect. To prevent technical debt ("spaghetti code") and ensure the codebase is highly readable and maintainable for human developers, you MUST strictly follow these architectural principles:

## 1. Modularization & Separation of Concerns (SoC)
- **No "God Components"**: NEVER dump all logic into a single massive file. If a `.vue` component exceeds 300-400 lines, you MUST extract its parts into smaller, reusable sub-components.
- **Logic Extraction**: Keep UI components "dumb" (focused on rendering and emitting events). Move complex business logic, data formatting, and state management OUT of `.vue` templates. 
  - Put reusable reactive logic into `src/composables/` (Vue 3 Composables).
  - Put global state into `src/stores/` (Pinia).
  - Put pure helper functions into `src/utils/`.
  - Put API HTTP calls into `src/services/`.

## 2. Routing & Business Domain Organization
- Keep `router/index.js` extremely clean and organized. Group routes by feature domain (e.g., Auth, Dashboard, KnowledgeBase, Interview).
- ALWAYS use Route Lazy Loading (e.g., `component: () => import('@/views/...')`) for all page-level components to optimize bundle size and decoupling.
- Use Route Meta Fields (e.g., `meta: { requiresAuth: true }`) for permission control, rather than writing complex permission `if/else` logic inside the UI components.

## 3. Human-Readable & Inheritable Code
- **Naming Conventions**: Use highly descriptive and predictable names. (e.g., Use `fetchUserResume()` instead of `getData()`, use `isSetupModalVisible` instead of `flag`).
- **Comments & Documentation**: You are writing code for human developers to maintain. Add concise comments explaining the *WHY* behind complex algorithms, regex, or business rules. 
- **Props & Emits**: Strictly define component inputs and outputs using `defineProps` and `defineEmits` with basic type definitions to ensure clear component boundaries.