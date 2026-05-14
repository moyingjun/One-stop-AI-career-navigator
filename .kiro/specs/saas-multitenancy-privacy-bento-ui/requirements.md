# Requirements Document

## Introduction

本功能将系统从"单用户无隔离"状态升级为具备 JWT 鉴权的多租户 SaaS 架构，分三个阶段交付：

1. **阶段一（后端鉴权与隐私隔离）**：引入 `users` 表、JWT 注册/登录接口、`get_current_user()` 依赖注入，以及所有历史记录查询强制附加 `WHERE user_id = current_user_id` 的隔离约束。
2. **阶段二（Bento 面板响应式数据链路）**：扩展 `userStore.js` 以支持三个 Tab 各自独立的 `pinnedId` 状态，`DataSourceModal` 按 Tab 过滤历史记录，`CyberRadarChart` 随 pinned ID 动态响应，并通过 localStorage 持久化。
3. **阶段三（UI/UX 体验补全）**：用自定义 `CustomDropdown.vue` 替换原生 `<select>`，新增 `ChatPreviewModal.vue` 预览 Agent 对话历史，`SetupModal.vue` 升学模式新增 `target_goal` 字段，Dashboard 在预测看板中展示 `target_goal`。

---

## Glossary

- **Auth_Router**: FastAPI 路由模块 `Router/auth.py`，负责处理注册和登录请求
- **Auth_Middleware**: FastAPI 依赖注入函数 `get_current_user()`，负责校验 JWT 并返回 `user_id`
- **Auth_Service**: 前端模块 `src/services/authService.js`，封装注册、登录、登出及鉴权请求头
- **Database**: 后端模块 `database.py`，负责所有 SQLite 数据访问
- **History_Router**: FastAPI 路由模块 `Router/history_router.py`，负责历史记录 CRUD
- **User_Store**: 前端 Pinia store `src/stores/userStore.js`，管理全局用户状态
- **DataSourceModal**: 前端组件 `DataSourceModal.vue`，用于选择历史记录作为数据源
- **CyberRadarChart**: 前端组件 `src/components/CyberRadarChart.vue`，基于 ECharts 渲染雷达图
- **CustomDropdown**: 前端组件 `src/components/CustomDropdown.vue`，深色赛博朋克风格自定义下拉菜单
- **ChatPreviewModal**: 前端组件 `ChatPreviewModal.vue`，用于预览 Agent 对话历史
- **SetupModal**: 前端组件 `SetupModal.vue`，用户信息配置弹窗
- **Dashboard**: 前端页面组件 `Dashboard.vue`，工作台 Bento 主页
- **HistoryArchive**: 前端页面组件 `HistoryArchive.vue`，历史档案页
- **Router_Guard**: 前端路由守卫 `router/index.js` 中的 `beforeEach` 钩子
- **JWT**: JSON Web Token，用于无状态身份验证的令牌格式
- **pinnedId**: 用户在某个 Tab 下选中并固定的历史记录 ID，用于驱动雷达图渲染
- **activeDataTab**: 当前激活的 Bento 面板 Tab，取值为 `resume`、`interview` 或 `career`
- **radarData**: 雷达图的数据对象，包含 `values` 数组（6 个维度分值）
- **target_goal**: 升学模式下用户填写的目标志愿（如"广东工业大学-软件工程"），存储于 localStorage

---

## Requirements

### Requirement 1: 用户注册

**User Story:** As a new user, I want to register an account with a username and password, so that I can access personalized features with my own data isolated from other users.

#### Acceptance Criteria

1. WHEN a registration request is received with a username between 1 and 50 characters (alphanumeric and underscore only) and a password of at least 8 characters, THE Auth_Router SHALL create a new user record with a bcrypt-hashed password and return an `access_token`, `user_id`, and `username`
2. IF bcrypt password hashing fails during registration, THEN THE Auth_Router SHALL return HTTP 500 and block the user record from being created
3. WHEN a registration request is received with a username that already exists, THE Auth_Router SHALL return HTTP 409 with detail message "用户名已被占用"
4. IF a registration request is received with a username or password that does not meet the format rules in criterion 1, THEN THE Auth_Router SHALL return HTTP 422 with a detail message describing the violated constraint, and SHALL NOT create any user record
5. WHERE an email field is provided in the registration request, THE Auth_Router SHALL store the email alongside the user record
6. THE Database SHALL enforce a UNIQUE constraint on the `username` column of the `users` table

