# Implementation Plan: LLM Streaming SSE Refactor

## Overview

Full-chain refactor across five interconnected areas: Dashboard sidebar mode-aware rendering, PremiumInterview context injection on every round, a new SSE stream consumer in llm_service.js, replacing the blocking /chat endpoint with a true SSE StreamingResponse, and rewriting the /evaluate scoring engine to remove WARNING-count penalty logic.

All changes target the existing FastAPI + Vue 3 `<script setup>` + Pinia architecture. No new dependencies are required.

---

## Tasks

- [x] 1. Extend userStore with examRank field
  - [x] 1.1 Add `examRank: ''` to `state()` in `frontend/src/stores/userStore.js`
    - Add the field after `estimatedScore` in the state object
    - _Requirements: 2.1_

  - [x] 1.2 Update `loadFromStorage()` to read `localStorage.getItem('exam_rank') || ''` into `this.examRank`
    - Add the read after the existing `estimatedScore` line
    - _Requirements: 2.2_

  - [x] 1.3 Update `updateUserProfile(payload)` to write `examRank` to both state and localStorage
    - Handle both non-empty and empty/null/undefined cases per the spec
    - Wrap the `localStorage.setItem` call in the existing try/catch block
    - _Requirements: 2.3, 2.4_

  - [x] 1.4 Write property test for userStore examRank persistence
    - **Property 8 (partial): Resume and JD context present in every LLM call** — analogous persistence guarantee for examRank
    - Verify that for any string value passed as `payload.examRank`, `loadFromStorage()` after `updateUserProfile()` restores the same value
    - _Requirements: 2.2, 2.3_

- [x] 2. Implement Dashboard sidebar mode-aware 全局资产 block
  - [x] 2.1 Locate the "全局资产" sidebar section in `frontend/src/Dashboard.vue` and replace its content with a `v-if` / `v-else` branch keyed on `userStore.activeMode`
    - 升学模式 (`activeMode === 'education'`): render `examTypeLabel` badge + `分数: {{ userStore.estimatedScore || '未设置' }} / 排位: {{ userStore.examRank || '未设置' }}`
    - 求职模式 (`else`): render `userStore.targetJob` (fallback `'点击完善个人信息'`) + conditional green "简历已就绪" indicator when `userStore.resumeText` is truthy
    - Reuse the existing `examTypeLabel` computed property already present in Dashboard.vue
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 2.2 Write unit tests for Dashboard sidebar branch rendering
    - Test that education branch renders when `activeMode === 'education'`
    - Test that job branch renders when `activeMode === 'job'`
    - Test `'未设置'` fallback when `estimatedScore` and `examRank` are empty
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Checkpoint — Ensure userStore and Dashboard changes are consistent
  - Verify `userStore.loadFromStorage()` is called in Dashboard's `onMounted` (already present — confirm it runs before sidebar renders)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Rewrite backend `build_messages()` and `/chat` endpoint for full context injection
  - [x] 4.1 Add `build_messages(request: ChatRequest) -> list[dict]` pure function to `Router/interview.py`
    - Construct system message at index 0 with `resume_text[:4000]` + `jd_text[:3000]` + difficulty prompt on EVERY call
    - Append `request.history[-20:]` (filter to `role in ('user', 'assistant')`, cap each content at 2000 chars)
    - Append `{"role": "user", "content": request.user_query}` as the final message
    - Omit resume/JD sections from system message when the respective field is empty (blind mode)
    - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 8.4_

  - [x] 4.2 Write property test for `build_messages()` — Property 1: system message always present
    - **Property 1: System message always present**
    - **Validates: Requirements 3.6**
    - Use `hypothesis` to generate arbitrary `ChatRequest` instances; assert `build_messages(r)[0]['role'] == 'system'` and `'你是一个专业面试官' in build_messages(r)[0]['content']`

  - [x] 4.3 Write property test for `build_messages()` — Property 2: user message always last
    - **Property 2: User message always last**
    - **Validates: Requirements 3.7, 3.8**
    - Use `hypothesis`; assert `build_messages(r)[-1]['role'] == 'user'` and `build_messages(r)[-1]['content'] == r.user_query`

  - [x] 4.4 Write property test for `build_messages()` — Property 8: resume context present when non-empty
    - **Property 8: Resume and JD context present in every LLM call**
    - **Validates: Requirements 3.4, 3.5**
    - For any `ChatRequest` where `resume_text` is non-empty, assert `build_messages(r)[0]['content']` contains a substring of `r.resume_text[:4000]`

