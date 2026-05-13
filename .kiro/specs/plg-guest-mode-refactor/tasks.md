# Implementation Plan: PLG 游客模式重构与首页转化率优化

## Overview

本实现计划将 PLG 游客模式功能分解为增量式编码任务。核心改造包括：路由守卫从 `requiresSetup` 迁移至 `requiresAuth`（支持 token 或 guest 角色放行）、Landing.vue 入口分流（主 CTA "免注册极速体验" + 次按钮 "登录/注册"）、Auth.vue 占位页创建、SetupModal.vue 弹窗组件封装。所有改动保持 GlobalSetup.vue 零修改的向后兼容。

## Tasks

- [x] 1. 路由守卫重构与路由配置更新
  - [x] 1.1 重构 router/index.js 路由守卫逻辑
    - 将 Dashboard 路由 meta 从 `requiresSetup: true` 改为 `requiresAuth: true`
    - 重写 `beforeEach` 守卫：检查 `to.meta.requiresAuth`，若为 false/undefined 直接放行
    - 实现 token 检查：`localStorage.getItem('token')` 非空且非纯空白字符串时放行
    - 实现 guest 角色检查：`localStorage.getItem('userRole') === 'guest'` 时放行
    - 两者均不满足时重定向至 `/`
    - 添加 localStorage 不可用时的 try-catch 降级处理（默认放行 + console.warn）
    - 保留所有现有路由定义不变（Landing, GlobalSetup, Dashboard, ResumeDiagnosis, Interview, CareerPlanning, HistoryArchive, SavedChats, KnowledgeBase 及 redirects）
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.1, 7.3, 7.4, 7.5_

  - [x] 1.2 注册 /auth 路由
    - 在 router/index.js 中新增 `/auth` 路由，name 为 `'Auth'`，组件指向 Auth.vue
    - 该路由不设置 `requiresAuth` meta 字段（无需认证即可访问）
    - _Requirements: 4.4, 7.2_

  - [x] 1.3 编写路由守卫属性测试
    - **Property 1: Router Guard Access Decision Correctness**
    - 使用 fast-check 随机生成 token（null/空字符串/纯空白/有效字符串）和 userRole（null/guest/registered/随机字符串）组合
    - 验证：requiresAuth 为 false 时始终放行；token 有效时放行；userRole 为 guest 时放行；其余情况重定向至 '/'
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6**

- [x] 2. Checkpoint - 路由守卫验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Landing.vue 入口分流改造
  - [x] 3.1 实现游客模式入口按钮与逻辑
    - 新增 `enterAsGuest()` 方法：写入 `localStorage.setItem('userRole', 'guest')` 后调用 `router.push('/dashboard')`
    - 将 Hero 区域主按钮文案从 "免费开始使用" 改为 "免注册极速体验"
    - 主按钮绑定 `@click="enterAsGuest"`，保留 `from-cyan-500 to-purple-600` 渐变背景和 glow shadow 样式
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.2 实现登录/注册入口按钮
    - 新增 `goToAuth()` 方法：仅调用 `router.push('/auth')`，不修改 localStorage
    - 将 Hero 区域次按钮文案从 "查看演示" 改为 "登录 / 注册"，保持 outline/text-only 低视觉权重样式
    - 更新 Navbar 右上角按钮区域：将 "登录" 文本按钮改为绑定 `@click="goToAuth"` 的 "登录 / 注册" 按钮
    - 将 Navbar "免费开始" 按钮改为绑定 `@click="enterAsGuest"` 的 "免注册极速体验" 按钮
    - 确保移动端（< md 断点）至少有一个 "登录 / 注册" 按钮可见可交互
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.3 编写 goToAuth 无副作用属性测试
    - **Property 2: Auth Navigation No Side Effects**
    - 使用 fast-check 随机生成 localStorage 初始状态，调用 goToAuth 后验证 localStorage 未被修改
    - **Validates: Requirement 3.2**