---

### Requirement 2: 用户登录与 JWT 签发

**User Story:** As a registered user, I want to log in with my credentials and receive a JWT token, so that I can authenticate subsequent API requests.

#### Acceptance Criteria

1. WHEN a login request is received with a valid username and matching password, THE Auth_Router SHALL return an `access_token` (JWT), `token_type: "bearer"`, `user_id`, and `username`
2. IF a login request fails for any reason — including incorrect password, non-existent username, or internal system errors — THEN THE Auth_Router SHALL return HTTP 401 with detail message "用户名或密码错误"
3. WHEN a JWT token is issued, THE Auth_Router SHALL encode the `user_id` and `username` as claims within the token and set an expiration (`exp`) of 7 days
4. THE Auth_Router SHALL read the JWT signing secret from the `JWT_SECRET_KEY` environment variable and SHALL NOT hardcode the secret in source code
5. WHEN a login succeeds, THE Auth_Service SHALL write the `access_token` to `localStorage` under the key `token` and write the `user_id` under the key `user_id`; IF login fails, THE Auth_Service SHALL clear any previously stored `token` and `user_id` from `localStorage` and SHALL NOT write new credentials

---

### Requirement 3: JWT 鉴权中间件

**User Story:** As the system, I want every protected API endpoint to validate the caller's JWT token, so that only authenticated users can access their own data.

#### Acceptance Criteria

1. WHEN a request arrives at a protected endpoint with a token that has a valid signature, has not expired, and contains a positive integer `user_id` claim, THE Auth_Middleware SHALL decode the token and return the `user_id` as a positive integer
2. WHEN a request arrives with a missing Authorization header, THE Auth_Middleware SHALL return HTTP 401 with detail message "未提供认证凭据"
3. WHEN a request arrives with a token that is expired, structurally malformed, has an invalid signature, or contains a missing or non-positive `user_id` claim, THE Auth_Middleware SHALL return HTTP 401 with detail message "Token 已失效，请重新登录"
4. WHEN a 401 response is received by the frontend, THE Auth_Service SHALL clear the `token` and `user_id` entries from `localStorage` and redirect the user to `/auth`
5. WHERE an endpoint supports guest access, THE Auth_Middleware SHALL provide a `get_optional_user()` variant that returns `None` when no token is present instead of raising an error
6. WHEN a valid token (as defined in criterion 1) is present on a guest-enabled endpoint, THE Auth_Middleware SHALL process the token normally and return the authenticated `user_id`

---

### Requirement 4: 历史记录数据隔离

**User Story:** As a registered user, I want my history records to be completely isolated from other users' data, so that my private career information is never exposed to others.

#### Acceptance Criteria

1. THE Database SHALL include a `user_id` INTEGER column (foreign key referencing `users.id`) on the `history_records` table
2. WHEN a history record is created via any Agent or feature endpoint, THE Database SHALL insert the `user_id` of the authenticated user into the record
3. WHEN history records are queried for a given authenticated user, THE History_Router SHALL return only records whose `user_id` matches the authenticated user's ID
4. IF a request attempts to access a history record belonging to a different user, THEN THE History_Router SHALL return HTTP 403 with detail message "无权访问此资源"
5. WHEN an unauthenticated request (no valid token) is made to any history endpoint, THE History_Router SHALL return HTTP 401
6. WHEN the database is initialized on a system with existing records, THE Database SHALL apply schema changes so that existing records retain `user_id = NULL` without data loss

---

### Requirement 5: 数据库 Schema 初始化

**User Story:** As a developer, I want the database schema to be automatically initialized on startup, so that the application works correctly in both fresh and existing deployments.

#### Acceptance Criteria

