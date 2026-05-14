# Implementation Plan: UX State Datasource Readability

## Overview

本实现计划将设计文档中的三大核心重构拆解为可增量执行的编码任务：(1) UserStore 扩展与 localStorage 双向同步；(2) SetupModal 升学模式字段持久化修复；(3) DataSourceModal 新组件开发；(4) Dashboard 入口解耦与自动加载逻辑升级；(5) Sidebar 用户模式信息展示升级；(6) 全局字号与对比度修复。所有任务均基于 Vue 3 + Pinia + Tailwind CSS 4 技术栈，遵循 Pinia Store 作为单一数据源的架构原则。

## Tasks

- [x] 1. 扩展 UserStore 并完善 localStorage 双向同步
  - [x] 1.1 在 `frontend/src/stores/userStore.js` 中添加 `activeDataSourceId` 字段到 state，并确认 `examType`、`estimatedScore`、`targetSchool` 字段已存在
    - 在 state 中添加 `activeDataSourceId: null`（number | null）
    - 确认现有 `examType`、`estimatedScore`、`targetSchool` 字段已在 state 中（当前代码已有，无需重复添加）
    - _Requirements: 3.1_

  - [x] 1.2 修复 `updateUserProfile()` action，确保调用时将所有字段同步写入 localStorage
    - 在 `updateUserProfile()` 中添加 localStorage.setItem 调用，写入 `candidate_name`、`resume_text`、`active_mode`、`target_job`、`job_description`、`exam_type`、`estimated_score`、`target_school`
    - 用 try-catch 包裹所有 localStorage 写入，失败时静默处理
    - _Requirements: 3.2, 10.2_

  - [x] 1.3 为 `updateUserProfile()` 的 localStorage 同步逻辑编写属性测试（Property 3）
    - **Property 3: Store-localStorage 双向同步（Store-LocalStorage Sync Round-Trip）**
    - **Validates: Requirements 3.2, 10.1, 10.2, 10.3, 10.4**
    - 使用 vitest + fast-check，对任意合法 formData 调用 `updateUserProfile()` 后，`loadFromStorage()` 应恢复相同字段值

- [x] 2. 修复 SetupModal 升学模式字段持久化
  - [x] 2.1 修复 `frontend/src/components/SetupModal.vue` 中的 `handleSubmit()` 方法
    - 在提交时写入 `localStorage.setItem('active_mode', activeTab.value)`
    - 当 `activeTab === 'education'` 时写入 `exam_type`、`estimated_score`、`target_school`
    - 当 `activeTab === 'job'` 时写入 `target_job`、`job_description`
    - 所有 localStorage 写入用 try-catch 包裹，失败时不抛出异常
    - 调用 `userStore.updateUserProfile()` 同步所有字段到 Store
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 2.2 修复 SetupModal 的预填充逻辑（`onMounted` 或 `watch(visible)`）
    - 弹窗打开时从 localStorage 读取 `active_mode`，设置 `activeTab`
    - 读取 `exam_type`、`estimated_score`、`target_school` 预填升学字段
    - 读取 `target_job`、`job_description` 预填求职字段
    - 缺失 key 时对应字段显示为空，不报错
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.3 为 `persistUserProfile()` 逻辑编写属性测试（Property 1）
    - **Property 1: 持久化完整性（Persistence Round-Trip）**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**
    - 使用 vitest + fast-check，对任意升学模式 formData，提交后 localStorage 和 UserStore 中字段值应完全一致

