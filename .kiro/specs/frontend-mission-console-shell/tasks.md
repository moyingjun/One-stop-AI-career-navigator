# Implementation Plan: Frontend Mission Console Shell

> Convert the feature design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Make sure that each prompt builds on the previous prompts, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.

## Overview

本特性是一次纯前端 UI 重构：把 `ResumeDiagnosis.vue` / `CareerPlanning.vue` / `PremiumInterview.vue` 三页统一收敛到「AI 任务控制台骨架」。实现顺序遵循「先底座、后业务」：

1. 先落地共享降级模块 `uiFallbacks.js`
2. 再落地四个新组件 `FeaturePageShell.vue` / `MetricCard.vue` / `ActionDock.vue` / `SidebarEducationPlaceholder.vue`，每个组件都配套属性测试
3. 在三页中按 Resume → Career → Interview 顺序逐页重构，每页配套「请求 / SSE 序列 / reply 累加 / error 透传」四合一的等价性回归属性测试
4. 最后通过「渲染节点不丢失」spec 与端到端验收清单完成集成

**测试纪律**：

- 全部测试使用 Vitest + fast-check（`frontend/package.json` 已装），运行命令 `npm run test`（即 `vitest --run`）
- 测试文件统一放在 `frontend/src/__tests__/` 下，命名 `featureMissionConsoleShell.<topic>.property.test.js` / `.spec.js`
- 每个属性测试用例顶部必须加注释 `// Feature: frontend-mission-console-shell, Property N: <property text>`，与项目既有 PBT 命名风格一致
- 属性测试默认 `numRuns: 100`，生成器较重的可降至 50，不得更低
- **严禁**任务执行过程中运行 `npm run build` / `vite build` / `tsc` / `vue-tsc`（Requirement 7.12 + steering `tech.md` 红线）

**受保护文件清单（Requirement 7，本特性下任务一律不得修改）**：

- `Router/**`、`Service/**`（含 `Service/Games/Avalon/**`）
- `frontend/src/router/index.js`
- `frontend/src/services/llm_service.js`
- `frontend/src/Dashboard.vue`
- `frontend/src/components/CyberGlassCard.vue`、`BaseModal.vue`、`CyberRadarChart.vue`
- `frontend/src/AvalonGame.vue`、`frontend/src/stores/gameStore.js`

## Tasks

- [x] 1. 构建共享降级模块 `uiFallbacks.js`
  - [x] 1.1 创建 `frontend/src/utils/uiFallbacks.js`，导出 `resolveLoader()`、`resolveToast()`、`showToast(message, options)`
    - 实现「先 `import('@/components/Toast.vue')` / `import('@/components/StreamingLoader.vue')`，失败则降级到内联 `InlineToastFallback` / `InlineLoaderFallback`」的解析顺序
    - `InlineToastFallback`：3000ms 自动消失，`success` 用 cyan 色调 class、`error` 用 red 色调 class，命令式挂载到 `document.body`
    - `InlineLoaderFallback`：使用 Tailwind 4 + 既有色调实现毛玻璃卡片 + 流光动效，禁止引入新依赖
    - 不在本模块内 `import` `services/llm_service.js`、`fetch`、`EventSource`、`axios`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ]* 1.2 编写属性测试：降级模块解析顺序优先级
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.uiFallbacksResolve.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 12: 降级模块解析顺序优先级`
    - 用 `vi.doMock('@/components/Toast.vue', ...)` / `vi.doMock('@/components/StreamingLoader.vue', ...)` 控制是否可解析
    - **Property 12: 降级模块解析顺序优先级**
    - **Validates: Requirements 8.1, 8.2, 8.4, 8.6, 8.7**
    - _Requirements: 8.1, 8.2, 8.4, 8.6, 8.7_

  - [ ]* 1.3 编写属性测试：Toast Fallback 自动消失 + 语义色调
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.toastAutoDismiss.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 13: Toast Fallback 自动消失 + 语义色调`
    - 使用 `vi.useFakeTimers()` + `advanceTimersByTime(duration)` 推进虚拟时间
    - 生成器：`message ∈ NonEmptyString`，`type ∈ {'success', 'error'}`，`duration ∈ [1000, 10000]`
    - **Property 13: Toast Fallback 自动消失 + 语义色调**
    - **Validates: Requirements 8.5**
    - _Requirements: 8.5_