- [x] 4. Auth.vue 占位页面创建
  - [x] 4.1 创建 Auth.vue 组件
    - 在 `frontend/src/Auth.vue` 创建占位页面
    - 使用 `bg-[#050505]` 背景，`min-h-screen flex items-center justify-center` 布局
    - 使用 CyberGlassCard 组件作为主内容容器，设置 `backdrop-blur` 效果（blur >= 12px）
    - 展示标题文案（如 "登录 / 注册"）和描述文案（如 "认证系统即将上线..."）
    - 提供 "返回首页" 按钮/链接，绑定 `router.push('/')`，支持 click 和 keyboard 交互
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5. Checkpoint - Landing 与 Auth 页面验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. SetupModal.vue 弹窗组件创建
  - [x] 6.1 创建 SetupModal.vue 组件结构与 UI
    - 在 `frontend/src/components/SetupModal.vue` 创建弹窗组件
    - 外层使用 `fixed inset-0 z-50` 遮罩层（半透明背景）
    - 内容区使用 CyberGlassCard 风格：`backdrop-blur-xl`、`border border-white/10`
    - 右上角提供关闭按钮(X)，使用 lucide-vue-next 的 X 图标
    - 复用 GlobalSetup.vue 的表单 UI 结构：姓名输入框 + 简历上传/粘贴区域
    - 支持预填充：mounted 时从 localStorage 读取已有 `candidate_name` 和 `resume_text` 填入表单
    - _Requirements: 5.1, 5.9, 5.10_

  - [x] 6.2 实现 SetupModal 表单验证与提交逻辑
    - `defineEmits(['close', 'complete'])`
    - 关闭按钮点击时 `emit('close')`，不修改 localStorage
    - 表单验证：姓名 trim 后为空 → 显示 inline 错误；姓名超过 50 字符 → 显示 inline 错误；简历 trim 后 < 20 字符 → 显示 inline 错误
    - 验证通过后：写入 `candidate_name`（trimmed, max 50）、`resume_text`（trimmed, max 10000）、`userRole: 'registered'` 至 localStorage
    - 三项写入完成后 `emit('complete')`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.11_

  - [x] 6.3 编写 SetupModal close 无副作用属性测试
    - **Property 3: SetupModal Close No Side Effects**
    - 使用 fast-check 随机生成 localStorage 初始状态，触发 close 后验证 localStorage 未被修改
    - **Validates: Requirement 5.2**

  - [x] 6.4 编写 SetupModal 有效提交持久化属性测试
    - **Property 4: SetupModal Valid Submission Persistence**
    - 使用 fast-check 生成满足条件的 candidateName（trim 非空, <= 50 字符）和 resumeText（trim >= 20 字符, <= 10000 字符）
    - 验证提交后 localStorage 中 candidate_name、resume_text、userRole 值正确
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.6**

  - [x] 6.5 编写 SetupModal 无效输入拒绝属性测试
    - **Property 5: SetupModal Invalid Input Rejection**
    - 使用 fast-check 生成不满足条件的输入（空姓名或简历 < 20 字符）
    - 验证提交后 localStorage 未被修改且不触发 complete 事件
    - **Validates: Requirements 5.7, 5.8**

- [x] 7. 集成验证与向后兼容确认
  - [x] 7.1 验证 GlobalSetup.vue 向后兼容
    - 确认 GlobalSetup.vue 文件内容未被修改（零改动）
    - 确认 `/setup` 路由仍然存在且指向 GlobalSetup 组件
    - 确认已注册用户（有 candidate_name + resume_text）通过 GlobalSetup 流程后仍可正常进入 Dashboard
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 7.2 编写集成测试验证端到端流程
    - 测试游客流程：模拟点击 "免注册极速体验" → 验证 userRole 写入 → 验证路由跳转至 /dashboard
    - 测试认证流程：模拟点击 "登录 / 注册" → 验证路由跳转至 /auth → 验证 localStorage 无修改
    - 测试拦截流程：无 token 且无 guest 角色时访问 /dashboard → 验证重定向至 /
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1_

- [x] 8. Final checkpoint - 全部测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- GlobalSetup.vue 必须保持零修改（byte-identical），所有新功能通过新组件实现
- SetupModal.vue 放置在 `src/components/` 目录下，遵循项目约定
- Auth.vue 作为页面级组件放置在 `src/` 目录下，遵循项目约定

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "4.1"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3", "6.1"] },
    { "id": 4, "tasks": ["6.2"] },
    { "id": 5, "tasks": ["6.3", "6.4", "6.5"] },
    { "id": 6, "tasks": ["7.1", "7.2"] }
  ]
}
```
