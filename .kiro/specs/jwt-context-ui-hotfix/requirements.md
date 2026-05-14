# Requirements Document

## Introduction

多租户架构升级后，前端出现四个相互独立但同等紧急的断层问题，需要紧急修复：

1. **Bug 1**：`PremiumInterview.vue` 中 `sendMessage` 函数推入占位 AI 消息时，将 `Date.now()` 毫秒整数直接赋给 `timestamp` 字段，导致聊天气泡渲染裸露的 Unix 时间戳数字（如 `1778750883422`）。
2. **Bug 2**：`authService.js` 已提供 `getAuthHeaders()` 工具函数，但多个页面和服务的 `fetch` 请求点未调用该函数，导致所有 `/api/*` 请求缺少 `Authorization: Bearer <token>` 请求头，后端返回 401 错误；同时 `endInterview` 评估成功后缺少保存历史记录的调用。
3. **Bug 3**：`SetupModal` 写入 `localStorage` 的键名（`target_job`、`job_description`）与 `PremiumInterview.vue`、`ResumeDiagnosis.vue` 读取的键名（`target_role`、`current_interview_jd`）不一致，导致大模型无法获取用户填写的求职意向和岗位描述上下文。
4. **Bug 4**：`PremiumInterview.vue` 左侧候选人档案栏只渲染简历原文（`resumeText`），`targetRole`（求职意向）未在档案栏独立展示，导致面试官视角缺失关键候选人信息。

---

## Glossary

- **PremiumInterview**：`frontend/src/PremiumInterview.vue`，AI 模拟面试页面组件
- **ResumeDiagnosis**：`frontend/src/ResumeDiagnosis.vue`，简历诊断页面组件
- **Dashboard**：`frontend/src/Dashboard.vue`，工作台主页面组件
- **LLM_Service**：`frontend/src/services/llm_service.js`，封装 LLM 流式请求的服务模块
- **AuthService**：`frontend/src/services/authService.js`，提供 `getAuthHeaders()` 的认证服务模块
- **SetupModal**：`frontend/src/components/SetupModal.vue`，用户信息录入弹窗组件
- **UserStore**：`frontend/src/stores/userStore.js`，Pinia 全局用户状态存储
- **Message**：聊天消息对象，包含 `role`、`content`、`timestamp`、`isNew` 字段
- **timestamp**：消息对象中的时间字段，修复后统一为 `HH:mm` 格式字符串（两位小时:两位分钟）
- **getAuthHeaders**：`AuthService` 提供的工具函数，返回包含 `Authorization: Bearer <token>` 的请求头对象；token 不存在或为空字符串时返回空对象 `{}`
- **targetRole**：用户填写的求职意向岗位名称，来源优先级为 `UserStore` → `localStorage`
- **interviewJd**：用户填写的岗位描述（JD），来源优先级为 `UserStore` → `localStorage`
- **候选人档案栏**：`PremiumInterview` 左侧面板中展示候选人简历和求职意向的区域
- **非空值**：非 `null` 且非空字符串（长度大于 0）的值

---

## Requirements

### 需求 1：统一消息时间戳格式

**用户故事**：作为面试候选人，我希望 AI 回复气泡显示可读的时间（如 `17:22`），而不是毫秒级数字，以便我能清晰了解对话时间线。

#### 验收标准

1. WHEN `sendMessage` 函数向 `messages` 数组推入占位 AI 消息对象时，THE `PremiumInterview` SHALL 将该消息对象的 `timestamp` 字段赋值为符合 `HH:mm` 格式的当前本地时间字符串（两位小时、冒号、两位分钟，如 `09:05`、`17:22`）。

2. WHEN `addMessage` 函数向 `messages` 数组添加任意消息对象时，THE `PremiumInterview` SHALL 将该消息对象的 `timestamp` 字段赋值为符合 `HH:mm` 格式的当前本地时间字符串，与 `sendMessage` 推入的占位消息格式保持一致。

3. WHEN 用户发送一条消息后 AI 开始流式回复时，THE `PremiumInterview` SHALL 在聊天气泡右下角渲染格式为 `HH:mm` 的时间字符串，不渲染毫秒级整数。

4. IF `messages` 数组中任意消息对象的 `timestamp` 字段值为毫秒级整数（即大于 `9999999999` 的数字），THEN THE `PremiumInterview` SHALL 在渲染前将该值转换为 `HH:mm` 格式字符串后再渲染，不直接将原始整数展示给用户。