- [x] 2. 实现 `FeaturePageShell.vue`（仅布局 + 具名插槽，无业务）
  - [x] 2.1 创建 `frontend/src/components/FeaturePageShell.vue`
    - 使用 `<script setup>` 语法糖
    - Props：`title: String (required)`、`subtitle?: String`、`stageBadges?: StageBadge[]`（最多 5 项，超出截断）、`variant?: 'default'|'cyan'|'purple'|'pink'|'emerald'`
    - 具名插槽：`hero` / `control` / `result` / `result-empty`；未提供 `hero` 时回退到由 props 渲染的默认 Hero
    - DOM 顺序固定为 Hero → Control → Result，Control / Result 区域使用 `CyberGlassCard` 作为容器（read-only 复用，不修改 `CyberGlassCard.vue`）
    - **严格禁止**在本组件内 `import` `services/llm_service.js`、`fetch`、`EventSource`、`axios`，禁止出现 `/api/...` 字符串、禁止声明 `onMessage` / `onError` / `onDone` 回调
    - 视觉变量与 `Dashboard.vue` 同源（毛玻璃 `backdrop-blur(16px)`、圆角 16px、conic-gradient 边框流光）
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.1, 4.4, 4.7, 4.8, 4.9, 5.2, 5.3, 5.4, 5.6_

  - [ ]* 2.2 编写属性测试：Shell 三段结构幂等性
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.shellShape.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 1: Shell 三段结构幂等性`
    - 生成合法 props（`title` 非空、`stageBadges` 0..5 项）与三段任意 slot 内容，挂载后断言 DOM 中存在恰好一个 Hero、Control、Result 容器，且顺序固定
    - **Property 1: Shell 三段结构幂等性**
    - **Validates: Requirements 1.1, 1.6**
    - _Requirements: 1.1, 1.6_

  - [ ]* 2.3 编写属性测试：FeaturePageShell 三段 Slot 路由隔离
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.slotIsolation.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 2: FeaturePageShell 三段 Slot 路由隔离`
    - 生成三段互不相同的随机字符串 `(h, c, r)`，分别注入 `hero` / `control` / `result` slot，断言 `h` 仅出现在 Hero 容器、`c` 仅在 Control、`r` 仅在 Result
    - 本文件随后由任务 4.2 追加 `ActionDock` 的 slot 隔离断言；本任务先建立 FeaturePageShell 部分
    - **Property 2: FeaturePageShell 三段 Slot 路由隔离**
    - **Validates: Requirements 1.5**
    - _Requirements: 1.5_

  - [ ]* 2.4 编写属性测试：FeaturePageShell Prop 到 Hero DOM 渲染契约
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.propRendering.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 4: FeaturePageShell Prop 到 Hero DOM 的渲染契约`
    - 生成合法 `(title, subtitle, stageBadges)` 组合，挂载后断言 Hero 容器 `textContent` 包含 `title`、`subtitle`（若有）、所有 `stageBadges[i].label`
    - 本文件随后由任务 3.2 追加 `MetricCard` 的 prop 渲染断言；本任务先建立 FeaturePageShell 部分
    - **Property 4: FeaturePageShell Prop 到 Hero DOM 的渲染契约**
    - **Validates: Requirements 4.4, 3.1, 3.2, 3.3**
    - _Requirements: 4.4, 3.1, 3.2, 3.3_

  - [ ]* 2.5 编写 Lint 风格 spec：FeaturePageShell 作用域守卫
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.shellScopeGuard.spec.js`
    - 用 `node:fs` 读取 `frontend/src/components/FeaturePageShell.vue` 源文件文本，断言文本中**不包含**以下任一子串：
      - `from '@/services/llm_service'` / `from "@/services/llm_service"`
      - `services/llm_service` / `llm_service.js`
      - `fetch(` / `new EventSource` / `axios.`
      - `/api/`
      - `onMessage` / `onError` / `onDone`
    - 这是用户补充约束 b 的硬性强制：FeaturePageShell 不接业务 API，不处理请求，不解析 SSE
    - _Requirements: 2.8_

