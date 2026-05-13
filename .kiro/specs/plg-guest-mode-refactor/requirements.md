# Requirements Document

## Introduction

本文档定义了 PLG（Product-Led Growth）游客模式重构功能的需求规格。该功能旨在降低用户首次体验门槛，通过引入"免注册极速体验"入口允许游客无需注册即可进入产品核心功能页面，同时保留已注册用户的完整体验路径。改造涉及路由守卫逻辑重构、Landing.vue 入口分流、Auth.vue 占位页创建、以及 GlobalSetup.vue 弹窗化封装。

## Glossary

- **Router_Guard**: Vue Router 的 `beforeEach` 导航守卫，负责在页面跳转前执行访问权限检查
- **Landing_Page**: 产品首页组件（Landing.vue），提供用户入口路径选择
- **Dashboard**: 产品核心功能仪表盘页面，展示用户概览和快捷入口
- **Auth_Page**: 登录/注册页面组件（Auth.vue），当前阶段为占位实现
- **SetupModal**: 全局设置弹窗组件，封装原 GlobalSetup.vue 的表单功能为可复用弹窗
- **Guest_Role**: 游客角色标识，localStorage 中 `userRole` 值为 `'guest'` 的用户状态
- **Registered_Role**: 已注册角色标识，localStorage 中 `userRole` 值为 `'registered'` 的用户状态
- **Token**: 认证令牌，存储于 localStorage 中，表示用户已通过身份验证（非空字符串）
- **GlobalSetup**: 原有的全局设置页面组件（GlobalSetup.vue），提供姓名和简历输入功能

## Requirements

### Requirement 1: 路由守卫访问控制

**User Story:** As a 用户, I want 在持有合法凭证或游客角色时自由访问受保护页面, so that 我无需每次都重复验证即可使用产品功能。

#### Acceptance Criteria

1. WHEN a route with `requiresAuth: true` meta is accessed AND localStorage contains a non-null, non-empty token string, THE Router_Guard SHALL allow navigation to the target route
2. WHEN a route with `requiresAuth: true` meta is accessed AND localStorage contains `userRole` equal to `'guest'`, THE Router_Guard SHALL allow navigation to the target route
3. WHEN a route with `requiresAuth: true` meta is accessed AND localStorage contains neither a valid token nor a guest userRole, THE Router_Guard SHALL redirect navigation to the root path `/`
4. WHEN a route without `requiresAuth` meta (or with `requiresAuth: false` or `requiresAuth: undefined`) is accessed, THE Router_Guard SHALL allow navigation regardless of authentication state
5. IF localStorage API is unavailable (e.g., browser privacy mode), THEN THE Router_Guard SHALL allow navigation by default and log a warning to the console
6. IF localStorage contains a token that is only whitespace characters, THEN THE Router_Guard SHALL treat it as invalid and NOT grant access based on token alone

### Requirement 2: 游客模式快速入口

**User Story:** As a 新访客, I want 无需注册即可快速体验产品核心功能, so that 我能在决定注册前评估产品价值。

#### Acceptance Criteria

1. WHEN a user clicks the "免注册极速体验" button on the Landing_Page, THE Landing_Page SHALL write `'guest'` to localStorage key `userRole`
2. WHEN the Landing_Page has written `'guest'` to localStorage key `userRole`, THE Landing_Page SHALL navigate to the `/dashboard` route within the same click event handler without requiring additional user interaction
3. THE Landing_Page SHALL display the "免注册极速体验" button in the Hero section as the primary call-to-action, positioned before any secondary action buttons
4. THE Landing_Page SHALL display the "免注册极速体验" button with a cyan-to-purple gradient background (`from-cyan-500 to-purple-600`) and a visible glow shadow effect
5. IF localStorage key `userRole` equals `'guest'`, THEN THE router navigation guard SHALL allow access to the `/dashboard` route without requiring `candidate_name` or `resume_text` in localStorage
6. IF a user navigates to `/dashboard` with localStorage key `userRole` equal to `'guest'` but without `candidate_name` or `resume_text`, THEN THE system SHALL display the dashboard without redirecting to `/setup`

### Requirement 3: 登录/注册入口导航

**User Story:** As a 回访用户, I want 从首页直接进入登录/注册流程, so that 我能使用已注册账户的完整功能。

#### Acceptance Criteria

1. WHEN a user clicks the "登录 / 注册" button on the Landing_Page, THE Landing_Page SHALL navigate to the `/auth` route without modifying any localStorage values
2. THE Landing_Page SHALL display the "登录 / 注册" button in the Hero section with lower visual prominence than the primary "免注册极速体验" button (e.g., no filled gradient background, using outline or text-only style)
3. THE Landing_Page SHALL display a "登录 / 注册" button in the Navbar area with the same label text and the same navigation target (`/auth`) as the Hero section button
4. WHILE the viewport width is less than the `md` breakpoint (768px), THE Landing_Page SHALL keep at least one "登录 / 注册" button visible and accessible to the user

### Requirement 4: Auth 占位页面

**User Story:** As a 用户, I want 看到一个登录/注册页面的占位界面, so that 我知道该功能即将上线并能返回首页继续使用产品。

#### Acceptance Criteria

