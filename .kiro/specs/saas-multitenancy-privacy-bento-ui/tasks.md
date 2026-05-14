# Implementation Plan: SaaS 多租户隐私隔离 + Bento UI 响应式数据链路

## Overview

分三个阶段实现：
1. **阶段一** — 后端 JWT 鉴权与数据隔离（`database.py` schema 升级、`Router/auth.py`、`Router/dependencies.py`、`history_router.py` 隔离、`agent_dispatcher.py` 注入 `user_id`、`main.py` 注册路由）
2. **阶段二** — Bento 面板响应式数据链路（`userStore.js` pinned ID 状态、`DataSourceModal.vue` Tab 过滤、`CyberRadarChart.vue` 动态绑定、`Dashboard.vue` 防抖 watch）
3. **阶段三** — UI/UX 补全（`CustomDropdown.vue`、`ChatPreviewModal.vue`、`SetupModal.vue` target_goal、Dashboard 预测看板展示 target_goal、路由守卫收窄、`Auth.vue` 注册/登录页、`authService.js`）

---

## Tasks

- [x] 1. 升级数据库 Schema（users 表 + user_id 列迁移）
  - [x] 1.1 在 `database.py` 的 `init_db()` 中新增 `users` 表创建语句（`CREATE TABLE IF NOT EXISTS`），字段：`id INTEGER PRIMARY KEY AUTOINCREMENT`、`username TEXT UNIQUE NOT NULL`、`password_hash TEXT NOT NULL`、`email TEXT`、`created_at TEXT`
    - 使用 `CREATE TABLE IF NOT EXISTS` 保证幂等，不破坏已有数据
    - _Requirements: 5.1, 5.2_
  - [x] 1.2 在 `init_db()` 中为 `history_records` 表添加 `user_id INTEGER` 列（`ALTER TABLE ... ADD COLUMN`，用 try/except 跳过已存在的情况），并新增 `CREATE INDEX IF NOT EXISTS idx_history_user_id ON history_records(user_id)` 索引
    - 存量记录 `user_id` 默认为 `NULL`，向后兼容
    - _Requirements: 4.1, 5.3, 5.4_
  - [x] 1.3 在 `database.py` 中实现 `create_user(username, password_hash, email=None) -> int`、`get_user_by_username(username) -> Optional[dict]`、`get_recent_records_by_user(user_id, limit=10, **filters) -> list` 三个函数
    - `get_recent_records_by_user` 的 SQL 必须包含 `WHERE user_id = ?`，使用参数化占位符，严禁字符串拼接
    - _Requirements: 4.3, 5.5, 5.6_
  - [x] 1.4 为 `get_recent_records_by_user` 编写 Hypothesis 属性测试
    - **Property 1: 用户数据隔离不变量** — 对任意合法 `user_id`，返回的所有记录的 `user_id` 字
    段均等于输入值
    - **Validates: Requirements 4.3, 4.4**

- [x] 2. 实现后端 JWT 鉴权路由（Router/auth.py）
  - [x] 2.1 新建 `Router/auth.py`，实现 `POST /api/auth/register` 端点：校验用户名（1-50 字符，字母数字下划线）和密码（≥8 字符），用 `passlib[bcrypt]` hash 密码后调用 `create_user()`，返回 `access_token`、`user_id`、`username`；用户名重复时返回 HTTP 409
    - 使用 `passlib.context.CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)`
    - 格式不合法时返回 HTTP 422，不创建任何用户记录
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - [x] 2.2 在 `Router/auth.py` 中实现 `POST /api/auth/login` 端点：查询用户、bcrypt 校验密码、签发 JWT（`python-jose` HS256，7 天有效期，payload 含 `user_id` 和 `username`），任何失败均返回 HTTP 401
    - 从 `.env` 读取 `JWT_SECRET_KEY`（≥32 字符），启动时若缺失或过短则抛出配置错误
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 16.2, 16.3_
  - [x] 2.3 为 JWT 签发与解码编写 Hypothesis 属性测试
    - **Property 8: JWT 签发与解码往返不变量** — 对任意合法 `user_id`，签发的 token 经解码后必须返回相同的 `user_id`
    - **Validates: Requirements 2.3, 3.1**
  - [x] 2.4 为密码安全编写 Hypothesis 属性测试
    - **Property 2: 密码安全不变量** — 对任意明文密码，`create_user` 写入的 `password_hash` 永远不等于明文；`bcrypt.verify` 是唯一合法校验路径
    - **Validates: Requirements 1.4, 16.4**

