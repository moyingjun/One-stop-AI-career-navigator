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