- [x] 3. 实现 `MetricCard.vue`
  - [x] 3.1 创建 `frontend/src/components/MetricCard.vue`
    - Props：`label: String (required)`、`value: Number|String (required)`、`unit?: String`、`trend?: 'up'|'down'|'flat'`、`tone?: 'default'|'cyan'|'purple'|'pink'|'emerald'`
    - 默认 slot 用于自定义图标 / 副文案
    - 内部**复用** `CyberGlassCard.vue`（不重新实现毛玻璃容器，Requirement 4.8）
    - 根元素根据 `trend` 取值带上 `trend-up` / `trend-down` / `trend-flat` class，方向标记色调分别为绿 / 红 / 灰
    - _Requirements: 4.2, 4.5, 4.7, 4.8, 4.9, 5.2, 5.4, 5.6_

  - [ ]* 3.2 追加属性测试：MetricCard Prop 到 DOM 渲染契约
    - 文件：复用任务 2.4 的 `frontend/src/__tests__/featureMissionConsoleShell.propRendering.property.test.js`，新增一个 `describe('MetricCard prop → DOM', ...)` 块
    - 顶部追加注释：`// Feature: frontend-mission-console-shell, Property 5: MetricCard Prop 到 DOM 的渲染契约`
    - 生成合法 `(label, value, unit, trend)`，挂载后断言：DOM 中可见 `label` 与 `value`；`unit` 存在时可见；`trend` 取定值时存在对应 class
    - **Property 5: MetricCard Prop 到 DOM 的渲染契约**
    - **Validates: Requirements 4.5**
    - _Requirements: 4.5_

- [x] 4. 实现 `ActionDock.vue`
  - [x] 4.1 创建 `frontend/src/components/ActionDock.vue`
    - Props：`align?: 'left'|'center'|'right'`（默认 `right`）、`sticky?: Boolean`（默认 `false`）
    - 具名插槽：`primary` / `secondary`，分别承载主操作（通常 1 个按钮）与次操作（可多个）
    - 内部**复用** `CyberGlassCard.vue`（Requirement 4.8）
    - `sticky` 为 `true` 时使用 `position: sticky; bottom: 0` 吸附页面底部
    - _Requirements: 4.3, 4.6, 4.7, 4.8, 4.9, 5.2, 5.4, 5.6_

  - [ ]* 4.2 追加属性测试：ActionDock 主次操作 Slot 路由隔离
    - 文件：复用任务 2.3 的 `frontend/src/__tests__/featureMissionConsoleShell.slotIsolation.property.test.js`，新增一个 `describe('ActionDock slot routing', ...)` 块
    - 顶部追加注释：`// Feature: frontend-mission-console-shell, Property 3: ActionDock 主次操作 Slot 路由隔离`
    - 生成两段互不相同的随机字符串 `(p, s)`，分别注入 `primary` / `secondary`，断言 `p` 仅出现在主操作容器、`s` 仅在次操作容器
    - **Property 3: ActionDock 主次操作 Slot 路由隔离**
    - **Validates: Requirements 4.6**
    - _Requirements: 4.6_