- [x] 3. 实现 JWT 鉴权依赖注入（Router/dependencies.py）
  - [x] 3.1 新建 `Router/dependencies.py`，实现 `get_current_user(token: str = Depends(oauth2_scheme)) -> int`：解码 JWT，校验签名、有效期、`user_id` 为正整数；token 缺失返回 HTTP 401 "未提供认证凭据"；token 无效/过期返回 HTTP 401 "Token 已失效，请重新登录"
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 3.2 在 `Router/dependencies.py` 中实现 `get_optional_user(token: Optional[str] = Depends(optional_oauth2_scheme)) -> Optional[int]`：token 存在则校验并返回 `user_id`，不存在则返回 `None`（不抛出异常）
    - _Requirements: 3.5, 3.6_

- [ ] 4. 历史记录路由隔离（history_router.py + agent_dispatcher.py）
  - [x] 4.1 修改 `Router/history_router.py`：在所有端点注入 `Depends(get_current_user)`，将 `get_recent_records` 替换为 `get_recent_records_by_user(user_id=current_user_id)`；`GET /{record_id}` 和 `DELETE /{record_id}` 在操作前校验记录的 `user_id` 是否匹配，不匹配返回 HTTP 403
    - _Requirements: 4.2, 4.3, 4.4, 4.5_
  - [x] 4.2 修改 `Router/agent_dispatcher.py`：在 `AgentChatRequest` 中新增可选 `user_id: Optional[int] = None` 字段，在 `stream_llm_response` 的 `insert_record` 调用中传入 `user_id`；修改 `/api/agent/chat` 端点注入 `Depends(get_optional_user)` 并将 `user_id` 传入请求处理函数
    - _Requirements: 4.2_
  - [x] 4.3 在 `main.py` 中注册 `auth.router`（`from Router import auth`，`app.include_router(auth.router)`）
    - _Requirements: 2.1, 2.2_

- [~] 5. 阶段一检查点
  - 确保所有后端测试通过，`uvicorn main:app --reload` 启动无报错，`/api/auth/register` 和 `/api/auth/login` 端点可正常响应，ask the user if questions arise.

