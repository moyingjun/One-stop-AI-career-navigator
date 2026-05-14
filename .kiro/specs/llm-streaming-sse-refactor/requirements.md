# Requirements Document

## Introduction

本文档描述 **LLM Streaming SSE Refactor** 功能的需求，该功能对一站式 AI 职业生涯导航员进行全链路重构，涵盖五个相互关联的改动：

1. **Dashboard.vue 侧边栏**：为"全局资产"区块增加模式感知渲染，区分升学模式与求职模式，并在 userStore 中新增 `examRank` 状态字段。
2. **PremiumInterview.vue**：在每一轮 LLM 调用（而非仅第 0 轮）中注入 `resume_text` 和 `jd_text`，并将阻塞式 `fetch + json()` 替换为 SSE 流式消费。
3. **llm_service.js**：新增 `streamInterviewChat()` 函数，使用 native fetch + ReadableStream + `TextDecoder({ stream: true })` 实现 CJK 安全的 SSE 消费。
4. **Router/interview.py `/chat` 端点**：将阻塞式 JSON 响应替换为真正的 SSE `StreamingResponse`，使用 httpx 异步流式传输，并每 15 秒发送一次心跳 ping。
5. **Router/interview.py `/evaluate` 端点**：重写评分引擎，使用完整上下文（history + resume + jd），移除基于 WARNING 计数的惩罚逻辑。

---

## Glossary

- **Dashboard**: `Dashboard.vue`，应用的中央工作台页面，包含侧边栏和主聊天区域。
- **PremiumInterview**: `PremiumInterview.vue`，模拟面试页面，负责面试对话 UI 和评估展示。
- **LLM_Service**: `frontend/src/services/llm_service.js`，前端 API 客户端服务层。
- **Interview_Router**: `Router/interview.py`，FastAPI 面试路由模块，处理 `/api/interview/*` 端点。
- **userStore**: Pinia 状态管理 Store（`frontend/src/stores/userStore.js`），管理用户画像全局状态。
- **SSE_Consumer**: `streamInterviewChat()` 函数，负责消费后端 SSE 流的前端逻辑。
- **SSE_Generator**: `stream_interview_response()` 异步生成器，负责产生 SSE 格式输出的后端逻辑。
- **ChatRequest**: 面试聊天端点的 Pydantic 请求模型，包含 `user_query`、`history`、`resume_text`、`jd_text`、`difficulty` 字段。
- **EvaluateRequest**: 面试评估端点的 Pydantic 请求模型，包含 `user_query`、`history`、`resume_text`、`jd_text`、`difficulty` 字段。
- **build_messages**: `Interview_Router` 中的纯函数，将 `ChatRequest` 转换为 DeepSeek API 所需的消息列表。
- **activeMode**: userStore 中的状态字段，值为 `'job'`（求职模式）或 `'education'`（升学模式）。
- **examRank**: userStore 中新增的状态字段，存储升学模式下的考试排位信息，对应 localStorage 键 `'exam_rank'`。
- **examType**: userStore 中的状态字段，存储升学考试类型（如 `'zhuanchaben'`、`'gaokao'`、`'kaoyan'` 等）。
- **examTypeLabel**: Dashboard.vue 中的计算属性，将 `examType` 枚举值映射为中文显示标签。
- **onChunk**: `streamInterviewChat()` 的回调参数，每收到一个内容片段时被调用一次。
- **onError**: `streamInterviewChat()` 的回调参数，流式传输失败时被调用。
- **WARNING_marker**: 面试对话历史中的 `[WARNING]` 标记字符串，由面试官 AI 在检测到无效输入时插入。
- **TextDecoder**: Web API，用于将字节流解码为字符串；`{ stream: true }` 模式可防止多字节 CJK 字符在块边界处被截断。
- **heartbeat_ping**: SSE 注释行 `': ping\n\n'`，由后端每 15 秒在无内容输出时发送，用于防止代理超时断连。

---

## Requirements

### Requirement 1: Dashboard 侧边栏模式感知渲染

**User Story:** 作为用户，我希望 Dashboard 侧边栏的"全局资产"区块能根据我当前所处的模式（升学或求职）展示对应的信息，以便我能快速了解自己的核心资产状态。

#### Acceptance Criteria