1. WHEN the application starts and the `users` table does not exist, THE Database SHALL create the `users` table with columns: `id` (INTEGER PRIMARY KEY), `username` (TEXT UNIQUE NOT NULL), `password_hash` (TEXT NOT NULL), `email` (TEXT), `created_at` (TEXT)
2. WHEN the application starts and the `users` table already exists, THE Database SHALL skip table creation without error
3. WHEN the application starts and the `history_records` table does not have a `user_id` column, THE Database SHALL add the `user_id` INTEGER column to the table
4. WHEN the application starts and the `history_records` table already has a `user_id` column, THE Database SHALL skip the column addition without error
5. THE Database SHALL use parameterized `?` placeholders for all SQL queries
6. IF any SQL statement in the Database module is constructed via string concatenation rather than parameterized placeholders, THEN THE Database SHALL be considered non-compliant and the affected query SHALL be refactored before deployment

---

### Requirement 6: 前端路由守卫升级

**User Story:** As the system, I want the frontend route guard to restrict guest users to only the Landing and Auth pages, so that unauthenticated users cannot access protected features.

#### Acceptance Criteria

1. WHILE a user's `userRole` is `guest`, THE Router_Guard SHALL permit navigation only to the Landing page (`/`) and the Auth page (`/auth`); all other routes are protected and SHALL NOT be accessible to guest users
2. WHEN a guest user attempts to navigate to any protected route — including by directly entering a URL in the browser address bar — THE Router_Guard SHALL redirect the user to `/auth`
3. WHEN a user has a non-empty, non-whitespace `token` in `localStorage`, THE Router_Guard SHALL allow navigation to all protected routes including Dashboard
4. IF a user has no valid token AND is not in guest mode, THEN THE Router_Guard SHALL redirect the user to `/auth`

---

### Requirement 7: 前端鉴权服务（authService.js）

**User Story:** As a frontend developer, I want a centralized auth service module, so that all authentication logic is encapsulated and reusable across components.

#### Acceptance Criteria

1. THE Auth_Service SHALL expose a `registerUser(username, password, email)` function that calls `POST /api/auth/register` and returns the response payload
2. THE Auth_Service SHALL expose a `loginUser(username, password)` function that calls `POST /api/auth/login`, stores the `access_token` under key `token` and `user_id` under key `user_id` in `localStorage`, and returns the response payload
3. THE Auth_Service SHALL expose a `getAuthHeaders()` function that reads the `token` from `localStorage` and returns an object `{ Authorization: "Bearer <token>" }`, or an empty object if no token exists
4. THE Auth_Service SHALL expose a `logout()` function that removes `token` and `user_id` from `localStorage` and resets the User_Store profile fields (`candidateName`, `resumeText`, `activeMode`, `targetJob`, `jobDescription`, `examType`, `estimatedScore`, `examRank`, `targetSchool`) to their default empty values via `updateUserProfile()`
5. WHEN any API call made through Auth_Service's request interceptor returns HTTP 401, THE Auth_Service SHALL automatically invoke `logout()` and redirect to `/auth`
6. IF `registerUser` or `loginUser` receives a non-2xx response, THEN THE Auth_Service SHALL throw an error with the response's `detail` message so the calling component can display it to the user

---

### Requirement 8: userStore Pinned ID 状态管理

**User Story:** As a user, I want the dashboard to remember which history record I've pinned for each tab, so that my radar chart data persists across page refreshes and tab switches.

#### Acceptance Criteria

