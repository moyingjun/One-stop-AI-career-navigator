# 多模型动态路由 — 任务清单

> ⚠️ 本文档列出**未来任务**，全部标记为 `[ ]`，当前**均未实施**。
> AI Agent 阅读时请勿勾选任何任务，也不要据此修改业务代码。

---

## Phase 0 — 当前已落地基础设施

> 这些不是本 spec 的任务，仅作为基线参考：

- LLM 配置统一为 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_NAME`（Settings/config.py 双位置）
- `llm_client.py` 三层防波堤（JSON 失败 / choices 越界 / 顶层异常 → `[系统异常]` 兜底）
- `[DONE]` 标记正确处理，`tool_calls` 等非文本 chunk 安全跳过
- 切换模型方式：修改 `.env` + 重启服务

---

## Phase 1 — 后端 Provider 注册表与管理 API

### 数据层
- [ ] 新建 `Service/Utils/databases/models/llm_provider_model.py`（`LlmProvider` ORM）
- [ ] `Service/Utils/databases/models/__init__.py` 注册 `LlmProvider` 到 `Base.metadata`
- [ ] Alembic autogenerate migration：`add_llm_providers_table`
- [ ] `main.py` lifespan：表为空时用 `LLM_*` 环境变量插入种子数据

### 服务层
- [ ] `Service/Utils/llm_client.py` `stream_chat()` / `complete_chat()` 新增可选 `provider_id, db` 参数
- [ ] 实现 `_resolve_provider(db, provider_id)` 查询函数
- [ ] 不传 `provider_id` 时完全保持现行行为（向后兼容）
- [ ] 现有调用方（4 个 Agent + 2 个 Service）零改动验证

### 管理 API
- [ ] 新建 `Router/admin_llm_providers.py`：CRUD + set-default
- [ ] `users` 表新增 `role` 字段 + 管理员鉴权依赖
- [ ] 响应过滤：`api_key` 脱敏（前 3 + 后 4，中间 ***）
- [ ] `PATCH /set-default` 原子事务：先全部置 false，再设新默认
- [ ] DELETE 前置校验：禁止删除 `is_default=true` 的 Provider

### 公开 API
- [ ] 新建 `Router/llm_providers_public.py`：`GET /api/llm-providers/active`
- [ ] 响应字段白名单：仅 `{ id, name, model_name, status }`
- [ ] 自动过滤 `is_active=false` 和 `status=down` 的 Provider

### 验收
- [ ] 现有功能（Dashboard chat / 简历诊断 / 模拟面试 / 职业规划）回归测试通过
- [ ] 新增 Provider 后通过 set-default 切换默认，重启服务前后行为对齐

---

## Phase 2 — Dashboard 模型选择器

### 前端 Pinia
- [ ] 新建 `frontend/src/stores/llmProviderStore.js`
  - state: `providerList`、`currentProviderId`
  - action: `fetchProviders()`、`setCurrentProvider(id)`
  - getter: `currentProvider`
  - 字段白名单过滤（即使后端返回了 api_key，前端也丢弃）

### 前端 UI
- [ ] `frontend/src/main.js` 启动时调用 `llmProviderStore.fetchProviders()`
- [ ] `frontend/src/Dashboard.vue` 顶部状态徽章替换为下拉
  - 复用 `CustomDropdown` 组件
  - 显示 `name + model_name + status 圆点`
  - 暗黑赛博风格，与现有徽章视觉对齐
- [ ] 游客模式禁用下拉，强制显示"系统默认"

### 请求体扩展
- [ ] `Router/models/agent_model.py` `AgentChatRequest` 新增 `provider_id: Optional[int] = None`
- [ ] `Router/models/interview_model.py` `ChatRequest` / `EvaluateRequest` 同上
- [ ] `Router/agent_dispatcher.py` 透传 `provider_id` 到 `stream_dispatcher_response()`
- [ ] `Router/interview.py` 透传 `provider_id`
- [ ] `frontend/src/services/llm_service.js` 自动附加 `provider_id` 到所有 SSE 请求 body

### 验收
- [ ] 用户选择 Provider A → 后续对话使用 A
- [ ] 切换 Provider B → 后续对话使用 B
- [ ] F5 后从 localStorage 恢复 `currentProviderId`
- [ ] 游客模式下下拉禁用

---

## Phase 3 — Fallback、健康检查、自动切换

### 健康检查
- [ ] 新建 `Service/Tasks/llm_health_checker.py`
- [ ] FastAPI lifespan 启动后台 asyncio.Task（60 秒轮询）
- [ ] 探测请求：最小化 prompt（`messages=[{role:'user', content:'ping'}]`，max_tokens=1）
- [ ] 状态机：`healthy → down`（连续 3 次失败）/ `down → healthy`（任一次成功）
- [ ] 写入 `llm_providers.status`

### Fallback 路由
- [ ] `Service/Utils/llm_client.py` 新增 `stream_chat_with_fallback()` 包装函数
- [ ] 失败重试上限：3 次
- [ ] 触发 fallback 时通过 SSE `event: warning` 通知前端：`"已自动切换至备用模型 X"`
- [ ] 优先级：用户手动选择 > `provider_id` 参数 > `is_default=true`

### 监控
- [ ] 新建 `logs/llm_fallback.log` 记录 fallback 事件
- [ ] 管理员后台展示：每 Provider 24h 成功率、Fallback TOP 5、平均响应时间

### 验收
- [ ] 主 Provider down 时自动切换至备用，前端收到 warning
- [ ] 所有 Provider 都 down 时 SSE 返回 error 事件
- [ ] 用户选择被尊重：选中 A 失败时 fallback 但不修改 `currentProviderId`

---

## 风险与约束

| 风险 | 缓解措施 |
|---|---|
| API Key 泄露至前端 | 公开接口字段白名单 + Pinia Store 白名单过滤 |
| Phase 1 Migration 破坏生产 | 仅新增表，不修改现有结构；表为空时种子数据保证行为不变 |
| Phase 2 调用方改动遗漏 | `provider_id=None` 时完全兼容，遗漏调用方走默认 Provider |
| Phase 3 健康检查频繁请求 | 探测使用 `max_tokens=1`、低频（60s）、可由管理员暂停 |
| Fallback 触发雪崩 | 单次请求最多 3 次重试，连续失败累计后置 down |

---

## 前置条件

| 阶段 | 前置 |
|---|---|
| Phase 1 | 已经有可用的 Alembic 配置（`alembic.ini` + `alembic/env.py`） |
| Phase 2 | Phase 1 公开接口已稳定，至少 2 个 Provider 在数据库中 |
| Phase 3 | Phase 2 已上线，前端已能感知 Provider 切换 |

---

## 不在本 spec 范围

- 修改 `llm_client.py` 当前实现（三层防波堤已正确）
- 修改 `Settings/config.py`（`LLM_*` 命名已正确）
- 修改 Dashboard 当前 UI（除非进入 Phase 2）
- 修改 `tech.md` / `structure.md`（steering 反映当前真实架构，不写未来规划）