1. WHEN `userStore.activeMode` 为 `'education'`，THE Dashboard SHALL 在"全局资产"区块渲染升学模式分支，显示 `examTypeLabel` 徽章、`estimatedScore` 和 `examRank`，且不渲染求职模式分支。
2. WHEN `userStore.activeMode` 为 `'job'`，THE Dashboard SHALL 在"全局资产"区块渲染求职模式分支：若 `userStore.targetJob` 非空则显示其文本，否则显示占位文本"点击完善个人信息"；若 `userStore.resumeText` 非空则显示绿色"简历已就绪"指示器，否则不显示该指示器。
3. WHEN `userStore.activeMode` 为 `'education'` 且 `userStore.estimatedScore` 为空字符串或 falsy，THE Dashboard SHALL 在分数位置显示文本 `'未设置'`。
4. WHEN `userStore.activeMode` 为 `'education'` 且 `userStore.examRank` 为空字符串或 falsy，THE Dashboard SHALL 在排位位置显示文本 `'未设置'`。
5. WHEN Dashboard 组件挂载完成（`onMounted` 触发），THE Dashboard SHALL 调用 `userStore.loadFromStorage()`，该调用须在任何"全局资产"区块渲染之前完成，以确保 `examRank` 等字段已从 localStorage 加载。

---

### Requirement 2: userStore 新增 examRank 状态字段

**User Story:** 作为开发者，我希望 userStore 能持久化存储用户的考试排位信息，以便升学模式下的 Dashboard 侧边栏能正确读取并展示该数据。

#### Acceptance Criteria

1. THE userStore SHALL 在 `state()` 中包含 `examRank` 字段，初始值为空字符串 `''`。
2. WHEN `userStore.loadFromStorage()` 被调用，THE userStore SHALL 从 localStorage 键 `'exam_rank'` 读取值并赋给 `this.examRank`；若该键不存在或值为 falsy，则赋值为 `''`。
3. WHEN `userStore.updateUserProfile(payload)` 被调用且 `payload.examRank` 为非空字符串（即 `payload.examRank` 不为 `''`、`null`、`undefined` 且键存在），THE userStore SHALL 将 `this.examRank` 更新为 `payload.examRank` 并调用 `localStorage.setItem('exam_rank', payload.examRank)`；若 localStorage 写入抛出异常，则静默忽略，内存状态仍保持更新。
4. WHEN `userStore.updateUserProfile(payload)` 被调用且 `payload.examRank` 为 `''`、`null`、`undefined` 或键不存在，THE userStore SHALL 将 `this.examRank` 设为 `''` 并调用 `localStorage.setItem('exam_rank', '')`；若 localStorage 写入抛出异常，则静默忽略，内存状态仍保持更新。

---

### Requirement 3: PremiumInterview 每轮调用注入完整上下文

**User Story:** 作为面试候选人，我希望面试官 AI 在整个面试过程中始终了解我的简历和目标岗位信息，而不仅仅是在第一轮，以便面试官能持续针对我的背景进行追问。

#### Acceptance Criteria

1. WHEN `sendMessage()` 被调用，THE PremiumInterview SHALL 在请求体中包含 `resume_text`（取自 `resumeText.value`，即 localStorage `'resume_text'` 的当前值）和 `jd_text`（取自 `interviewJd.value`，即 localStorage `'current_interview_jd'` 的当前值）字段，无论当前是第几轮对话。
2. WHEN `startInterviewWithDifficulty()` 被调用，THE PremiumInterview SHALL 在请求体中包含 `resume_text` 和 `jd_text` 字段，取值来源与 Criterion 1 相同。
3. IF `resumeText.value` 或 `interviewJd.value` 为空字符串，THEN THE PremiumInterview SHALL 仍将空字符串作为对应字段的值包含在请求体中，不得省略该字段键。
4. WHEN 后端 `/api/interview/chat` 收到 `resume_text` 非空的 `ChatRequest`，THE Interview_Router SHALL 构建系统消息，其 `content` 字段包含 `resume_text` 的前 4000 个字符作为子串（若 `resume_text` 长度不超过 4000 字符则包含完整内容）。
5. WHEN 后端 `/api/interview/chat` 收到 `jd_text` 非空的 `ChatRequest`，THE Interview_Router SHALL 构建系统消息，其 `content` 字段包含 `jd_text` 的前 3000 个字符作为子串（若 `jd_text` 长度不超过 3000 字符则包含完整内容）。
6. WHEN 后端 `/api/interview/chat` 收到任意合法 `ChatRequest`，THE Interview_Router SHALL 构建消息列表，其中第一条消息的 `role` 字段值为 `'system'`。
7. WHEN 后端 `/api/interview/chat` 收到任意合法 `ChatRequest`，THE Interview_Router SHALL 构建消息列表，其中最后一条消息的 `role` 字段值为 `'user'`，`content` 字段值等于 `request.user_query`。
8. WHEN 后端 `/api/interview/chat` 收到任意合法 `ChatRequest`，THE Interview_Router SHALL 构建长度大于等于 2 的消息列表（至少包含系统消息和当前用户消息）。