1. THE User_Store SHALL maintain three independent state fields: `pinnedResumeId`, `pinnedInterviewId`, and `pinnedCareerId`, each initialized to `null`
2. THE User_Store SHALL expose a `setPinnedId(tab, recordId)` action that accepts `tab` as one of `'resume'`, `'interview'`, or `'career'` and updates the corresponding field
3. WHEN `setPinnedId(tab, recordId)` is called with a valid tab and a non-null `recordId`, THE User_Store SHALL write the `recordId` to `localStorage` using the key `pinned_resume_id`, `pinned_interview_id`, or `pinned_career_id` respectively
4. WHEN `setPinnedId` is called for one tab, THE User_Store SHALL NOT modify the `pinnedId` values of the other two tabs
5. WHEN `setPinnedId(tab, null)` is called, THE User_Store SHALL set the corresponding field to `null` and remove the corresponding `localStorage` key
6. THE User_Store SHALL expose a `loadPinnedIds()` action that reads all three pinned ID keys from `localStorage` and restores the corresponding store fields; IF a key is absent in `localStorage`, THE User_Store SHALL leave the corresponding field as `null`
7. WHEN the application mounts, THE User_Store SHALL call `loadPinnedIds()` to restore persisted pinned IDs from `localStorage`; IF `loadPinnedIds()` throws an exception or `localStorage` is unavailable, THE User_Store SHALL continue with all three `pinnedId` fields set to `null` and allow users to re-pin records
8. THE User_Store SHALL expose a `getPinnedIdByTab(tab)` getter that returns the `pinnedId` for the specified tab; IF an unrecognized tab value is passed, THE getter SHALL return `null`
9. IF `setPinnedId` is called with an unrecognized tab value, THE User_Store SHALL silently ignore the call and leave all three `pinnedId` fields unchanged

---

### Requirement 9: DataSourceModal 按 Tab 过滤

**User Story:** As a user, I want the data source modal to show only records relevant to the current tab, so that I can quickly find and pin the right history record for each feature.

#### Acceptance Criteria

1. WHEN DataSourceModal is opened, THE DataSourceModal SHALL accept an `activeTab` prop and filter the displayed history records to only those matching the tab's category mapping
2. THE DataSourceModal SHALL apply the following category mapping: `resume` tab shows only records where `category === 'resume_diagnosis'`; `interview` tab shows only records where `category.startsWith('interview')`; `career` tab shows only records where `category === 'career_planning'`
3. WHEN a user selects a record in DataSourceModal, THE DataSourceModal SHALL emit a `select` event with the selected record
4. WHEN a `select` event is received by Dashboard, THE Dashboard SHALL call `userStore.setPinnedId(activeDataTab, record.id)`
5. THE DataSourceModal SHALL display all records matching the tab filter regardless of scores validity, but SHALL visually distinguish records without valid scores data using a dimmed style or a "无评分" badge so users can still reference them for context

---

### Requirement 10: 雷达图动态数据绑定

**User Story:** As a user, I want the radar chart to automatically update when I switch tabs or change the pinned record, so that I always see the scores for the currently selected data source.

#### Acceptance Criteria

1. WHEN the `pinnedId` for the active tab changes to a non-null value, THE CyberRadarChart SHALL fetch the corresponding history record and update its display with the record's `scores` data within 1 second of the change
2. IF the fetch for a pinned record fails, THEN THE CyberRadarChart SHALL preserve the existing `radarData` values and display an error indication; THE CyberRadarChart SHALL NOT reset values to zero on a failed fetch
3. WHEN `activeDataTab` changes and the new tab's `pinnedId` differs from the previous tab's `pinnedId`, THE Dashboard SHALL trigger a radar data update using the new tab's pinned record
4. WHILE `pinnedId` is `null` for the active tab AND all score values are zero, THE CyberRadarChart SHALL display all-zero values `[0, 0, 0, 0, 0, 0]` and render a "暂无数据" hint text in the chart center
5. WHEN valid score data is present, THE CyberRadarChart SHALL hide the "暂无数据" hint text
6. WHEN `updateRadarData(scores)` is called with any scores dictionary, THE CyberRadarChart SHALL clamp each numeric value `v` in `radarData.values` such that `0 ≤ v ≤ 100`; non-numeric values SHALL be treated as 0
7. WHEN the `pinnedId` changes multiple times within 300ms, THE Dashboard SHALL debounce the fetch request so that only the last change triggers an API call; any in-flight request from a superseded `pinnedId` SHALL be cancelled before the new request is sent

---

### Requirement 11: 自定义下拉菜单组件（CustomDropdown）