- [x] 6. 前端鉴权服务（authService.js）与 Auth.vue 页面
  - [~] 6.1 新建 `frontend/src/services/authService.js`，实现 `registerUser(username, password, email)`、`loginUser(username, password)`（成功后写入 `localStorage` 的 `token` 和 `user_id`）、`getAuthHeaders()`（返回 `{ Authorization: "Bearer <token>" }` 或空对象）、`logout()`（清除 `token`/`user_id`，调用 `userStore.updateUserProfile({})` 重置画像）
    - 非 2xx 响应时抛出含 `detail` 消息的 Error，供组件展示
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 16.4_
  - [~] 6.2 新建或修改 `frontend/src/Auth.vue`：实现注册/登录双 Tab 表单（用户名、密码、可选邮箱），调用 `authService.js` 对应函数，成功后跳转 `/dashboard`，失败时展示错误 Toast；表单遵循深色赛博朋克风格
    - _Requirements: 2.5, 7.1, 7.2_
  - [~] 6.3 升级 `frontend/src/router/index.js` 路由守卫：`userRole === 'guest'` 仅允许访问 `/` 和 `/auth`，其余受保护路由一律重定向至 `/auth`；有效 `token` 时放行所有受保护路由
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. userStore Pinned ID 状态管理
  - [~] 7.1 在 `frontend/src/stores/userStore.js` 的 `state` 中新增 `pinnedResumeId: null`、`pinnedInterviewId: null`、`pinnedCareerId: null`、`targetGoal: ''` 四个字段
    - _Requirements: 8.1, 14.4_
  - [~] 7.2 在 `userStore.js` 的 `actions` 中实现 `setPinnedId(tab, recordId)`：更新对应字段并写入 `localStorage`（键名 `pinned_resume_id` / `pinned_interview_id` / `pinned_career_id`）；`recordId` 为 `null` 时移除对应 `localStorage` 键；未知 `tab` 值时静默忽略
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.9_
  - [~] 7.3 在 `userStore.js` 的 `actions` 中实现 `loadPinnedIds()`：从 `localStorage` 读取三个 pinned ID 键并恢复对应字段；键不存在时保持 `null`；整个函数用 try/catch 包裹，异常时静默处理
    - 在 `loadFromStorage()` 末尾调用 `this.loadPinnedIds()`
    - _Requirements: 8.6, 8.7_
  - [~] 7.4 在 `userStore.js` 的 `getters` 中实现 `getPinnedIdByTab(tab)`：返回对应 `pinnedId`；未知 `tab` 返回 `null`
    - 同时在 `updateUserProfile` 和 `loadFromStorage` 中处理 `targetGoal` 字段（读写 `localStorage` 键 `target_goal`）
    - _Requirements: 8.8, 14.4_
  - [~] 7.5 为 `setPinnedId` + `loadPinnedIds` 编写 Hypothesis 属性测试
    - **Property 9: Pinned ID 持久化往返不变量** — 对任意 tab 和 recordId，`setPinnedId` 后再 `loadPinnedIds`，对应 tab 的 `pinnedId` 必须等于原始 `recordId`
    - **Validates: Requirements 8.3, 8.5**
  - [~] 7.6 为 `setPinnedId` 编写属性测试验证 Tab 隔离
    - **Property 6: localStorage 键名隔离不变量** — 对单个 Tab 的 `setPinnedId` 调用，其他两个 Tab 的 `pinnedId` 不变；`target_goal` 与 `target_school` 独立存储
    - **Validates: Requirements 8.4, 14.4**

- [x] 8. DataSourceModal Tab 过滤
  - [~] 8.1 修改 `frontend/src/components/DataSourceModal.vue`：新增 `activeTab` prop（String，取值 `'resume'`/`'interview'`/`'career'`），实现 `computed filteredByTab`：`resume` → `category === 'resume_diagnosis'`；`interview` → `category.startsWith('interview')`；`career` → `category === 'career_planning'`；无有效 scores 的记录用灰显样式或"无评分"徽章区分，但仍显示
    - _Requirements: 9.1, 9.2, 9.5_
  - [~] 8.2 修改 `frontend/src/Dashboard.vue`：在 `DataSourceModal` 的 `select` 事件处理函数中调用 `userStore.setPinnedId(activeDataTab.value, record.id)`；向 `DataSourceModal` 传入 `:activeTab="activeDataTab"`
    - _Requirements: 9.3, 9.4_
  - [~] 8.3 为 DataSourceModal 过滤逻辑编写属性测试
    - **Property 10: DataSourceModal Tab 过滤不变量** — 对任意历史记录集合和任意 `activeTab`，过滤后所有记录的 `category` 必须符合该 Tab 的映射规则
    - **Validates: Requirements 9.1, 9.2**

