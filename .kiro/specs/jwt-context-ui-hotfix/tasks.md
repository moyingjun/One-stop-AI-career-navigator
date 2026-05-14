# Implementation Plan: jwt-context-ui-hotfix

## Overview

针对多租户架构升级后出现的四个紧急前端问题，按独立 Task 逐一修复。每个 Task 对应一个 Bug，互不依赖（Task 4 依赖 Task 3 的上下文读取逻辑，其余完全独立）。

## Tasks

- [ ] 1. 修复 PremiumInterview.vue 中裸露的 Unix 时间戳
  - 定位 `sendMessage` 函数中推入占位 AI 消息的代码行：`const aiMsg = { role: 'ai', content: '', timestamp: Date.now(), isNew: true }`
  - 将 `timestamp: Date.now()` 替换为 `timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })`
  - 与 `addMessage` 函数的 timestamp 格式保持完全一致
  - **验证**：发送消息后，AI 回复气泡右下角显示 `HH:mm` 格式（如 `17:22`），不再显示毫秒整数
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

- [ ] 2. 在 llm_service.js 中添加本地 getAuthHeaders 并补全所有 fetch 请求头
  - 在文件顶部添加本地 `getAuthHeaders` 工具函数（直接读 localStorage，不 import Vue/Pinia）：`function getAuthHeaders() { const token = localStorage.getItem('token'); return token ? { Authorization: \`Bearer \${token}\` } : {} }`
  - 修改 `callAgent` 函数的 `fetch` 调用，在 `headers` 中合并 `getAuthHeaders()`：`headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }`
  - 修改 `streamInterviewChat` 函数的 `fetch` 调用，在 `headers` 中合并 `getAuthHeaders()`
  - **涉及文件**：`frontend/src/services/llm_service.js`

- [ ] 3. 在 PremiumInterview.vue 中补全所有 fetch 请求的 JWT Auth 头
  - 在 `<script setup>` 顶部导入 `getAuthHeaders`：`import { getAuthHeaders } from '@/services/authService.js'`
  - 修复 `initInterview` 中恢复历史记录的 `fetch` 调用，添加 Auth 头
  - 修复 `startInterviewWithDifficulty` 中初始化面试的 `fetch` 调用，添加 Auth 头
  - 修复 `endInterview` 中调用 `/interview/evaluate` 的 `fetch` 调用，添加 Auth 头
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

- [ ] 4. 在 PremiumInterview.vue 的 endInterview 中新增保存历史记录调用
  - 在 `endInterview` 评估成功分支（`resData.success && resData.data` 为真，且 `radarScores` 已更新后）新增 `POST /api/history` 调用
  - 请求体包含：`category`（值为 `interview_${interviewDifficulty.value}`）、`user_input`（面试摘要）、`ai_result`（`mentorComment.value`）、`scores`（`JSON.stringify(radarScores.value)`）、`chat_history`（`JSON.stringify(messages.value.map(m => ({ role: m.role, content: m.content })))`）、`extra_data`（`JSON.stringify({ resume_text, target_role, jd_text, difficulty })`）
  - 该调用需携带 Auth 头；失败时仅 `console.error` 不阻断 UI 流程（不影响雷达图展示）
  - **验证**：完成一次完整面试后，刷新 Dashboard，历史记录列表中出现本次面试记录
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

- [ ] 5. 在 ResumeDiagnosis.vue 中补全 fetch 请求的 JWT Auth 头
  - 在 `<script setup>` 顶部导入 `getAuthHeaders`
  - 修复 `initResume` 中恢复历史记录的 `fetch` 调用，添加 Auth 头
  - 修复 `startDiagnosis` 中调用 `/resume/diagnose` 的 `fetch` 调用，添加 Auth 头
  - **涉及文件**：`frontend/src/ResumeDiagnosis.vue`

- [ ] 6. 在 Dashboard.vue 中补全所有遗漏的 JWT Auth 头
  - 确认 `getAuthHeaders` 已在文件顶部导入（当前已导入，检查即可）
  - 修复 `loadHistory` 中的 `fetch` 调用，添加 Auth 头
  - 修复 `loadLatestRadarData` 中的 `fetch` 调用，添加 Auth 头（当前仅 `fetchPinnedRadarData` 有，`loadLatestRadarData` 遗漏）
  - 修复 `toggleSaveRecord` 中的 `fetch` 调用，添加 Auth 头
  - 修复 `deleteHistoryRecord` 中的 `fetch` 调用，添加 Auth 头
  - 修复 `sendGeneralChatMessage` 中的 `fetch` 调用，添加 Auth 头
  - 修复 `saveAndStartNew` 中的 `fetch` 调用，添加 Auth 头
  - **验证**：打开 DevTools → Network，确认所有 `/api/*` 请求携带 `Authorization: Bearer <token>`；Dashboard Bento 看板历史记录和雷达图正常加载
  - **涉及文件**：`frontend/src/Dashboard.vue`