1. WHEN a user navigates to the `/auth` route, THE Auth_Page SHALL display a placeholder interface containing a visible heading text that communicates the authentication feature is coming soon, and a brief descriptive message explaining the feature is under development
2. THE Auth_Page SHALL provide a "返回首页" clickable navigation element that uses Vue Router navigation to route back to `/`
3. THE Auth_Page SHALL render with the cyberpunk dark glass design language using `bg-[#050505]` background, `backdrop-blur` effects with a minimum blur radius of 12px, and the CyberGlassCard component as the primary content container
4. THE Auth_Page SHALL be registered in the Vue Router configuration at path `/auth` with name `'Auth'`
5. IF the user activates the "返回首页" navigation element via click or keyboard interaction, THEN THE Auth_Page SHALL navigate to the `/` route within 1 second without a full page reload

### Requirement 5: SetupModal 弹窗组件

**User Story:** As a 游客用户, I want 在 Dashboard 中通过弹窗完善个人信息, so that 我能在体验产品后无缝升级为完整用户。

#### Acceptance Criteria

1. WHEN SetupModal is displayed, THE SetupModal SHALL render as a fixed overlay with `inset-0 z-50` positioning and a semi-transparent backdrop
2. WHEN a user clicks the close button (X) on SetupModal, THE SetupModal SHALL emit a `close` event without modifying any localStorage values
3. WHEN a user submits valid form data in SetupModal, THE SetupModal SHALL write `candidate_name` (trimmed, maximum 50 characters) to localStorage
4. WHEN a user submits valid form data in SetupModal, THE SetupModal SHALL write `resume_text` (trimmed, maximum 10000 characters) to localStorage
5. WHEN a user submits valid form data in SetupModal, THE SetupModal SHALL write `'registered'` to localStorage key `userRole`
6. WHEN a user submits valid form data in SetupModal, THE SetupModal SHALL emit a `complete` event after all three localStorage writes have completed
7. IF a user submits with a candidate name that is empty or contains only whitespace after trim, THEN THE SetupModal SHALL display an inline error message below the name field indicating the name is required, and prevent submission
8. IF a user submits with resume text shorter than 20 characters after trim, THEN THE SetupModal SHALL display an inline error message below the resume field indicating the minimum length requirement, and prevent submission
9. THE SetupModal SHALL use the CyberGlassCard design style with `backdrop-blur-xl` and `border border-white/10` styling
10. WHEN SetupModal is displayed and localStorage already contains `candidate_name` or `resume_text`, THE SetupModal SHALL pre-populate the corresponding form fields with the existing stored values
11. IF a user submits with a candidate name exceeding 50 characters after trim, THEN THE SetupModal SHALL display an inline error message below the name field indicating the maximum length has been exceeded, and prevent submission

### Requirement 6: GlobalSetup 向后兼容

**User Story:** As a 开发者, I want 原有 GlobalSetup.vue 保持不变, so that 现有功能不受影响且可作为独立页面继续使用。

#### Acceptance Criteria

1. THE GlobalSetup component SHALL remain at its original file path `frontend/src/GlobalSetup.vue` with zero content changes compared to the pre-refactor version (byte-identical)
2. THE Router SHALL maintain the `/setup` route with name `GlobalSetup` pointing to the GlobalSetup component, and the navigation guard SHALL redirect users to `/setup` when `candidate_name` or `resume_text` is absent from localStorage
3. WHEN a user enters a name (at least 1 character) and resume text (at least 20 characters) in the GlobalSetup form and clicks the submit button, THE system SHALL save `candidate_name` and `resume_text` to localStorage and navigate to `/dashboard`
4. WHEN a user arrives at `/dashboard` after completing setup via GlobalSetup, THE system SHALL read `candidate_name` and `resume_text` from localStorage and render the Dashboard with the user's profile data displayed
5. IF the new SetupModal component is introduced by the refactor, THEN THE system SHALL NOT modify, remove, or override the localStorage keys `candidate_name` and `resume_text` in a way that conflicts with GlobalSetup's read/write behavior

### Requirement 7: 路由配置更新

**User Story:** As a 系统, I want 路由元信息从 `requiresSetup` 迁移为 `requiresAuth`, so that 访问控制语义与新的认证模型一致。

#### Acceptance Criteria

1. THE Router SHALL define the Dashboard route (`/dashboard`) with `meta: { requiresAuth: true }` replacing the previous `meta: { requiresSetup: true }`
2. THE Router SHALL register the `/auth` route with route name `Auth` and the Auth.vue page component, with no meta guard fields
3. WHEN a user navigates to a route with `meta: { requiresAuth: true }`, THE Router beforeEach guard SHALL check for a valid authentication state and redirect the user to `/` if authentication is not satisfied
4. WHEN the application loads, THE Router SHALL preserve all existing routes (Landing, GlobalSetup, Dashboard, ResumeDiagnosis, Interview, CareerPlanning, HistoryArchive, SavedChats, KnowledgeBase, and existing redirects) as navigable alongside the new `/auth` route
5. IF the beforeEach guard encounters a route without `meta: { requiresAuth: true }`, THEN THE Router SHALL allow navigation without any authentication check