- [x] 9. 雷达图动态数据绑定
  - [~] 9.1 修改 `frontend/src/Dashboard.vue`：新增 `watch(activeDataTab, ...)` 和 `watch(() => userStore.getPinnedIdByTab(activeDataTab.value), ...)`，使用 `@vueuse/core` 的 `useDebounceFn`（300ms）防抖触发 `fetchPinnedRadarData(tab, pinnedId)`；`pinnedId` 为 `null` 时调用 `userStore.resetRadarData()`；fetch 失败时保留现有 `radarData` 并显示错误提示，不重置为零
    - 使用 `AbortController` 取消前一个未完成的请求
    - _Requirements: 10.1, 10.2, 10.3, 10.7_
  - [~] 9.2 修改 `frontend/src/Dashboard.vue`：`activeDataTab` 切换时触发雷达图数据更新，使用新 Tab 的 `pinnedId` 对应记录
    - _Requirements: 10.3_
  - [~] 9.3 为 `updateRadarData` 编写 Hypothesis 属性测试
    - **Property 3: 雷达图数值 clamp 不变量** — 对任意 `scores` 字典，`updateRadarData` 后 `radarData.values` 中每个值 `v` 满足 `0 ≤ v ≤ 100`
    - **Validates: Requirements 10.4, 10.6**
  - [~] 9.4 为空状态编写属性测试
    - **Property 4: 空状态不变量** — 当 `pinnedId === null` 且所有分值为零时，`radarData.values` 必须为 `[0,0,0,0,0,0]`，雷达图显示"暂无数据"提示
    - **Validates: Requirements 10.3, 10.4**
  - [~] 9.5 为 Tab 数据绑定编写属性测试
    - **Property 5: Tab 数据绑定不变量** — 任意 `activeDataTab` 切换后，雷达图数据必须对应新 Tab 的 `pinnedId` 所指向的记录，不得显示其他 Tab 的数据
    - **Validates: Requirements 10.2**

- [~] 10. 阶段二检查点
  - 确保 DataSourceModal 按 Tab 正确过滤，选中记录后雷达图响应更新，pinned ID 刷新页面后仍能恢复，ask the user if questions arise.

- [x] 11. CustomDropdown 自定义下拉组件
  - [~] 11.1 新建 `frontend/src/components/CustomDropdown.vue`：接受 `modelValue`（String）、`options`（Array of `{ value, label }`）、`placeholder`（String）props，emit `update:modelValue`；内部维护 `isOpen` 状态；点击触发按钮切换开关；点击选项时 emit 新值并关闭；`options` 为空时显示空面板不报错
    - 样式：触发按钮 `bg-white/5 border border-white/10 rounded-lg`；面板 `bg-gray-900 border border-white/10 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.5)]`；悬停 `hover:bg-white/5`；选中项 `text-purple-300 bg-purple-500/10`；过渡 `opacity 0.2s, transform 0.2s`
    - _Requirements: 11.1, 11.2, 11.5, 11.6, 11.7, 11.8_
  - [~] 11.2 在 `CustomDropdown.vue` 中使用 `@vueuse/core` 的 `onClickOutside` 检测外部点击关闭面板，并监听 `keydown` 事件在 ESC 键时关闭面板
    - _Requirements: 11.3, 11.4_
  - [~] 11.3 修改 `frontend/src/HistoryArchive.vue`：将所有原生 `<select>` 替换为 `<CustomDropdown>`；修正"面试评估"过滤为 `category.startsWith('interview')`；新增"Agent 对话"选项（value: `agent_`，过滤为 `category.startsWith('agent_')`）；所有分类标签使用 `font-bold`
    - _Requirements: 11.9, 12.1, 12.2, 12.3, 12.4_
  - [~] 11.4 为 CustomDropdown 编写属性测试
    - **Property 7: 自定义下拉关闭不变量** — 处于打开状态时，点击外部区域或按 ESC 键后，`isOpen` 必须变为 `false`
    - **Validates: Requirements 11.3, 11.4**