- [x] 3. 实现有效数据源筛选工具函数
  - [x] 3.1 在 `frontend/src/utils/` 目录下新建 `dataSourceUtils.js`，实现 `hasValidScores(record)` 和 `filterValidDataSources(records)` 函数
    - `hasValidScores(record)`：安全解析 scores（支持 JSON 字符串），返回 true 当且仅当至少一个维度值 > 0
    - `filterValidDataSources(records)`：返回满足 `hasValidScores` 的子集，不修改原数组
    - 对 null、undefined、空对象、解析失败的 scores 均返回 false
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 3.2 为 `hasValidScores()` 编写属性测试（Property 8）
    - **Property 8: hasValidScores 正确性（hasValidScores Correctness）**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    - 使用 vitest + fast-check，对含至少一个正数值的 scores 对象应返回 true；对 null/空对象/全零/不可解析字符串应返回 false

  - [x] 3.3 为 `filterValidDataSources()` 编写属性测试（Property 6 & 7）
    - **Property 6: 有效数据源筛选（Valid DataSource Filtering）**
    - **Property 7: 筛选不修改原数组（Filter Immutability）**
    - **Validates: Requirements 8.6, 8.7**
    - 使用 vitest + fast-check，验证返回子集中每条记录均满足 `hasValidScores === true`，且原数组长度和引用不变

- [x] 4. 新建 DataSourceModal 组件
  - [x] 4.1 在 `frontend/src/components/` 下新建 `DataSourceModal.vue`，实现组件骨架与 props/emits 定义
    - Props: `visible` (Boolean)、`historyRecords` (Array)
    - Emits: `close`、`select`
    - 引入 `hasValidScores`、`filterValidDataSources` 工具函数
    - 用 `computed` 计算 `filteredRecords`
    - 赛博朋克深色毛玻璃样式（与 Dashboard 风格一致），最小字号 text-xs
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 11.3, 12.3_

  - [x] 4.2 实现 DataSourceModal 的记录列表渲染与空状态
    - 遍历 `filteredRecords`，展示每条记录的类别标签（使用 `getCategoryLabel`）、创建时间戳、`user_input` 摘要
    - 空状态：无有效记录时展示提示文案"暂无可用数据源"
    - scores JSON 解析失败的记录静默排除，不显示错误
    - 所有文字颜色使用 text-gray-400 或更亮，不使用 text-gray-600 及更深
    - _Requirements: 5.4, 5.5, 5.8, 5.9, 13.1, 13.2, 13.3_

  - [x] 4.3 实现 `selectDataSource(record)` 方法与关闭逻辑
    - 选中记录时：解析 scores → 调用 `userStore.updateRadarData(scores)` → 设置 `userStore.activeDataSourceId = record.id` → emit('select', record)
    - 关闭按钮和背景点击均 emit('close')
    - _Requirements: 5.6, 5.7_

- [x] 5. Checkpoint — 确保工具函数与 DataSourceModal 核心逻辑正确
  - 确保所有测试通过，向用户确认是否有疑问后继续。

- [x] 6. 升级 Dashboard.vue：入口解耦与自动加载
  - [x] 6.1 在 `Dashboard.vue` 中添加 `showDataSourceModal` ref，修改"数据面板设置 >"按钮的点击处理器
    - 添加 `const showDataSourceModal = ref(false)`
    - 将"数据面板设置 >"按钮的 `@click` 改为 `showDataSourceModal = true`，移除对 `showSetupModal` 的赋值
    - 在 template 中添加 `<DataSourceModal>` 组件，绑定 `:visible`、`:historyRecords`、`@close`、`@select`
    - `@select` 和 `@close` 均将 `showDataSourceModal` 设为 false
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 6.2 升级 `loadLatestRadarData()` 函数，使用 `has_scores=true` 参数并更新 `activeDataSourceId`
    - 将 API 请求改为 `GET /api/history?has_scores=true&limit=1`
    - 收到有效记录时调用 `userStore.updateRadarData(scores)` 并设置 `userStore.activeDataSourceId = records[0].id`
    - 无有效记录时调用 `userStore.resetRadarData()`
    - 请求失败时保持当前 radarData 状态不变，不向用户展示错误
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 6.3 在 `onMounted()` 中调用 `userStore.loadFromStorage()` 恢复用户画像状态
    - 在 `onMounted` 最前面调用 `userStore.loadFromStorage()`，确保 Sidebar 等组件初始化时能读到正确的 Store 状态
    - _Requirements: 3.2, 10.1_

