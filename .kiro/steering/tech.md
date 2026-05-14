# Tech Stack & Build System

## Backend (Python)

- **Framework**: FastAPI with Uvicorn (ASGI)
- **Database**: SQLite via `sqlite3` (file: `history.db`)
- **LLM Provider**: DeepSeek API (via httpx, configurable base URL in `.env`)
- **RAG**: Custom RAG service using markdown knowledge files
- **OCR**: Tencent Cloud OCR SDK
- **PDF Parsing**: PyMuPDF, PyPDF2, pdfminer.six
- **Validation**: Pydantic v2
- **Environment**: python-dotenv for config

## Frontend (Vue 3 + Vite)

- **Framework**: Vue 3 (Composition API with `<script setup>`)
- **Build Tool**: Vite 8
- **State Management**: Pinia
- **Routing**: Vue Router 5 (history mode)
- **Styling**: Tailwind CSS 4 (via PostCSS plugin)
- **Charts**: ECharts 6 + vue-echarts
- **3D Effects**: Three.js + Vanta.js
- **HTTP Client**: Axios + native fetch (for SSE streaming)
- **Icons**: lucide-vue-next
- **Utilities**: @vueuse/core, @formkit/auto-animate
- **Document Parsing** (client-side): mammoth (DOCX), pdfjs-dist (PDF)
- **Markdown Rendering**: marked

## Common Commands

```bash
# Backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev      # Dev server (Vite)
npm run build    # Production build
npm run preview  # Preview production build
```

## Environment Variables (`.env` at project root)

- `DEEPSEEK_API_KEY` — LLM API key
- `DEEPSEEK_BASE_URL` — LLM endpoint URL
- `DEEPSEEK_MODEL_NAME` — Model identifier (default: deepseek-v4-flash)

## API Communication

- Frontend calls backend at `/api/*` endpoints
- Local dev uses `http://127.0.0.1:8000/api`, production uses relative `/api`
- Streaming responses use Server-Sent Events (SSE) with `event: reply` / `data: {payload}` format


# 🛠️ System Architecture & AI Execution Rules (Tech Spec)

You are an expert Full-Stack Architect. Whenever you execute tasks, write code, or run terminal commands for this project, you MUST strictly adhere to the following configurations and rules.

## 1. 🚫 AI Safety & Execution Rules (CRITICAL)
To prevent system freezes and memory issues, you must follow these terminal rules:
- **FORBIDDEN COMMANDS**: NEVER run static type checking commands like `vue-tsc` or `tsc`. NEVER run production builds (`vite build`, `npm run build`) unless explicitly requested by the user. If you encounter type errors, fix the code directly instead of running verification commands.
- **TRUSTED COMMANDS**: You are allowed to run the following safe commands:
  - Backend: `uvicorn main:app --reload --port 8000`
  - Frontend: `npm run dev`
  - Package Management: `npm install/uninstall <pkg>`, `pip install -r requirements.txt`
  - Formatting & Linting: `black .`, `prettier --write .`, `npm run lint`

## 2. 🧩 Tech Stack
**Frontend (Vue 3 + Vite 8)**
- Core: Vue 3 (STRICTLY Composition API with `<script setup>`), Pinia for state management, Vue Router 5 (history mode).
- Styling & UI: Tailwind CSS 4 (via PostCSS), lucide-vue-next for icons.
- Visuals & Charts: ECharts 6 + vue-echarts, Three.js + Vanta.js for 3D effects.
- Parsing: mammoth (DOCX), pdfjs-dist (PDF), marked (Markdown rendering).

**Backend (Python + FastAPI)**
- Core: FastAPI with Uvicorn (ASGI), Pydantic v2 for validation.
- Database: SQLite via `sqlite3` (File: `history.db`).
- AI & LLM: DeepSeek API (via httpx), Tencent Cloud OCR SDK.
- RAG & PDF: Custom RAG service (Markdown), PyMuPDF, PyPDF2, pdfminer.six.

## 3. 💻 Code Style & Architecture Guidelines
- **Frontend**: ALWAYS use `<script setup>`. Ensure UI components follow the existing "Dark Cyberpunk + Glassmorphism" design language.
- **Backend**: Use asynchronous programming (`async/await`) properly in FastAPI route handlers. Manage configs using `python-dotenv` reading from `.env` (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL_NAME`).
- **API Communication**: 
  - Frontend calls backend exclusively at `/api/*` endpoints.
  - Local dev uses `http://127.0.0.1:8000/api`.
  - For streaming LLM responses, strictly implement Server-Sent Events (SSE) using the format: `event: reply` / `data: {payload}` via native `fetch`.