---

### Requirement 4: llm_service.js 新增 streamInterviewChat() 函数

**User Story:** 作为前端开发者，我希望服务层提供一个专用的 SSE 流式消费函数，以便 PremiumInterview 组件能以打字机效果实时展示 AI 回复，而不是等待完整响应后一次性渲染。

#### Acceptance Criteria

1. THE LLM_Service SHALL 导出 `streamInterviewChat(endpoint, payload, onChunk, onError)` 函数，接受端点路径字符串、请求体对象、内容回调函数和错误回调函数四个参数，并返回一个 Promise，该 Promise 在流正常结束或发生错误后 resolve（不 reject）。
2. WHEN `streamInterviewChat` 被调用，THE LLM_Service SHALL 使用 native `fetch` API 向 `API_BASE_URL + endpoint` 发送 POST 请求，请求头包含 `Content-Type: application/json`，请求体为 `JSON.stringify(payload)`。
3. WHEN 服务器返回 HTTP 非 200 状态码（即 `response.ok === false`），THE LLM_Service SHALL 调用 `onError('[网络连接异常，请重试]')` 并终止处理，不调用 `onChunk`，Promise resolve。
4. WHEN 读取 SSE 流时发生网络异常（`fetch` 抛出或 `reader.read()` 抛出），THE LLM_Service SHALL 使用布尔标志位确保 `onError('[网络连接异常，请重试]')` 在单次 `streamInterviewChat` 调用中至多被调用一次，之后 Promise resolve。
5. WHEN SSE 流中出现以 `': '` 开头的注释行（心跳 ping）或 `event` 字段值为 `'ping'` 的块，THE LLM_Service SHALL 忽略该块，不调用 `onChunk`。
6. WHEN SSE 流中出现 `event` 字段值为 `'message'` 的块，且 `data:` 行解析为合法 JSON 对象，且该对象的 `content` 字段为长度大于等于 1 的字符串，THE LLM_Service SHALL 以该 `content` 字符串为唯一参数调用 `onChunk`。
7. WHEN SSE 流中出现 `event` 字段值为 `'done'` 的块，THE LLM_Service SHALL 退出读取循环，不再调用 `onChunk`，Promise resolve。
8. WHEN SSE `data:` 行内容不是合法 JSON（`JSON.parse` 抛出），THE LLM_Service SHALL 静默跳过该块，继续处理后续块，不调用 `onError`。
9. THE LLM_Service SHALL 创建单个 `new TextDecoder('utf-8')` 实例（每次 `streamInterviewChat` 调用创建一次，不在循环内重复创建），以 `{ stream: true }` 模式调用 `decode(value, { stream: true })` 解码每个字节块，将解码结果追加至行缓冲区，以 `'\n\n'` 切割完整 SSE 块，保留末尾不完整片段至下次迭代，从而防止 CJK 多字节字符在块边界处被截断。
10. WHEN SSE 流中出现 `event` 字段值为 `'error'` 的块，且 `data:` 行解析为合法 JSON 对象且 `content` 字段非空，THE LLM_Service SHALL 以该 `content` 字符串为参数调用 `onChunk`（将错误内容追加至当前消息气泡），而非调用 `onError`。

---

### Requirement 5: PremiumInterview 替换阻塞式 fetch 为 SSE 流式消费

**User Story:** 作为面试候选人，我希望面试官的回复能以流式打字机效果逐字出现，而不是等待数秒后突然全部显示，以获得更自然的对话体验。

#### Acceptance Criteria

