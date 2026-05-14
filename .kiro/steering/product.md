---
inclusion: always
---

# Product Overview

One-stop AI Career Navigator (一站式AI职业生涯导航员) is an AI-powered career guidance platform targeting IT job seekers in the Chinese market. It combines LLM-driven coaching, RAG-backed domain knowledge, and a streamlined UX to guide users from resume review through interview prep to career planning.

## Core Features

- **Resume Diagnosis**: Upload PDF/DOCX resumes → AI parses, scores, and returns structured improvement feedback
- **Mock Interview**: AI-driven interview simulation with real-time SSE streaming responses
- **Career Planning**: Personalized career path recommendations derived from the user's profile and goals
- **Knowledge Base (RAG)**: Domain expertise store (张雪峰-style career advice) used to ground all AI responses
- **History & Saved Chats**: Persistent SQLite record of all AI interactions; users can save/bookmark sessions
- **Dashboard**: Central hub displaying user profile summary and quick-access entry points to all features

## User Flow & Access Model

- **Guest mode**: Landing page is publicly accessible; no login required
- **Setup gate**: Users must complete a one-time profile setup before accessing personalized features (Dashboard, Interview, Career Plan, Resume Diagnosis)
- **Route guards** in `router/index.js` enforce the setup gate — do not replicate this logic inside page components

## AI Response Conventions

- All AI-generated text must be in **Simplified Chinese**
- Tone: professional career-coaching voice, warm but authoritative (modeled on 张雪峰's style)
- Streaming responses use SSE (`event: reply` / `data: {payload}`) — never buffer and return all at once
- RAG context from `data/system_knowledge/` must be injected into prompts where relevant

## UI / UX Design Language

- Visual theme: **Dark Cyberpunk + Glassmorphism** — dark backgrounds, neon accent colors, frosted-glass card surfaces
- All reusable card surfaces use `CyberGlassCard.vue`; do not inline equivalent styles in page components
- Charts use `CyberRadarChart.vue` (ECharts 6 + vue-echarts); maintain consistent color palette across all chart instances
- Responsive and mobile-friendly; test layouts at both desktop and mobile breakpoints

## Feature Boundaries & Conventions

- Resume parsing happens **client-side** (mammoth for DOCX, pdfjs-dist for PDF) before sending text to the backend
- OCR fallback for scanned PDFs uses the Tencent Cloud OCR SDK via the `/api/ocr` endpoint
- History records are stored in SQLite (`history.db`) through `database.py` — no ORM, raw `sqlite3`
- Each feature domain (resume, interview, career plan, knowledge base) has its own Router file and Service file; do not cross-wire them