**User Story:** As a user, I want all dropdown menus to match the dark cyberpunk visual theme, so that the UI is visually consistent throughout the application.

#### Acceptance Criteria

1. THE CustomDropdown SHALL accept `modelValue` (String), `options` (Array of `{ value, label }`), and `placeholder` (String) as props, and SHALL emit `update:modelValue` to support `v-model` binding
2. WHEN a user clicks the trigger button, THE CustomDropdown SHALL show the dropdown panel if it is hidden, and hide it if it is visible
3. WHEN the dropdown panel is visible and the user clicks outside the dropdown element, THE CustomDropdown SHALL hide the dropdown panel
4. WHEN the dropdown panel is visible and the user presses the ESC key, THE CustomDropdown SHALL hide the dropdown panel
5. WHEN a user clicks an option, THE CustomDropdown SHALL emit `update:modelValue` with the selected option's `value` and hide the dropdown panel
6. WHEN `modelValue` matches an option's `value`, THE CustomDropdown trigger button SHALL display that option's `label`; WHEN no option matches, THE trigger button SHALL display the `placeholder` text
7. THE CustomDropdown trigger button SHALL have a semi-transparent dark background with a subtle border; the dropdown panel SHALL have a dark opaque background with a border and shadow; hovered options SHALL have a light highlight; the selected option SHALL have a purple tint
8. WHEN `options` is an empty array, THE CustomDropdown SHALL display an empty dropdown panel with no selectable items and SHALL NOT throw an error
9. THE HistoryArchive component SHALL replace all native `<select>` elements with the CustomDropdown component

---

### Requirement 12: HistoryArchive 过滤逻辑修正

**User Story:** As a user, I want the history archive filter to correctly categorize all interview and agent records, so that I can find all relevant records without missing any.

#### Acceptance Criteria

1. WHEN the "面试评估" filter option is selected in HistoryArchive, THE HistoryArchive SHALL display all records where `category.startsWith('interview')` is true, including records with categories such as `interview_evaluate`, `interview_mock`, and any other `interview_*` variants
2. WHEN the "Agent 对话" filter option is selected in HistoryArchive, THE HistoryArchive SHALL display all records where `category.startsWith('agent_')` is true
3. THE HistoryArchive filter dropdown SHALL include an "Agent 对话" option with value `agent_` in addition to the existing filter options
4. THE HistoryArchive SHALL display all category filter option labels using bold font weight

---

### Requirement 13: Agent 对话预览弹窗（ChatPreviewModal）

**User Story:** As a user, I want to preview my past Agent chat history in a modal before loading it, so that I can confirm the context before continuing a conversation.

#### Acceptance Criteria

1. WHEN a user clicks a history record card with a category matching `agent_*` on the Dashboard, THE Dashboard SHALL open ChatPreviewModal with `visible=true` and the corresponding `recordId`
2. WHEN ChatPreviewModal becomes visible with a `recordId` that is a positive integer, THE ChatPreviewModal SHALL display a loading indicator, fetch the record from the history API, and render the `chat_history` as a bubble conversation list
3. WHEN rendering chat bubbles, THE ChatPreviewModal SHALL display user messages right-aligned with a purple-tinted bubble style and AI messages left-aligned with a neutral dark bubble style
4. WHEN a user clicks the "✨ 载入上下文并继续对话" button, THE ChatPreviewModal SHALL emit a `load-context` event with payload `{ messages: ChatMessage[], recordId: Number }` and then emit `close`
5. WHEN the `load-context` event is received by Dashboard, THE Dashboard SHALL set `chatMessages` to the payload messages, set `currentRecordId` to the payload `recordId`, and after `nextTick` focus the chat input and scroll to the bottom
6. WHEN the Dashboard receives a `close` event from ChatPreviewModal, THE Dashboard SHALL set the modal's `visible` prop to `false`
7. IF the API request in ChatPreviewModal fails, THEN THE ChatPreviewModal SHALL display an error message with a retry button and a dismiss button within the modal; clicking retry SHALL re-trigger the fetch; clicking dismiss SHALL emit `close`; THE ChatPreviewModal SHALL NOT propagate the error to the parent Dashboard component
8. WHEN ChatPreviewModal fetches a record whose `chat_history` is empty or null, THE ChatPreviewModal SHALL display an empty state message indicating no conversation history is available

