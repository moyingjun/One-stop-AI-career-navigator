# Implementation Plan: Dashboard 新手启航舱（Onboarding Empty State）

## Overview

在 `frontend/src/Dashboard.vue` 单文件中，为"继续上次"区块重构零数据态体验。当 `historyRecords` 为空时渲染新手启航舱（OnboardingPanel），有历史记录时平滑切换回现有历史列表（HistoryPanel）。整个改动不引入任何新依赖。

---

## Tasks

- [x] 1. 添加加载状态 ref 并修改 loadHistory 函数
  - 在 `<script setup>` 中新增 `const isHistoryLoading = ref(true)` 响应式变量
  - 修改现有 `loadHistory()` 函数：进入时将 `isHistoryLoading` 置为 `true`，在 `finally` 块中置为 `false`（无论成功或失败）
  - 确保网络错误或非 2xx 响应时 `historyRecords` 保持为空数组，`isHistoryLoading` 仍能正确归 `false`
  - _Requirements: 1.4, 1.5_

- [x] 2. 实现面板互斥渲染与过渡动画
  - [x] 2.1 用 `<transition name="onboarding-fade" mode="out-in">` 包裹"继续上次"区块的条件渲染区域
    - 在 `v-if="isHistoryLoading"` 分支中渲染加载占位状态（skeleton 或 spinner）
    - 在 `v-else-if="historyRecords.length === 0"` 分支中挂载 OnboardingPanel（`key="onboarding"`）
    - 在 `v-else` 分支中挂载现有 HistoryPanel（`key="history"`）
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 6.1, 6.2_

  - [x] 2.2 为 Property 1（互斥渲染）编写属性测试
    - **Property 1: Mutual Exclusion Rendering**
    - **Validates: Requirements 1.1, 1.2, 1.3**
    - 对任意 `historyRecords` 值（空 / 非空），断言 OnboardingPanel 与 HistoryPanel 有且仅有一个存在于 DOM 中

  - [x] 2.3 在 `<style scoped>` 中添加 `onboarding-fade` 过渡 CSS
    - 实现 `.onboarding-fade-enter-active` / `.onboarding-fade-leave-active`：`transition: opacity 0.4s ease, transform 0.4s ease`
    - 实现 `.onboarding-fade-enter-from` / `.onboarding-fade-leave-to`：`opacity: 0; transform: translateY(8px)`
    - _Requirements: 6.3, 6.4_

- [x] 3. 实现 OnboardingPanel 容器与全局引导语
  - 使用与 HistoryPanel 完全相同的外层容器样式类：`rounded-[28px] border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5`
  - 添加 `animate-fade-in-up` 入场动画类（仅执行一次）
  - 在容器顶部渲染全局引导语，样式：`border-l-2 border-purple-500/50 pl-3 text-xs text-gray-400`
  - 引导语文案："系统初始化完成。欢迎登舰，新同学。四大核心引擎已就绪，请选择你的首个突破口进行全息扫描。"
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4. 实现卡片网格布局与静态数据配置
  - [x] 4.1 在 `<script setup>` 中定义 `onboardingCards` 静态常量数组（4 张卡片配置）
    - 包含字段：`id`、`emoji`、`title`、`subtitle`、`desc`、`action`、`path`、`locked`、`themeColor`
    - 按设计文档填入简历诊断、模拟面试、职业规划、升学与避坑的完整文案和路径
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.3_

  - [x] 4.2 为 Property 5（卡片内容配置一致性）编写属性测试
    - **Property 5: Card Content Config Consistency**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    - 对任意卡片，断言渲染的 `desc` 文本与 `onboardingCards` 配置中对应条目完全一致

  - [x] 4.3 在 OnboardingPanel 中渲染卡片网格容器
    - 使用 `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3` 布局
    - 用 `v-for="card in onboardingCards"` 遍历渲染卡片
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 5. 实现激活状态引导卡片（ActiveCard）
  - [x] 5.1 渲染激活卡片的完整结构（`v-if="!card.locked"`）
    - Emoji 图标区域（`w-10 h-10` 主题色背景圆角块）
    - 标题行：中文 `title`（`text-sm font-bold text-white`）+ 英文 `subtitle`（`text-xs text-gray-500`）
    - 描述文本：`text-xs text-gray-400 leading-relaxed line-clamp-3`
    - 操作按钮（`mt-auto`）：绑定 `@click="router.push(card.path)"`，应用对应主题色样式
    - _Requirements: 4.1, 4.5_

  - [x] 5.2 为 Property 3（激活卡片内容完整性）编写属性测试
    - **Property 3: Active Card Content Completeness**
    - **Validates: Requirements 4.5**
    - 对每张激活卡片，断言 Emoji、中文标题、英文副标题、描述文本、操作按钮同时存在于渲染结果中

  - [x] 5.3 为激活卡片应用主题色样式与悬停动画
    - 按主题色映射表应用边框色（`border-purple-500/40` / `border-pink-500/40` / `border-blue-500/40`）
    - 按钮应用对应主题色（`text-purple-300 bg-purple-500/20 hover:bg-purple-500/30` 等）
    - 卡片容器添加 `hover:-translate-y-1 hover:shadow-[...] transition-all duration-300`
    - _Requirements: 4.6, 4.7_

  - [x] 5.4 为 Property 2（激活卡片路由跳转正确性）编写属性测试
    - **Property 2: Active Card Route Navigation Correctness**
    - **Validates: Requirements 4.2, 4.3, 4.4**
    - 对每张激活卡片，模拟点击按钮，断言 `router.push` 被调用且参数与 `card.path` 完全一致；断言不同卡片的路径互不相同