- [x] 7. 升级 Sidebar 用户模式信息展示
  - [x] 7.1 修改 `Dashboard.vue` 中 Sidebar 的全局资产区域，从 userStore 响应式读取并渲染模式信息
    - 添加 `examTypeLabel` computed，映射 examType key 到中文标签（zhuanchaben→专插本、gaokao→普通高考、kaoyan→考研、kaogong→考公、other→其他），未知值返回'未设置'
    - 升学模式（`userStore.activeMode === 'education'`）：第一行展示 examType 高亮标签 badge，第二行展示"分数/排位: {{ estimatedScore }}"
    - 求职模式（`userStore.activeMode === 'job'`）：展示 targetJob，resumeText 非空时展示就绪状态指示器
    - 所有数据从 userStore 读取，不直接读 localStorage
    - _Requirements: 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 7.2 为 Sidebar examTypeLabel 映射编写属性测试（Property 5）
    - **Property 5: 未知考试类型回退（Unknown examType Fallback）**
    - **Validates: Requirements 4.6**
    - 使用 vitest + fast-check，对任意非五个合法 key 的字符串，examTypeLabel 应返回'未设置'

- [x] 8. 全局字号下限升级与对比度修复
  - [x] 8.1 扫描并替换 `Dashboard.vue` 中所有 `text-[9px]`、`text-[10px]`、`text-[11px]` 为 `text-xs`
    - 使用 grep 定位所有违规字号类名，逐一替换为 text-xs
    - 检查替换后是否有布局溢出，必要时添加 `truncate` 或 `min-w-0`
    - _Requirements: 11.1, 11.5, 11.6_

  - [x] 8.2 扫描并替换 `SetupModal.vue` 中所有违规字号类名与深色背景灰色文字
    - 替换 `text-[9px]`、`text-[10px]`、`text-[11px]` 为 `text-xs`
    - 将深色背景上的 `text-gray-600`、`text-gray-700`、`text-gray-800`、`text-gray-900` 替换为 `text-gray-400` 或 `text-gray-500`
    - _Requirements: 11.2, 12.2_

  - [x] 8.3 确保 `DataSourceModal.vue` 全程使用 text-xs 最小字号，深色背景文字使用 text-gray-400/500
    - 新建组件时直接遵循规范，不使用任何违规字号类名
    - 主要可读文字使用 text-gray-400 或更亮，次要装饰文字最深使用 text-gray-500
    - _Requirements: 11.3, 12.3_

  - [x] 8.4 扫描并修复 `Dashboard.vue` 中深色背景上的灰色文字对比度问题
    - 将 `text-gray-600`、`text-gray-700`、`text-gray-800`、`text-gray-900` 替换为 `text-gray-400` 或 `text-gray-500`
    - 主要可读内容使用 text-gray-400 或更亮
    - _Requirements: 12.1_

- [x] 9. Final Checkpoint — 确保所有测试通过
  - 确保所有测试通过，向用户确认是否有疑问后继续。

## Notes

- 标有 `*` 的子任务为可选测试任务，可跳过以加快 MVP 交付
- 每个任务均引用具体需求条款，确保可追溯性
- 属性测试使用 vitest + fast-check，测试文件建议放在 `frontend/src/__tests__/` 目录下
- UserStore 中 `activeDataSourceId` 字段不需要持久化到 localStorage（仅会话级状态）
- DataSourceModal 的历史记录由 Dashboard 通过 props 传入，组件本身不发起 API 请求
- 字号替换时注意保持赛博朋克深色毛玻璃视觉风格，避免布局溢出

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.2", "3.2", "3.3"] },
    { "id": 2, "tasks": ["1.3", "2.3", "4.1"] },
    { "id": 3, "tasks": ["4.2", "4.3"] },
    { "id": 4, "tasks": ["6.1", "6.2", "6.3", "7.1", "8.1", "8.2", "8.3", "8.4"] },
    { "id": 5, "tasks": ["7.2"] }
  ]
}
```