1. WHEN `sendMessage()` 发送用户消息后，THE PremiumInterview SHALL 调用 `streamInterviewChat()` 而非 `response.json()` 来获取 AI 回复，原有的 `const data = await response.json()` 调用须被移除。
2. WHEN `streamInterviewChat` 的 `onChunk` 回调被触发，THE PremiumInterview SHALL 将收到的内容片段追加（`+=`）到 `messages` 数组中最后一条 AI 消息对象的 `content` 字段，实现打字机效果。
3. WHEN `streamInterviewChat` 的 `onError` 回调被触发，THE PremiumInterview SHALL 将错误信息追加（`+=`）到 `messages` 数组中最后一条 AI 消息对象的 `content` 字段，向用户展示内联错误提示，不弹出独立错误对话框。
4. WHEN `sendMessage()` 准备发起流式请求前，THE PremiumInterview SHALL 向 `messages` 数组推入一条 `{ role: 'ai', content: '', timestamp: Date.now(), isNew: true }` 格式的占位消息对象，供后续 `onChunk` 回调追加内容。
5. WHEN `streamInterviewChat` 的 `onChunk` 回调被触发，THE PremiumInterview SHALL 在每次回调执行后调用 `scrollToBottom()` 以保持消息列表滚动到底部。

---

### Requirement 6: Interview_Router /chat 端点替换为 SSE StreamingResponse

**User Story:** 作为系统架构师，我希望面试聊天端点返回真正的 SSE 流式响应，以便前端能实时接收并展示 AI 生成的内容，同时避免长时间等待导致的代理超时。

#### Acceptance Criteria

1. WHEN POST 请求发送至 `/api/interview/chat`，THE Interview_Router SHALL 返回 `StreamingResponse`，`media_type` 为 `'text/event-stream'`，不再返回 JSON 响应体。
2. THE Interview_Router SHALL 在 `StreamingResponse` 的响应头中包含 `Cache-Control: no-cache`、`Connection: keep-alive` 和 `X-Accel-Buffering: no` 三个头字段。
3. WHEN `stream_interview_response(request)` 生成器运行时，THE Interview_Router SHALL 使用 `httpx.AsyncClient(timeout=httpx.Timeout(120.0))` 以 `stream=True` 模式向 DeepSeek API 发起请求，不使用同步 `httpx.Client`。
4. WHEN DeepSeek API 的 SSE 流中出现包含非空 `content` 字段的 delta，THE Interview_Router SHALL yield 格式严格为 `f'event: message\ndata: {json.dumps({"content": content}, ensure_ascii=False)}\n\n'` 的字符串。
5. WHEN 距上次 yield 内容（或上次 ping）超过 15 秒，THE Interview_Router SHALL yield `': ping\n\n'` 并将计时器重置为当前时间，无论 DeepSeek 流是否仍在传输。
6. WHEN `stream_interview_response(request)` 生成器因任何原因退出（正常完成、`httpx.ReadTimeout`、或其他异常），THE Interview_Router SHALL 在退出前 yield `'event: done\ndata: {}\n\n'` 作为最后一个 yield 项。
7. WHEN `httpx.ReadTimeout` 异常被捕获，THE Interview_Router SHALL 先 yield `'event: error\ndata: {"content":"模型思考超时，请稍后重试"}\n\n'`，再 yield done 事件，不将原始异常信息暴露给客户端。
8. WHEN 非 `httpx.ReadTimeout` 的其他异常被捕获，THE Interview_Router SHALL 先 yield 包含固定错误提示文本（不含原始异常堆栈）的 `event: error` 块，再 yield done 事件。
9. WHEN POST 请求发送至 `/api/interview/chat` 且请求体不符合 `ChatRequest` Pydantic 模型验证，THE Interview_Router SHALL 返回 HTTP 422 Unprocessable Entity 响应，不启动 SSE 生成器。

---

### Requirement 7: Interview_Router /evaluate 端点重写评分引擎

**User Story:** 作为面试候选人，我希望面试结束后的评分能客观反映我的真实回答质量，而不受系统内部 WARNING 标记的干扰，以获得公正的能力评估结果。

#### Acceptance Criteria

