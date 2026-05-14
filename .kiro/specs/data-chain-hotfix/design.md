# 设计文档：data-chain-hotfix

## 根因分析

经过代码审查，确认以下四个精确的断链点：

### Bug 1：后端 interview.py / resumeDiagnosis.py 落库时 user_id 为 NULL

**根因**：
- `Router/interview.py` 的 `/evaluate` 端点：`insert_record()` 调用完全没有 `user_id` 参数，且 `EvaluateRequest` 模型没有 `user_id` 字段，路由函数也没有注入 `get_current_user` 依赖。
- `Router/resumeDiagnosis.py` 的 `deepseek_resume_stream()` 函数：`insert_record()` 调用没有 `user_id`，且 `ResumeDiagnoseRequest` 没有 `user_id`，路由函数没有注入 `get_current_user`。
- 结果：所有面试评估和简历诊断记录的 `user_id = NULL`，`history_router.py` 的 `get_recent_records_by_user(user_id=current_user_id)` 查询用 `WHERE user_id = ?` 过滤，NULL 记录永远查不到。

**修复方案**：
1. `interview.py`：`EvaluateRequest` 添加 `user_id: Optional[int] = None`；`evaluate_interview` 路由注入 `get_optional_user` 依赖，将 `current_user_id` 写入 `request.user_id`；`insert_record()` 传入 `user_id=request.user_id`。
2. `resumeDiagnosis.py`：`ResumeDiagnoseRequest` 添加 `user_id: Optional[int] = None`；`diagnose_resume` 路由注入 `get_optional_user` 依赖，将 `current_user_id` 写入 `request.user_id`；`deepseek_resume_stream()` 接收 `user_id` 参数并传给 `insert_record()`。

### Bug 2：前端 PremiumInterview.vue 保存历史记录时 user_id 已由 JWT 头携带，但 evaluate 端点不读取

这是 Bug 1 的前端侧表现。前端已在 Task 3/4 中添加了 `getAuthHeaders()`，但后端 `/evaluate` 端点没有注入 `get_optional_user`，所以 token 被忽略了。修复见 Bug 1。

### Bug 3：Dashboard.vue sendGeneralChatMessage 漏传 target_job

**根因**：`sendGeneralChatMessage` 构建 payload 时，只传了 `resume_text` 和 `jd_text`，没有传 `target_job`。`agent_dispatcher.py` 的 `build_user_prompt` 函数有 `jd_text` 段落但没有独立的 `target_job` 字段。

**修复方案**：在 `sendGeneralChatMessage` 的 payload 构建中，添加 `payload.target_job = userStore.targetJob || localStorage.getItem('target_job') || ''`，并在 `AgentChatRequest` 模型中添加 `target_job: Optional[str] = ""`，在 `build_user_prompt` 中注入到 prompt。

### Bug 4：PremiumInterview.vue startInterviewWithDifficulty 漏传 target_job 字段名

**根因**：`startInterviewWithDifficulty` 发送的 payload 中，目标岗位字段名是 `jd_text`（JD），但没有单独的 `target_job` 字段。后端 `build_messages` 中 `jd_section` 只拼接 JD，没有单独的目标岗位行。

**修复方案**：`ChatRequest` 添加 `target_job: Optional[str] = ""`；`build_messages` 在 system prompt 中拼接目标岗位；前端 `startInterviewWithDifficulty` 和 `sendMessage` 的 payload 中加入 `target_job: targetRole.value`。

### Bug 5：时间戳裸奔（已在上轮修复，验证即可）

上轮已将 `sendMessage` 中的 `timestamp: Date.now()` 改为 `toLocaleTimeString`。本轮只需确认没有其他遗漏点。

## 修复范围（精确文件列表）

| 文件 | 修改内容 |
|------|---------|
| `Router/interview.py` | `EvaluateRequest` 加 `user_id`；路由注入 `get_optional_user`；`insert_record` 传 `user_id` |
| `Router/resumeDiagnosis.py` | `ResumeDiagnoseRequest` 加 `user_id`；路由注入 `get_optional_user`；`deepseek_resume_stream` 传 `user_id` |
| `Router/agent_dispatcher.py` | `AgentChatRequest` 加 `target_job`；`build_user_prompt` 注入目标岗位 |
| `Router/interview.py` | `ChatRequest` 加 `target_job`；`build_messages` 注入目标岗位 |
| `frontend/src/Dashboard.vue` | `sendGeneralChatMessage` 加 `target_job` 字段 |
| `frontend/src/PremiumInterview.vue` | `startInterviewWithDifficulty` 加 `target_job` 字段 |

## 铁律

- 不修改数据库表结构（`user_id` 列已存在）
- 不修改 Dashboard Bento UI HTML 结构
- 不运行 `vue-tsc` 或 `vite build`
- 使用 `get_optional_user`（不是 `get_current_user`），保持游客兼容性