---

### Requirement 14: SetupModal 升学模式 target_goal 字段

**User Story:** As a student user in education mode, I want to specify my exact target school and major as a goal, so that the AI can provide more precise career planning advice.

#### Acceptance Criteria

1. WHILE the user is in education mode (`active_mode === 'education'`), THE SetupModal SHALL display a `target_goal` input field alongside the existing `target_school` field; IF a rendering error prevents the `target_goal` field from displaying, THE SetupModal SHALL continue to display and function normally without the field
2. WHEN a user enters a value in the `target_goal` field (up to 200 characters) and saves the setup while in education mode, THE SetupModal SHALL write the trimmed value to `localStorage` under the key `target_goal`
3. WHEN SetupModal is opened and `localStorage` contains a `target_goal` value, THE SetupModal SHALL pre-fill the `target_goal` input field with that value
4. THE User_Store SHALL include a `targetGoal` state field initialized to `''`; WHEN `loadFromStorage` is called, THE User_Store SHALL read `localStorage.getItem('target_goal')` and assign it to `targetGoal`, defaulting to `''` if the key is absent; WHEN `updateUserProfile` is called with a `targetGoal` payload field, THE User_Store SHALL update the state and write to `localStorage`
5. THE `target_goal` localStorage key SHALL be stored independently from the `target_school` key and SHALL NOT overwrite or merge with `target_school`

---

### Requirement 15: Dashboard 预测看板展示 target_goal

**User Story:** As a student user, I want to see my target goal displayed in the prediction panel on the Dashboard, so that I have a constant reminder of my objective while using the platform.

#### Acceptance Criteria

1. WHEN `target_goal` is set in `localStorage` or `userStore.targetGoal` contains a non-empty value, THE Dashboard SHALL display the `target_goal` value in the header row of the "智能预测(冲稳保)" panel
2. WHEN `target_goal` is empty or not set, THE Dashboard SHALL display a placeholder prompt text in the prediction panel header row
3. WHEN a valid `target_goal` is present, THE Dashboard SHALL hide the placeholder text so that the goal value and placeholder are mutually exclusive and never displayed simultaneously
4. THE Dashboard SHALL reactively update the displayed `target_goal` value whenever `userStore.targetGoal` changes, without requiring a page reload
5. THE Dashboard SHALL derive the displayed value from a computed property that reads `localStorage.getItem('target_goal')` or `userStore.targetGoal`, trims whitespace, and evaluates to `null` if the result is empty

---

### Requirement 16: 安全约束

**User Story:** As a system operator, I want all security-sensitive operations to follow established best practices, so that user data and credentials are protected against common attack vectors.

#### Acceptance Criteria

1. THE Database SHALL use parameterized SQL queries with `?` placeholders for all SQL statements and SHALL NOT construct any SQL strings via string concatenation
2. THE Auth_Router SHALL use `passlib[bcrypt]` with a cost factor of at least 12 for password hashing and `python-jose[cryptography]` with the HS256 algorithm for JWT operations
3. THE Auth_Router SHALL read `JWT_SECRET_KEY` exclusively from the `.env` environment file via `python-dotenv`; the key SHALL be at least 32 characters long; IF the key is absent or shorter than 32 characters at startup, THE application SHALL raise a configuration error and refuse to start
4. THE Auth_Service SHALL never store plaintext passwords in `localStorage`, cookies, session storage, or any other client-side storage mechanism
5. WHEN a JWT token expires or is invalidated, THE Auth_Middleware SHALL return HTTP 401 and THE Auth_Service SHALL clear all stored credentials (`token`, `user_id`) from `localStorage`
6. IF a JWT token with a tampered payload or invalid signature is received, THEN THE Auth_Middleware SHALL return HTTP 401 with detail message "Token 已失效，请重新登录" and SHALL NOT process the request further