- [x] 5. 实现 `SidebarEducationPlaceholder.vue`
  - [x] 5.1 创建 `frontend/src/components/SidebarEducationPlaceholder.vue`
    - 渲染为 `<div role="button" aria-disabled="true" tabindex="-1">`，不响应点击与键盘激活（不绑定 `@click` 或绑定 `@click.prevent`）
    - 文案以**组件内部常量**写死：`'工程师正在玩命开发中，敬请期待！🚀'`，禁止从 props 传入以避免文案漂移
    - 鼠标悬停时通过 `title` 属性 + 同区域内联 tooltip 展示文案
    - 不向 Vue Router 注册任何新路由，不触发跳转
    - 视觉：`lucide-vue-next` 的 `GraduationCap` 图标 + emerald 色调，毛玻璃容器
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 5.3, 5.4_

  - [ ]* 5.2 编写属性测试：侧边栏升学占位不变性
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.sidebarPlaceholder.property.test.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 11: 侧边栏升学占位不变性`
    - 参数化「初次进入 / 重新挂载 / 切换页面后再挂载」三种序列，断言 `aria-disabled === 'true'`、可见文案恒为 `'工程师正在玩命开发中，敬请期待！🚀'`、点击事件被阻止
    - **Property 11: 侧边栏升学占位不变性**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 6. Checkpoint - 底座组件就绪
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. 重构 `ResumeDiagnosis.vue`（视觉重构 ≠ 业务重构）
  - [x] 7.1 改写 `frontend/src/ResumeDiagnosis.vue` 顶层 `<template>` 为 `<FeaturePageShell title="简历诊断" :stageBadges="[扫描, 诊断, 报告]" variant="purple">`
    - 文件上传 dropzone、目标岗位输入、JD 文本框 → `#control` slot
    - 流式 Markdown 报告与 `CyberRadarChart` 六维评分 → `#result` slot
    - 「触发诊断」按钮通过 `ActionDock` 聚合为 `#primary`
    - 在页面顶部 / 左侧渲染 `<SidebarEducationPlaceholder />`
    - Toast / Loader 引用统一改为 `import { showToast, resolveLoader } from '@/utils/uiFallbacks'`，**不**在本文件内重复实现降级（Requirement 8.8）
    - **严格不变**：既有 `fetch('/api/resume/diagnose')` + 行解析 SSE 处理逻辑、`onMeta` / `onMessage` / `onError` / `onDone` 回调、HTTP 端点、请求体字段、所有业务节点（报告标题、报告条目、雷达图容器）原样保留
    - **错误透传纪律**：`onError(message)` 收到的 `message` 直接渲染到错误展示区域 `textContent`，禁止额外添加任何前缀 / 后缀 / 模板包装文案（用户补充约束 a）
    - 不修改 `frontend/src/services/llm_service.js`、`router/index.js`、`Dashboard.vue`、`CyberGlassCard.vue`、`BaseModal.vue`、`CyberRadarChart.vue`
    - 不移动文件物理路径、不删除任何已有功能入口
    - 同步为关键业务节点添加 `data-test` 属性（报告标题、报告条目、阶段徽章、雷达图容器），供任务 10.1 使用
    - _Requirements: 1.1, 2.1, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.4, 3.7, 4.7, 5.1, 5.2, 5.4, 5.6, 6.1, 7.7, 7.8, 7.10, 7.11, 7.13, 8.6, 8.7, 8.8_

  - [ ]* 7.2 编写属性测试：Resume 页请求 / SSE / reply / error 等价性
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.resumePage.property.test.js`
    - 顶部注释（多条）：
      - `// Feature: frontend-mission-console-shell, Property 6: 重构前后请求等价性 (Resume_Page)`
      - `// Feature: frontend-mission-console-shell, Property 7: SSE 事件序列等价性 (Resume_Page)`
      - `// Feature: frontend-mission-console-shell, Property 8: Reply 增量累加渲染等价性 (Resume_Page)`
      - `// Feature: frontend-mission-console-shell, Property 10: Error 透传不变性 (Resume_Page)`
    - **Property 6**：mock `globalThis.fetch`，遍历合法 `(resumeText, jdText, targetRole)` 输入空间，断言抓到的请求 `endpoint === '/api/resume/diagnose'`、`method === 'POST'`、请求体 keys 集合等于既定字段集合（不增、不减）
    - **Property 7**：用 fast-check 生成满足 grammar `meta? reply* warning* (done | error)` 的 SSE 事件序列 `S`，通过 mock fetch 的 `ReadableStream` 重放给页面，断言回调按 `S` 的相对顺序与计数被触发
    - **Property 8**：生成非空字符串数组 `[d1..dN]` 依序作为 `onMessage(delta)` 触发，断言 Result Zone `textContent` 在归一化后包含 `d1+...+dN` 拼接结果且相对顺序一致
    - **Property 10**：生成随机非空字符串 `m`，触发 `onError(m)`，断言 DOM 中错误区域 `textContent` 在 trim 后**严格等于** `m`，且不包含黑名单文案集合 `['请求失败', '系统错误', '服务异常', '出错了', '错误：']`
    - **Validates: Requirements 2.4, 2.5, 2.6, 2.7**
    - _Requirements: 2.4, 2.5, 2.6, 2.7_

