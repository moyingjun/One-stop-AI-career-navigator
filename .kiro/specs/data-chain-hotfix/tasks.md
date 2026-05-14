# Implementation Plan: data-chain-hotfix

## Tasks

- [ ] 1. 修复 interview.py 评估端点的 user_id 落库
  - 在 `EvaluateRequest` 模型中添加 `user_id: Optional[int] = None` 字段
  - 在 `evaluate_interview` 路由函数签名中注入 `get_optional_user` 依赖：`current_user_id: Optional[int] = Depends(get_optional_user)`
  - 在路由函数体中将 `current_user_id` 赋给 `request.user_id`
  - 在 `insert_record()` 调用中添加 `user_id=request.user_id` 参数
  - 在文件顶部添加 `from Router.dependencies import get_optional_user` 和 `from fastapi import Depends` 导入
  - **涉及文件**：`Router/interview.py`

- [ ] 2. 修复 resumeDiagnosis.py 诊断端点的 user_id 落库
  - 在 `ResumeDiagnoseRequest` 模型中添加 `user_id: Optional[int] = None` 字段
  - 修改 `deepseek_resume_stream` 函数签名，添加 `user_id: Optional[int] = None` 参数
  - 在 `deepseek_resume_stream` 的 `insert_record()` 调用中添加 `user_id=user_id` 参数
  - 在 `diagnose_resume` 路由函数签名中注入 `get_optional_user` 依赖：`current_user_id: Optional[int] = Depends(get_optional_user)`
  - 在路由函数体中将 `current_user_id` 赋给 `request.user_id`，并在调用 `deepseek_resume_stream` 时传入 `user_id=request.user_id`
  - 在文件顶部添加 `from Router.dependencies import get_optional_user` 和 `from fastapi import Depends` 导入
  - **涉及文件**：`Router/resumeDiagnosis.py`

- [ ] 3. 修复 interview.py ChatRequest 和 build_messages 注入 target_job
  - 在 `ChatRequest` 模型中添加 `target_job: Optional[str] = ""` 字段
  - 在 `build_messages` 函数中，在 `resume_section` 之后添加 `target_job_section`：若 `request.target_job` 非空，则拼接 `f"候选人的目标岗位是：{request.target_job.strip()}"` 到 `context_prefix`
  - **涉及文件**：`Router/interview.py`

- [ ] 4. 修复 agent_dispatcher.py AgentChatRequest 注入 target_job 到 prompt
  - 在 `AgentChatRequest` 模型中添加 `target_job: Optional[str] = ""` 字段
  - 在 `build_user_prompt` 函数中，在 `resume_text` 段落之后，若 `request.target_job` 非空，添加 `sections.append(f"【求职意向/目标岗位】\n{request.target_job.strip()}")`
  - **涉及文件**：`Router/agent_dispatcher.py`

- [ ] 5. 修复 Dashboard.vue sendGeneralChatMessage 补传 target_job
  - 在 `sendGeneralChatMessage` 函数的 payload 构建区域（`savedJd` 之后），添加：`const targetJob = userStore.targetJob || localStorage.getItem('target_job') || ''; if (targetJob) payload.target_job = targetJob`
  - **涉及文件**：`frontend/src/Dashboard.vue`

- [ ] 6. 修复 PremiumInterview.vue startInterviewWithDifficulty 补传 target_job
  - 在 `startInterviewWithDifficulty` 函数的 fetch payload 中，添加 `target_job: targetRole.value` 字段（与 `resume_text`、`jd_text` 并列）
  - **涉及文件**：`frontend/src/PremiumInterview.vue`

## Task Dependency Graph

```json
{
  "waves": [
    [1, 2, 3, 4, 5, 6]
  ]
}
```

## Notes

- 使用 `get_optional_user`（非 `get_current_user`），保持游客兼容性，user_id 可为 None
- 不修改数据库表结构
- 不修改 Dashboard Bento UI HTML 结构
- 不运行 vue-tsc 或 vite build