---

### 需求 2：全局 JWT 认证请求头补全

**用户故事**：作为已登录用户，我希望所有向后端发起的 API 请求都携带我的身份令牌，以便后端能正确识别我的身份并返回个人化数据，而不是返回 401 未授权错误。

#### 验收标准

1. WHEN `PremiumInterview` 调用 `startInterviewWithDifficulty` 函数向 `/api/interview/chat` 发起 POST 请求时，THE `PremiumInterview` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

2. WHEN `PremiumInterview` 调用 `initInterview` 函数通过历史记录 ID 向 `/api/history/:id` 发起 GET 请求恢复历史面试时，THE `PremiumInterview` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

3. WHEN `PremiumInterview` 调用 `endInterview` 函数向 `/api/interview/evaluate` 发起 POST 请求时，THE `PremiumInterview` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

4. WHEN `endInterview` 函数成功获取评估结果（`resData.success === true` 且 `resData.data` 存在）后，THE `PremiumInterview` SHALL 向 `/api/history` 发起 POST 请求保存本次面试历史记录，请求体包含 `category`、`user_input`、`ai_result`、`scores`、`chat_history`、`extra_data` 字段，且该请求的 `headers` 中包含 `getAuthHeaders()` 的返回值。

5. IF `endInterview` 中保存历史记录的 POST 请求失败，THEN THE `PremiumInterview` SHALL 仅通过 `console.error` 记录错误，不阻断雷达图和评估结果的正常展示流程。

6. WHEN `ResumeDiagnosis` 调用 `startDiagnosis` 函数向 `/api/resume/diagnose` 发起请求时，THE `ResumeDiagnosis` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

7. WHEN `ResumeDiagnosis` 调用 `initResume` 函数通过历史记录 ID 恢复历史诊断时，THE `ResumeDiagnosis` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

8. WHEN `Dashboard` 调用 `loadHistory` 函数向 `/api/history` 发起 GET 请求时，THE `Dashboard` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

9. WHEN `Dashboard` 调用 `loadLatestRadarData` 函数向 `/api/history` 发起 GET 请求时，THE `Dashboard` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

10. WHEN `Dashboard` 调用 `toggleSaveRecord` 函数向 `/api/history/:id/save` 发起 PATCH 请求时，THE `Dashboard` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

11. WHEN `Dashboard` 调用 `deleteHistoryRecord` 函数向 `/api/history/:id` 发起 DELETE 请求时，THE `Dashboard` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

12. WHEN `Dashboard` 调用 `sendGeneralChatMessage` 函数向 `/api/agent/chat` 发起 POST 请求时，THE `Dashboard` SHALL 在请求的 `headers` 中合并 `getAuthHeaders()` 的返回值。

13. WHEN `LLM_Service` 中的 `callAgent` 函数发起 API 请求时，THE `LLM_Service` SHALL 通过本地工具函数读取 `localStorage.getItem('token')` 并在 token 为长度大于 0 的字符串时将 `Authorization: Bearer <token>` 加入请求头。

14. WHEN `LLM_Service` 中的 `streamInterviewChat` 函数发起流式请求时，THE `LLM_Service` SHALL 通过本地工具函数读取 `localStorage.getItem('token')` 并在 token 为长度大于 0 的字符串时将 `Authorization: Bearer <token>` 加入请求头。

15. THE `LLM_Service` SHALL 使用独立的本地 `getAuthHeaders()` 工具函数（通过 `localStorage.getItem('token')` 读取 token），不依赖 `AuthService` 模块的导入，以避免在非 Vue 模块中引入 Pinia 依赖。

16. WHILE `localStorage.getItem('token')` 返回长度大于 0 的字符串，THE 系统 SHALL 保证所有向 `/api/*` 路径发起的 `fetch` 请求的 `headers` 中包含值为 `Bearer <token>` 的 `Authorization` 字段。

17. IF `localStorage.getItem('token')` 返回 `null` 或空字符串，THEN THE `getAuthHeaders` 工具函数 SHALL 返回空对象 `{}`，不在请求头中添加 `Authorization` 字段，不发送 `Authorization: Bearer null` 或 `Authorization: Bearer ` 等无效头。

---

### 需求 3：SetupModal 上下文键名统一与多键名降级读取

**用户故事**：作为用户，我希望在 SetupModal 中填写的求职意向和岗位描述能被面试和简历诊断功能正确读取，以便大模型能根据我的实际岗位需求提供针对性的面试问题和诊断建议。