- [x] 5. Implement SSE streaming generator and replace `/chat` endpoint
  - [x] 5.1 Add `stream_interview_response(request: ChatRequest)` async generator to `Router/interview.py`
    - Call `build_messages(request)` to get the messages list
    - Use `httpx.AsyncClient(timeout=httpx.Timeout(120.0))` with `stream=True` to call DeepSeek
    - Parse `data:` lines from `response.aiter_lines()`, yield `event: message\ndata: {"content": ...}\n\n` for each non-empty delta content
    - Track `last_yield_time`; yield `': ping\n\n'` if no content for > 15 seconds
    - Catch `httpx.ReadTimeout` → yield error event with `'模型思考超时，请稍后重试'` then done event
    - Catch all other exceptions → yield error event with fixed text (no raw stack trace) then done event
    - Always yield `'event: done\ndata: {}\n\n'` as the final item via `finally` block
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [x] 5.2 Replace the `@router.post("/chat")` handler body to return `StreamingResponse(stream_interview_response(request), media_type="text/event-stream", headers={...})`
    - Include headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
    - Remove the old `call_deepseek()` call and JSON return from this handler
    - Keep the `call_deepseek()` helper function in place — it is still used by `/evaluate`
    - _Requirements: 6.1, 6.2, 6.9_

  - [x] 5.3 Write property test for SSE generator — Property 3: stream always terminates with done event
    - **Property 3: SSE stream always terminates with done event**
    - **Validates: Requirements 6.6, 6.7, 6.8**
    - Mock `httpx.AsyncClient` to simulate success, timeout, and generic exception; collect all yielded strings; assert the last item equals `'event: done\ndata: {}\n\n'`

- [x] 6. Checkpoint — Ensure backend streaming changes are consistent
  - Verify `/chat` returns `text/event-stream` and `/evaluate` still returns JSON
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Rewrite `/evaluate` scoring engine
  - [x] 7.1 Replace `EVALUATE_SYSTEM_PROMPT` with `EVALUATE_SYSTEM_PROMPT_V2` in `Router/interview.py`
    - New prompt must explicitly instruct the AI to ignore `[WARNING]` markers and score only on semantic answer quality
    - Remove all WARNING-count arithmetic penalty logic from the prompt string
    - _Requirements: 7.2, 7.3_

  - [x] 7.2 Update `evaluate_interview()` handler to include `resume_text` and `jd_text` in the evaluation prompt
    - Build `eval_user_prompt` with full `history` text + `resume_text` + `jd_text` (no truncation per spec)
    - Keep `_extract_json_from_text()` helper unchanged
    - Keep `insert_record()` DB write unchanged; wrap in try/except to log and continue on failure
    - _Requirements: 7.1, 7.4, 7.5, 7.6, 7.7_

  - [x] 7.3 Write property test for evaluate endpoint — Property 7: scores unaffected by WARNING count
    - **Property 7: Evaluation scores unaffected by WARNING count**
    - **Validates: Requirements 7.3**
    - Mock `call_deepseek` to return a fixed score JSON; call `evaluate_interview` with histories containing 0, 1, 2, 3 `[WARNING]` markers; assert returned scores are identical in all cases (no arithmetic deduction applied by the router)

