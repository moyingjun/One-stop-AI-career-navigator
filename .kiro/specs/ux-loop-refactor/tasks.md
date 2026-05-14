# Implementation Plan: 核心业务组件扩容与交互体验(UX)闭环重构

## Overview

本实现计划围绕"做减法"的产品理念，分六个阶段完成核心业务组件扩容与 UX 闭环重构：废弃冗余页面、HistoryArchive 状态过滤重构、SetupModal 多维扩容、userStore 扩展、Dashboard 雷达图动态化、Agent 对话恢复闭环。所有任务基于 Vue 3 Composition API + Pinia + Vue Router 技术栈，使用 JavaScript 实现。

## Tasks

- [x] 1. 废弃冗余页面与入口
  - [x] 1.1 删除 `frontend/src/SavedChats.vue` 文件
    - 彻底移除该组件文件
    - _Requirements: 1.2_
  - [x] 1.2 在 `frontend/src/router/index.js` 中移除 `SavedChats` 组件的 import 语句和独立路由定义，替换为重定向规则 `{ path: '/saved-chats', redirect: '/history-archive' }`
    - 确保旧路由兼容性
    - _Requirements: 1.3, 1.4_
  - [x] 1.3 在 `frontend/src/Dashboard.vue` 左侧菜单 `menuItems` 数组中移除"保存的对话"项
    - _Requirements: 1.1_
  - [x] 1.4 在 `frontend/src/Dashboard.vue` 的 `handleSidebarItemClick` 函数中移除"保存的对话"相关的路由跳转逻辑
    - _Requirements: 1.1_

- [x] 2. HistoryArchive 状态过滤 UI 重构
  - [x] 2.1 在 `frontend/src/HistoryArchive.vue` 中导入 `vAutoAnimate` 指令（从 `@formkit/auto-animate/vue`），新增 `filterSaved` ref（'all' | 'saved'），默认值为 'all'
    - _Requirements: 2.1_
  - [x] 2.2 修改 `filteredRecords` computed 属性，在现有类型过滤和搜索过滤之前增加 `is_saved` 过滤逻辑
    - 收藏过滤与类型过滤/搜索过滤叠加生效（AND 逻辑）
    - _Requirements: 2.2, 2.5_
  - [x] 2.3 在页面顶部过滤区域（搜索框旁）新增 Segmented Control UI，包含"全部记录"和"🌟 仅看收藏"两个按钮，使用 Purple 主色调 + Cyberpunk Glow 激活态样式
    - _Requirements: 2.1, 2.4_
  - [x] 2.4 为历史记录卡片列表容器添加 `v-auto-animate` 指令，实现过滤切换时卡片的平滑消失/补齐动画
    - _Requirements: 2.2, 2.3_
  - [x] 2.5 处理过滤后空状态：当 filteredRecords 为空时，根据当前 filterSaved 状态显示不同的空状态文案（"暂无历史记录" / "暂无收藏记录"）
    - _Requirements: 2.6_
  - [x] 2.6 Write property test for HistoryArchive 收藏过滤
    - **Property 4: 对任意 historyRecords 数组和 filterSaved='saved'，filteredRecords 中每条记录的 is_saved 为 truthy**
    - **Validates: Requirements 2.2, 2.5**

- [x] 3. Checkpoint - 确保废弃页面与过滤重构完成
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. SetupModal 多维扩容（Tabbed UI）
  - [x] 4.1 在 `frontend/src/components/SetupModal.vue` 中新增 `activeTab` ref（'job' | 'education'），默认 'job'；新增求职模式字段 ref：`targetJob`、`jobDescription`，以及对应的 error ref
    - _Requirements: 3.1, 3.2_
  - [x] 4.2 新增升学模式字段 ref：`examType`、`estimatedScore`、`targetSchool`，以及 `examTypeOptions` 常量数组（专插本/普通高考/考研/考公/其他）
    - _Requirements: 3.3_
  - [x] 4.3 在模板中姓名+简历区域下方添加 Tab 切换 UI（两个按钮：求职模式/升学模式），使用暗黑赛博朋克毛玻璃风格
    - _Requirements: 3.1, 3.6_
  - [x] 4.4 在模板中根据 `activeTab` 条件渲染对应字段组：求职模式显示 Input + Textarea；升学模式显示 Select + Input + Input
    - _Requirements: 3.2, 3.3_
  - [x] 4.5 修改 `handleSubmit` 函数：在原有姓名+简历验证后，增加模式特定字段的验证和 localStorage 写入逻辑
    - _Requirements: 3.5, 3.7_
  - [x] 4.6 在 `onMounted` 中从 localStorage 预填充新增字段（target_job、job_description、exam_type、estimated_score、target_school、active_mode）
    - _Requirements: 3.4, 3.5_
  - [x] 4.7 Write property test for SetupModal 姓名截断
    - **Property 3: 对任意 candidateName 字符串，经 trim().slice(0, 50) 后长度 ≤ 50**
    - **Validates: Requirements 3.7**