1. WHEN POST 请求发送至 `/api/interview/evaluate`，THE Interview_Router SHALL 使用包含 `EvaluateRequest.history` 中所有条目、完整 `resume_text`（不截断）和完整 `jd_text`（不截断）的提示词构建评估请求发送至 DeepSeek API。
2. THE Interview_Router SHALL 使用 `EVALUATE_SYSTEM_PROMPT_V2` 作为评估系统提示词，该提示词须明确包含指示 AI 忽略 `[WARNING]` 标记的指令，且不得包含任何基于 WARNING 计数执行算术扣分的指令。
3. WHEN `EvaluateRequest.history` 中包含含有 `[WARNING]` 子串的消息条目，THE Interview_Router SHALL 返回仅基于用户语义回答质量的评分，不在 AI 输出之外对任何维度执行额外的算术扣分操作。
4. WHEN 评估成功，THE Interview_Router SHALL 返回 JSON 响应 `{"success": true, "data": {...}}`，其中 `data` 对象包含且仅包含 `professional`、`logic`、`communication`、`problemSolving`、`potential`、`resilience` 六个值为 0–100 整数的键，以及 `comment` 一个值为字符串的键。
5. WHEN `_extract_json_from_text()` 被调用时，THE Interview_Router SHALL 依次尝试：提取 markdown 代码块（` ```json ... ``` `）内的 JSON、提取裸 JSON 对象（以 `{` 开头至匹配 `}` 结尾的子串），两种策略均须覆盖，任一成功即返回解析结果。
6. IF 所有 JSON 提取策略均失败，THEN THE Interview_Router SHALL 返回 `{"success": false, "msg": "打分失败，请重试"}`，且不向 SQLite 数据库写入任何记录。
7. WHEN 评估成功且 `_extract_json_from_text()` 返回合法评分对象，THE Interview_Router SHALL 调用 `insert_record()` 将以下字段写入 SQLite 数据库：`session_type`（值为 `'interview'`）、`resume_text`、`jd_text`、`difficulty`、`scores`（JSON 序列化的评分对象）、`comment`、`created_at`（UTC 时间戳）；若 `insert_record()` 抛出异常，则记录日志并继续返回成功响应，不向客户端暴露数据库错误。

---

### Requirement 8: SSE 协议合规性与错误恢复

**User Story:** 作为系统运维人员，我希望 SSE 流式传输在各种异常场景下都能优雅降级，以确保用户不会看到空白消息气泡或无响应的界面。

#### Acceptance Criteria

1. WHEN SSE 流在收到 `event: done` 之前因网络中断（`reader.read()` 返回 `done: true` 或抛出 `TypeError`）而终止，THE LLM_Service SHALL 调用 `onError('[网络连接异常，请重试]')`，THE PremiumInterview SHALL 将该错误文本追加至当前 AI 消息气泡的 `content` 字段，不留下空白消息气泡。
2. WHEN 后端 DeepSeek 调用超时，THE Interview_Router SHALL 通过 SSE `event: error` 块将固定超时提示文本（`'模型思考超时，请稍后重试'`）传递给前端，THE SSE_Consumer SHALL 将该文本通过 `onChunk` 追加到当前消息气泡的 `content` 字段。
3. WHEN SSE `data:` 行内容不是合法 JSON（如上游代理返回 HTML 错误页面），THE LLM_Service SHALL 静默跳过该块，不调用 `onError`，不中断流的处理，继续读取后续字节。
4. WHEN `resume_text` 或 `jd_text` 为空字符串，THE Interview_Router SHALL 在 `build_messages()` 中省略对应的上下文段落（即系统消息中不包含简历或 JD 相关句子），面试以"盲测模式"继续进行，返回正常 SSE 流，不返回错误响应。
5. IF 评估 JSON 解析失败，THEN THE Interview_Router SHALL 返回 `{"success": false, "msg": "打分失败，请重试"}`，THE PremiumInterview SHALL 展示重试按钮；WHEN 用户点击重试按钮，THE PremiumInterview SHALL 隐藏重试按钮并重新发起评估请求；WHEN 评估请求成功返回，THE PremiumInterview SHALL 隐藏重试按钮并展示评分结果。
6. WHEN SSE 流中出现 `event` 字段值为 `'error'` 的块，THE SSE_Consumer SHALL 将该块 `data:` 行 JSON 中的 `content` 字段值通过 `onChunk` 追加至当前消息气泡，不调用 `onError`，不中断流的处理（继续等待 `event: done`）。