- [x] 8. Add `streamInterviewChat()` to llm_service.js
  - [x] 8.1 Implement `async function streamInterviewChat(endpoint, payload, onChunk, onError)` in `frontend/src/services/llm_service.js`
    - POST to `API_BASE_URL + endpoint` with `Content-Type: application/json`
    - Create a single `new TextDecoder('utf-8')` instance per call; decode with `{ stream: true }` to prevent CJK truncation
    - Buffer accumulation + split on `'\n\n'`; keep last incomplete block in buffer
    - Ignore blocks starting with `': '` (heartbeat comment) or with `event: ping`
    - Parse `data:` line as JSON; call `onChunk(content)` for `event: message` blocks with non-empty `content`
    - Call `onChunk(content)` (not `onError`) for `event: error` blocks — append error text to current message bubble
    - Exit loop cleanly on `event: done`
    - Use a boolean `errorFired` flag to ensure `onError` is called at most once per invocation
    - Export `streamInterviewChat` from the module
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 8.1, 8.2, 8.3, 8.6_

  - [x] 8.2 Write property test for SSE consumer — Property 5: ping blocks never trigger onChunk
    - **Property 5: Ping blocks never trigger onChunk**
    - **Validates: Requirements 4.5**
    - Use `fast-check` to generate arbitrary SSE streams containing `: ping\n\n` and `event: ping\ndata: {}\n\n` blocks mixed with valid message blocks; assert `onChunk` is never called for ping blocks

  - [x] 8.3 Write property test for SSE consumer — Property 6: onError called at most once
    - **Property 6: onError called at most once per stream invocation**
    - **Validates: Requirements 4.4**
    - Simulate streams that throw at various points; assert `onError` call count ≤ 1 per `streamInterviewChat` invocation

  - [x] 8.4 Write property test for SSE consumer — Property 4: no CJK character splitting
    - **Property 4: No CJK character splitting across chunk boundaries**
    - **Validates: Requirements 4.9**
    - Use `fast-check` to generate valid UTF-8 Chinese strings, split into arbitrary byte-boundary chunks; assert `TextDecoder({ stream: true })` reassembles them without loss or corruption

- [x] 9. Migrate PremiumInterview.vue sendMessage() to SSE streaming
  - [x] 9.1 Import `streamInterviewChat` from `@/services/llm_service.js` in `PremiumInterview.vue`
    - Add the import at the top of `<script setup>`
    - _Requirements: 5.1_

  - [x] 9.2 Refactor `sendMessage()` to use `streamInterviewChat()` instead of blocking `fetch + response.json()`
    - Before calling `streamInterviewChat`, push a placeholder AI message `{ role: 'ai', content: '', timestamp: ..., isNew: true }` to `messages.value`
    - Pass `onChunk` callback: append chunk to the placeholder message's `content` field and call `scrollToBottom()`
    - Pass `onError` callback: append error text to the placeholder message's `content` field
    - Remove the old `const data = await response.json()` call and the `addMessage('ai', data.reply)` call
    - Keep the existing `[SCORE_UPDATE]` regex extraction logic — apply it inside `onChunk` as content accumulates, or in a post-stream hook after the stream ends
    - Keep `isLoading` / `isAiSpeaking` flag management (`true` before call, `false` in finally)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.3 Write unit tests for sendMessage() SSE integration
    - Mock `streamInterviewChat` to call `onChunk` with known fragments; assert `messages` array accumulates content correctly
    - Mock `streamInterviewChat` to call `onError`; assert error text is appended to the AI message bubble
    - _Requirements: 5.2, 5.3_

- [x] 10. Final checkpoint — Full chain integration
  - Verify the complete flow: Dashboard sidebar renders correctly for both modes, `sendMessage()` in PremiumInterview uses SSE streaming, `/chat` returns `text/event-stream`, `/evaluate` returns clean JSON scores without WARNING penalties
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- The `call_deepseek()` helper in `interview.py` is retained for the `/evaluate` endpoint — do not remove it
- `startInterviewWithDifficulty()` in PremiumInterview.vue already sends `resume_text` + `jd_text` and currently uses blocking fetch; it can be migrated to `streamInterviewChat` as a follow-up (not in scope for this refactor per the design doc's "already ✓" note)
- Property tests use `hypothesis` (Python) and `fast-check` (JavaScript) per the design's Testing Strategy section
- The `[SCORE_UPDATE]` tag extraction in `sendMessage()` must be adapted to work on the accumulated `aiMsg.content` string rather than a single `data.reply` string — apply the regex after the stream completes or on each chunk append

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "4.2", "4.3", "4.4"] },
    { "id": 3, "tasks": ["5.1", "7.1"] },
    { "id": 4, "tasks": ["5.2", "7.2", "8.1"] },
    { "id": 5, "tasks": ["5.3", "7.3", "8.2", "8.3", "8.4"] },
    { "id": 6, "tasks": ["9.1"] },
    { "id": 7, "tasks": ["9.2"] },
    { "id": 8, "tasks": ["9.3"] }
  ]
}
```