- [x] 5. userStore 扩展
  - [x] 5.1 在 `frontend/src/stores/userStore.js` 的 state 中新增字段：`resumeText`、`targetJob`、`jobDescription`、`activeMode`、`examType`、`estimatedScore`、`targetSchool`
    - _Requirements: 3.5, 4.2_
  - [x] 5.2 将 `radarData.values` 默认值从 `[78, 65, 82, 90, 72, 68]` 改为 `[0, 0, 0, 0, 0, 0]`
    - _Requirements: 4.1_
  - [x] 5.3 新增 action `updateUserProfile(payload)`：接收 payload 对象，更新所有用户画像字段
    - _Requirements: 3.5_
  - [x] 5.4 新增 action `updateRadarData(scores)`：接收 scores 对象，映射到 values 数组，每项 clamp 到 [0, 100]
    - _Requirements: 4.2, 4.3_
  - [x] 5.5 新增 action `resetRadarData()`：将 values 重置为 `[0, 0, 0, 0, 0, 0]`
    - _Requirements: 4.1_
  - [x] 5.6 新增 action `loadFromStorage()`：从 localStorage 读取所有用户画像字段并同步到 state
    - _Requirements: 3.5_
  - [x] 5.7 Write property test for updateRadarData
    - **Property 1: 对任意合法 scores 对象，updateRadarData(scores) 后 values 数组长度恒为 6 且每项 ∈ [0, 100]**
    - **Validates: Requirements 4.2, 4.3**

- [x] 6. Checkpoint - 确保 SetupModal 和 userStore 扩展完成
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Dashboard 雷达图动态化与入口修正
  - [x] 7.1 在 `frontend/src/Dashboard.vue` 的 `onMounted` 中新增 `loadLatestRadarData()` 调用，从 API 获取最新简历诊断评估的 scores 并调用 `userStore.updateRadarData()`
    - _Requirements: 4.2, 4.5_
  - [x] 7.2 将 Bento 面板右上角"历史档案 >"文案更名为"数据面板设置 >"或移除该链接元素
    - _Requirements: 4.4_
  - [x] 7.3 移除模板中雷达图下方进度条的硬编码百分比值（如 `style="width: 78%"`），改为从 `radarData.values` 动态绑定
    - _Requirements: 4.2_

- [x] 8. Agent 对话恢复闭环
  - [x] 8.1 在 `frontend/src/HistoryArchive.vue` 的 `goToRecord` 函数中新增对 `agent_*` 和 `general_chat` category 的处理：`router.push('/dashboard?chat_id=' + record.id)`
    - _Requirements: 5.1, 5.6_
  - [x] 8.2 在 `frontend/src/Dashboard.vue` 中导入 `useRoute`，新增 `watch(() => route.query.chat_id, ...)` 监听器（immediate: true）
    - _Requirements: 5.2_
  - [x] 8.3 实现 `restoreChatContext(chatId)` 异步函数：调用 `GET /api/history/{chatId}` 获取记录，解析 chat_history JSON，赋值给 chatMessages，设置 currentRecordId
    - _Requirements: 5.2, 5.3_
  - [x] 8.4 在 `restoreChatContext` 中实现降级逻辑：当 chat_history 为空时，从 user_input + ai_result 构建最小上下文
    - _Requirements: 5.4, 5.7_
  - [x] 8.5 确保恢复对话后，用户发送新消息时 `sendGeneralChatMessage` 的 history payload 包含已恢复的历史消息上下文
    - _Requirements: 5.5_
  - [x] 8.6 Write property test for restoreChatContext 消息角色
    - **Property 2: 对任意 chatHistory 数组，restoreChatContext 解析后每条消息的 role 仅为 'user' 或 'ai'**
    - **Validates: Requirements 5.3**

- [x] 9. Final checkpoint - 确保所有功能集成完成
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document
- 所有 UI 组件严格遵循现有"暗黑赛博朋克 + 毛玻璃"设计风格
- 使用 fast-check 库进行 property-based testing
- 无需新增任何 npm 依赖，所有功能基于现有技术栈实现

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "5.1", "5.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "5.3", "5.4", "5.5", "5.6"] },
    { "id": 2, "tasks": ["2.1", "4.1", "4.2", "5.7"] },
    { "id": 3, "tasks": ["2.2", "2.3", "4.3", "4.4"] },
    { "id": 4, "tasks": ["2.4", "2.5", "4.5", "4.6"] },
    { "id": 5, "tasks": ["2.6", "4.7", "7.1", "7.2", "7.3"] },
    { "id": 6, "tasks": ["8.1", "8.2"] },
    { "id": 7, "tasks": ["8.3", "8.4"] },
    { "id": 8, "tasks": ["8.5", "8.6"] }
  ]
}
```