- [ ] 7. 修复 PremiumInterview.vue 的上下文读取逻辑（target_role / jd_text）
  - 在 `<script setup>` 顶部导入 `useUserStore` 并初始化：`import { useUserStore } from '@/stores/userStore'; const userStore = useUserStore()`
  - 修改 `initInterview` 函数中 `targetRole.value` 的赋值，改为优先读 `userStore.targetJob`，降级兼容 `localStorage.getItem('target_role')` → `localStorage.getItem('target_job')`
  - 修改 `initInterview` 函数中 `resumeText.value` 的赋值，改为优先读 `userStore.resumeText`，降级 `localStorage.getItem('resume_text')`
  - 修改 `initInterview` 函数中 `interviewJd.value` 的赋值，改为优先读 `userStore.jobDescription`，降级兼容 `localStorage.getItem('job_description')` → `localStorage.getItem('current_interview_jd')` → `localStorage.getItem('jd_content')`
  - 确认 `startInterviewWithDifficulty` 和 `sendMessage` 的请求体中，`resume_text`、`jd_text` 字段均使用已正确赋值的响应式变量
  - **验证**：在 SetupModal 填写目标岗位"Java后端开发工程师"和 JD 后进入面试，AI 第一条问题应与 Java 后端岗位相关
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

- [ ] 8. 修复 ResumeDiagnosis.vue 的上下文读取逻辑（target_role / jd_text）
  - 在 `<script setup>` 顶部导入 `useUserStore` 并初始化
  - 修改 `initResume` 函数，补全 `jdText.value` 的读取逻辑（当前完全缺失），使用与 Task 7 相同的多键名降级策略：优先 `userStore.jobDescription`，降级 `localStorage.getItem('job_description')` → `localStorage.getItem('current_interview_jd')` → `localStorage.getItem('jd_content')`
  - 修改 `initResume` 中 `targetRole.value` 的读取，兼容 `target_job` 键名：优先 `userStore.targetJob`，降级 `localStorage.getItem('target_role')` → `localStorage.getItem('target_job')`
  - **验证**：进入简历诊断页面，"目标岗位"和"岗位描述"输入框已预填充 SetupModal 中填写的内容
  - **涉及文件**：`frontend/src/ResumeDiagnosis.vue`

- [ ] 9. 在 PremiumInterview.vue 左侧档案栏新增求职意向优先展示块
  - 依赖 Task 7 完成（确保 `targetRole.value` 已按优先级正确赋值）
  - 在左侧候选人档案区模板中，在简历内容展示块（`animate-scan` div）**上方**新增求职意向展示块：使用 `v-if="targetRole"` 控制显隐，使用 `themeConfig.borderLight` 和 `themeConfig.text` 保持主题一致性，展示"求职意向"标签和 `targetRole` 值
  - **验证**：在 SetupModal 填写目标岗位后进入面试，左侧档案栏顶部显示"求职意向：<填写的岗位>"；若未填写，该块不渲染
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

## Task Dependency Graph

```json
{
  "waves": [
    [1, 2, 3, 5, 6, 7, 8],
    [4, 9]
  ]
}
```

## Notes

- 严禁运行 `vue-tsc` 或 `vite build` 等打包命令
- `llm_service.js` 不能 import Vue/Pinia，使用本地 `getAuthHeaders` 函数直接读 `localStorage`
- 所有 `fetch` 调用统一使用展开运算符合并 Auth 头：`headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }`
- FormData 请求（文件上传）不设 `Content-Type`，只合并 Auth 头：`headers: { ...getAuthHeaders() }`
- 历史记录保存调用失败时只 `console.error`，不阻断 UI 流程
- Task 4 的保存调用放在 `setTimeout(() => { showMatrixModal.value = false; showResultModal.value = true }, 500)` 之前，确保数据已写入后再展示结果弹窗