- [x] 12. ChatPreviewModal Agent 对话预览弹窗
  - [~] 12.1 新建 `frontend/src/components/ChatPreviewModal.vue`：接受 `visible`（Boolean）、`recordId`（Number）props，emit `close` 和 `load-context`；`visible` 变为 `true` 且 `recordId` 为正整数时自动 fetch `/api/history/{recordId}`，展示加载指示器；`chat_history` 为空时显示空状态提示
    - _Requirements: 13.1, 13.2, 13.8_
  - [~] 12.2 在 `ChatPreviewModal.vue` 中渲染气泡对话列表：用户消息右对齐（`bg-purple-500/20 border border-purple-500/30 rounded-2xl rounded-tr-sm`），AI 消息左对齐（`bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm`）；"✨ 载入上下文并继续对话"按钮（`bg-gradient-to-r from-cyan-500 to-purple-600`）点击后 emit `load-context` 并 emit `close`
    - _Requirements: 13.3, 13.4_
  - [~] 12.3 在 `ChatPreviewModal.vue` 中处理 fetch 失败：显示错误消息 + 重试按钮 + 关闭按钮；重试触发重新 fetch；关闭 emit `close`；不向父组件传播错误
    - _Requirements: 13.7_
  - [~] 12.4 修改 `frontend/src/Dashboard.vue`：导入并注册 `ChatPreviewModal`；点击 `category.startsWith('agent_')` 的历史记录卡片时打开 `ChatPreviewModal`（`visible=true`，传入 `recordId`）；接收 `load-context` 事件后设置 `chatMessages`、`currentRecordId`，`nextTick` 后 focus 输入框并滚动到底部；接收 `close` 事件后关闭弹窗
    - _Requirements: 13.1, 13.5, 13.6_

- [x] 13. SetupModal target_goal 字段 + Dashboard 预测看板
  - [~] 13.1 修改 `frontend/src/components/SetupModal.vue`：升学模式（`active_mode === 'education'`）下新增 `target_goal` 输入框（最多 200 字符），采用左右两栏布局；打开时从 `localStorage` 预填；保存时将 trimmed 值写入 `localStorage` 键 `target_goal`；渲染错误时降级处理，不影响其他字段
    - _Requirements: 14.1, 14.2, 14.3, 14.5_
  - [~] 13.2 修改 `frontend/src/Dashboard.vue`：新增 `computed targetGoalDisplay`（读取 `localStorage.getItem('target_goal')` 或 `userStore.targetGoal`，trim 后为空则返回 `null`）；在"智能预测(冲稳保)"看板顶部展示 `target_goal`，有值时隐藏占位提示文字，无值时显示占位提示；响应式更新（watch `userStore.targetGoal`）
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [~] 14. 最终检查点
  - 确保所有测试通过，三个阶段功能端到端联通（注册→登录→Dashboard 数据隔离→Bento 雷达图响应→UI 组件深色化），ask the user if questions arise.

---

## Notes

- 标注 `*` 的子任务为可选测试任务，可跳过以加快 MVP 交付
- 所有 Hypothesis 属性测试放在 `tests/` 目录下，文件命名如 `test_pbt_auth.py`、`test_pbt_store.py`
- 后端所有 SQL 查询必须使用参数化 `?` 占位符，禁止字符串拼接（Requirements 5.5, 5.6, 16.1）
- `JWT_SECRET_KEY` 必须从 `.env` 读取，长度 ≥ 32 字符，启动时校验（Requirements 16.3）
- 前端 `localStorage` 中永远不存储明文密码（Requirements 16.4）
- `DataSourceModal.vue` 实际位于 `frontend/src/components/DataSourceModal.vue`
- `SetupModal.vue` 实际位于 `frontend/src/components/SetupModal.vue`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["1.4", "2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "3.1"] },
    { "id": 4, "tasks": ["3.2", "4.1", "4.2"] },
    { "id": 5, "tasks": ["4.3"] },
    { "id": 6, "tasks": ["6.1"] },
    { "id": 7, "tasks": ["6.2", "6.3", "7.1"] },
    { "id": 8, "tasks": ["7.2", "7.3"] },
    { "id": 9, "tasks": ["7.4"] },
    { "id": 10, "tasks": ["7.5", "7.6", "8.1"] },
    { "id": 11, "tasks": ["8.2"] },
    { "id": 12, "tasks": ["8.3", "9.1"] },
    { "id": 13, "tasks": ["9.2", "9.3", "9.4", "9.5", "11.1"] },
    { "id": 14, "tasks": ["11.2", "12.1"] },
    { "id": 15, "tasks": ["11.3", "12.2", "12.3"] },
    { "id": 16, "tasks": ["11.4", "12.4", "13.1"] },
    { "id": 17, "tasks": ["13.2"] }
  ]
}
```