- [x] 8. 重构 `CareerPlanning.vue`
  - [x] 8.1 改写 `frontend/src/CareerPlanning.vue` 顶层 `<template>` 为 `<FeaturePageShell title="职业规划" :stageBadges="[路线图, 阶段目标, 能力缺口]" variant="default">`
    - 简历文本（来自 `userStore`）、用户困惑输入、推荐问题 chips → `#control` slot
    - 流式 Markdown 蓝图 → `#result` slot
    - 「生成蓝图 / 复制 / 导出」按钮通过 `ActionDock` 聚合为 `#primary` + `#secondary`
    - 渲染 `<SidebarEducationPlaceholder />`
    - Toast / Loader 引用改为 `import { showToast, resolveLoader } from '@/utils/uiFallbacks'`
    - **严格不变**：既有 `fetch('/api/career/plan')` + `fetch('/api/career/suggestions')` 行解析 SSE 处理逻辑、HTTP 端点、请求体字段、能力缺口条目渲染原样保留
    - **错误透传纪律**：与任务 7.1 相同
    - 同步为关键业务节点添加 `data-test` 属性（阶段路线条目、能力缺口条目），供任务 10.1 使用
    - 受保护文件清单不变
    - _Requirements: 1.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8, 3.2, 3.5, 3.8, 4.7, 5.1, 5.2, 5.4, 5.6, 6.1, 7.7, 7.8, 7.10, 7.11, 7.13, 8.6, 8.7, 8.8_

  - [ ]* 8.2 编写属性测试：Career 页请求 / SSE / reply / error 等价性
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.careerPage.property.test.js`
    - 顶部注释（多条，对应 Property 6 / 7 / 8 / 10 在 Career_Page 上的实例化）
    - **Property 6**：endpoint ∈ `{'/api/career/plan', '/api/career/suggestions'}`，方法与字段集合按既定白名单
    - **Property 7 / 8 / 10**：与任务 7.2 同结构，但作用对象为 `CareerPlanning.vue`
    - **Validates: Requirements 2.4, 2.5, 2.6, 2.7**
    - _Requirements: 2.4, 2.5, 2.6, 2.7_

- [x] 9. 重构 `PremiumInterview.vue`
  - [x] 9.1 改写 `frontend/src/PremiumInterview.vue` 顶层 `<template>` 为 `<FeaturePageShell title="模拟面试" :stageBadges="[训练舱, 实时评分, 复盘]" :variant="themeVariant">`
    - 难度选择（温和 / 标准 / P8）、消息输入 → `#control` slot
    - 对话气泡流、压力分 `MetricCard`、复盘 Modal（基于既有 `BaseModal.vue` 扩展，不修改 `BaseModal.vue`） → `#result` slot
    - 「发送 / 结束面试」通过 `ActionDock` 聚合为 `#primary` + `#secondary`
    - 渲染 `<SidebarEducationPlaceholder />`
    - 复用既有 `CyberRadarChart.vue` 渲染六维复盘评分（不修改该文件）
    - Toast / Loader 引用改为 `import { showToast, resolveLoader } from '@/utils/uiFallbacks'`
    - **严格不变**：既有 `streamInterviewChat` 调用（来自 `services/llm_service.js`）、`fetch('/api/interview/evaluate')`、HTTP 端点、请求体字段、对话流追加逻辑、压力分 / 评分链路原样保留
    - **错误透传纪律**：与任务 7.1 相同
    - 同步为关键业务节点添加 `data-test` 属性（对话气泡、压力分卡片、复盘按钮、复盘雷达图容器），供任务 10.1 使用
    - 受保护文件清单不变
    - _Requirements: 1.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.3, 3.6, 3.9, 4.7, 5.1, 5.2, 5.4, 5.6, 6.1, 7.7, 7.8, 7.10, 7.11, 7.13, 8.6, 8.7, 8.8_

  - [ ]* 9.2 编写属性测试：Interview 页请求 / SSE / reply / error 等价性
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.interviewPage.property.test.js`
    - 顶部注释（多条，对应 Property 6 / 7 / 8 / 10 在 Interview_Page 上的实例化）
    - **Property 6**：endpoint ∈ `{'/api/interview/chat', '/api/interview/evaluate'}`，方法与字段集合按既定白名单（`messages`、`difficulty` 等）
    - **Property 7 / 8 / 10**：与任务 7.2 同结构，但作用对象为 `PremiumInterview.vue`，且需覆盖「对话流的累加追加」与「评分 MetricCard 节点」
    - **Validates: Requirements 2.4, 2.5, 2.6, 2.7**
    - _Requirements: 2.4, 2.5, 2.6, 2.7_

- [x] 10. 集成验证：渲染节点不丢失 + 端到端验收清单
  - [ ]* 10.1 编写 spec 测试：三页渲染节点不丢失
    - 文件：`frontend/src/__tests__/featureMissionConsoleShell.renderNodeNonLoss.spec.js`
    - 顶部注释：`// Feature: frontend-mission-console-shell, Property 9: 渲染节点不丢失`
    - **EXAMPLE 级**测试：每页准备 1-3 份代表性后端响应固定夹具（含报告标题、报告条目、阶段徽章、雷达图容器、压力分 MetricCard、复盘按钮等），断言重构后页面渲染的 `data-test` 标记节点集合是「重构前快照集合」的**超集**
    - 任务 7.1 / 8.1 / 9.1 已为关键业务节点添加 `data-test` 属性，本任务直接消费
    - **Property 9: 渲染节点不丢失**
    - **Validates: Requirements 2.1, 2.2, 2.3, 3.7, 3.8, 3.9**
    - _Requirements: 2.1, 2.2, 2.3, 3.7, 3.8, 3.9_

  - [x] 10.2 编写端到端手工验收清单 `frontend/src/__tests__/featureMissionConsoleShell.e2eChecklist.md`
    - 列出三页 happy path 验收项：
      1. Resume_Page：上传 → 触发诊断 → 接收 SSE → 渲染报告 + 雷达图
      2. Career_Page：输入背景 → 触发规划 → 阶段路线 + 能力缺口
      3. Interview_Page：进入训练舱 → 一轮问答 → 实时评分 → 复盘
    - 列出视觉抽样对比项：三页与 `Dashboard.vue` 在字体层级 / 圆角 / 阴影 / 边框透明度上的同源性
    - 列出 git diff 检查项：受保护文件清单未被触碰
    - 列出 grep 检查项：三页内 `Toast.vue` / `StreamingLoader.vue` 的直接 import 出现次数 ≤ 1（且仅来自 `@/utils/uiFallbacks`）
    - 该清单是发版前的人工核对单，不包含任何用户文档 / 营销 / 部署内容
    - _Requirements: Acceptance Criteria 1, 2, 3, 4, 5, 6, 7, 8_