- [x] 6. 实现锁定状态引导卡片（LockedCard）
  - [x] 6.1 渲染锁定卡片结构（`v-else`，即 `card.locked === true`）
    - 外层容器添加 `opacity-60`
    - 操作按钮文案："模块构筑中... Coming Soon"，添加 `animate-pulse cursor-not-allowed`
    - 按钮样式：`border border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50`
    - 卡片边框：`border-emerald-500/40`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [x] 6.2 为锁定卡片按钮绑定点击拦截逻辑
    - 使用 `@click.prevent` 阻止默认行为
    - 调用 `showToastMsg('该模块正在开发中，敬请期待！', 3000)` 反馈用户
    - 确保 `router.push` 不被调用
    - _Requirements: 5.5_

  - [x] 6.3 为 Property 4（锁定卡片不可达性）编写属性测试
    - **Property 4: Locked Card Unreachability**
    - **Validates: Requirements 5.5**
    - 对锁定卡片，模拟点击按钮，断言 `router.push` 永远不被调用，且 Toast 提示被触发

- [x] 7. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请向用户确认。

- [x] 8. 零副作用验证与收尾
  - [x] 8.1 验证 OnboardingPanel 渲染不触发额外 fetch 请求
    - 检查 `onboardingCards` 数据为纯静态常量，不依赖任何响应式数据源
    - 确认 OnboardingPanel 渲染路径中无 `fetch` / `XHR` 调用
    - _Requirements: 8.1, 8.3_

  - [x] 8.2 为 Property 7（零副作用渲染）编写属性测试
    - **Property 7: Zero Side Effect Rendering**
    - **Validates: Requirements 8.2**
    - 对导致 `historyRecords.length === 0` 的任意状态，断言渲染前后所有其他 `ref`（如 `chatMessages`）的值保持不变

  - [x] 8.3 为 Property 6（渲染幂等性）编写属性测试
    - **Property 6: Rendering Idempotency**
    - **Validates: Requirements 8.4**
    - 多次调用 `loadHistory()` 后，断言面板渲染结果仅由最终 `historyRecords` 值决定，与调用次数无关

  - [x] 8.4 确认 `historyRecords` 变为非空时不重置 `chatMessages` 等其他响应式状态
    - 检查切换逻辑中无对 `chatMessages`、`userChatInput` 等 ref 的赋值操作
    - _Requirements: 8.5_

- [x] 9. 最终检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请向用户确认。

---

## Notes

- 标有 `*` 的子任务为可选项，可在快速 MVP 阶段跳过
- 每个任务均引用了具体的需求条款，便于追溯
- 检查点确保增量验证，避免积累问题
- 属性测试验证系统级不变量，单元测试验证具体示例和边界条件
- 整个改动仅涉及 `frontend/src/Dashboard.vue` 单文件，不引入任何新依赖

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "4.2", "4.3"] },
    { "id": 3, "tasks": ["3", "5.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 5, "tasks": ["5.4", "6.2"] },
    { "id": 6, "tasks": ["6.3", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4"] }
  ]
}
```