#### 验收标准

1. WHEN `PremiumInterview` 的 `initInterview` 函数读取目标岗位时，THE `PremiumInterview` SHALL 按照 `UserStore.targetJob` → `localStorage.getItem('target_role')` → `localStorage.getItem('target_job')` 的优先级顺序依次降级读取（每一级均为非 null 且非空字符串时才采用），将第一个非空值赋给 `targetRole.value`，所有来源均为空时赋值为空字符串 `''`。

2. WHEN `PremiumInterview` 的 `initInterview` 函数读取岗位描述时，THE `PremiumInterview` SHALL 按照 `UserStore.jobDescription` → `localStorage.getItem('job_description')` → `localStorage.getItem('current_interview_jd')` → `localStorage.getItem('jd_content')` 的优先级顺序依次降级读取（每一级均为非 null 且非空字符串时才采用），将第一个非空值赋给 `interviewJd.value`，所有来源均为空时赋值为空字符串 `''`。

3. WHEN `ResumeDiagnosis` 读取目标岗位时，THE `ResumeDiagnosis` SHALL 按照 `UserStore.targetJob` → `localStorage.getItem('target_role')` → `localStorage.getItem('target_job')` 的优先级顺序依次降级读取（每一级均为非 null 且非空字符串时才采用），将第一个非空值赋给对应的目标岗位响应式变量，所有来源均为空时赋值为空字符串 `''`。

4. WHEN `ResumeDiagnosis` 读取岗位描述时，THE `ResumeDiagnosis` SHALL 按照 `UserStore.jobDescription` → `localStorage.getItem('job_description')` → `localStorage.getItem('current_interview_jd')` 的优先级顺序依次降级读取（每一级均为非 null 且非空字符串时才采用），将第一个非空值赋给对应的岗位描述响应式变量，所有来源均为空时赋值为空字符串 `''`。

5. WHEN `PremiumInterview` 向后端发起面试请求时，THE `PremiumInterview` SHALL 在请求体中同时包含 `resume_text`、`target_role`、`jd_text` 三个字段，其值分别来自上述降级读取逻辑的结果（字段值为空字符串时请求仍正常发出）。

6. IF `localStorage` 中所有目标岗位相关键名均不存在或值为空，THEN THE `PremiumInterview` SHALL 将 `targetRole.value` 设为空字符串 `''`，不抛出异常，不阻断面试初始化流程。

7. IF `localStorage` 中所有岗位描述相关键名均不存在或值为空，THEN THE `PremiumInterview` SHALL 将 `interviewJd.value` 设为空字符串 `''`，不抛出异常，不阻断面试初始化流程。

---

### 需求 4：候选人档案栏展示求职意向

**用户故事**：作为面试候选人，我希望左侧候选人档案栏在简历内容上方优先展示我的求职意向，以便面试官（AI）和我自己能在面试过程中随时确认目标岗位信息。

#### 验收标准

1. WHEN `PremiumInterview` 渲染左侧候选人档案栏时，THE `PremiumInterview` SHALL 在简历内容展示块的上方新增一个求职意向展示块，该块包含标签文字"求职意向"和 `targetRole.value` 的值，且该块在 DOM 中的位置位于简历内容展示块之前。

2. WHILE `targetRole.value` 为长度大于 0 的非空字符串时，THE `PremiumInterview` SHALL 渲染求职意向展示块，使其在候选人档案栏中占据独立的视觉区域，不与简历内容合并显示。

3. IF `targetRole.value` 为空字符串、`null` 或 `undefined`，THEN THE `PremiumInterview` SHALL 不渲染求职意向展示块，不产生空白占位区域，不在控制台产生渲染相关错误。

4. THE `PremiumInterview` SHALL 使用与现有档案栏风格一致的 Dark Cyberpunk + Glassmorphism 样式渲染求职意向展示块，包含与当前主题色（`themeConfig`）匹配的边框颜色类和文字颜色类，不使用内联硬编码颜色值。

5. WHEN `targetRole.value` 在运行时从空字符串变为长度大于 0 的非空字符串时，THE `PremiumInterview` SHALL 响应式地渲染求职意向展示块，无需页面刷新。

6. WHEN `targetRole.value` 在运行时从长度大于 0 的非空字符串变为空字符串时，THE `PremiumInterview` SHALL 响应式地移除求职意向展示块，不在 DOM 中留下空节点或空白间距，不在控制台产生错误。