- [x] 11. Final checkpoint - 全量回归
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 任务标记 `*` 的子任务为可选测试，可在快速 MVP 路径下跳过；但本特性「重构前后等价性」是核心承诺，强烈建议全部执行
- 每个任务均以「写代码 / 改代码 / 写测试」为单位，不包含部署、用户验收、性能采集、运行应用等非编码动作
- 任务 2.4 + 3.2、2.3 + 4.2 共用同一个测试文件以减少文件碎片，因此被强制安排在不同 wave 以避免并发写入冲突
- 三页业务闭环 happy path 的真实端到端跑通由任务 10.2 的清单承担，不在自动化测试范围内
- 13 条 Correctness Properties 全部映射到了上面的属性测试任务，对应关系如下：
  - Property 1 → 任务 2.2
  - Property 2 → 任务 2.3
  - Property 3 → 任务 4.2
  - Property 4 → 任务 2.4
  - Property 5 → 任务 3.2
  - Property 6 / 7 / 8 / 10 → 任务 7.2、8.2、9.2（每页一份独立属性测试）
  - Property 9 → 任务 10.1（EXAMPLE 级）
  - Property 11 → 任务 5.2
  - Property 12 → 任务 1.2
  - Property 13 → 任务 1.3
- **构建命令红线**：实现期间**严禁**运行 `npm run build` / `vite build` / `tsc` / `vue-tsc`；类型 / 编译问题直接改代码，类型校验交由 IDE 与 `npm run test` 间接覆盖

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1", "4.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.2", "2.3", "2.4", "2.5", "5.2", "7.1", "8.1", "9.1"] },
    { "id": 2, "tasks": ["3.2", "4.2"] },
    { "id": 3, "tasks": ["7.2", "8.2", "9.2", "10.1"] },
    { "id": 4, "tasks": ["10.2"] }
  ]
}
```
