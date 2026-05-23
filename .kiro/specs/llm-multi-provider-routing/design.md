# 多模型动态路由 — 技术设计文档

> ⚠️ 本文档描述**未来实现方案**，当前业务代码与本设计无关。
> 任何对 `llm_client.py` / Dashboard.vue 的改动都**不属于本 spec 范围**。

---

## 当前真实架构（基线）

```
.env
  └── LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME
       ↓
Settings/config.py（双位置：根 + Service/）
       ↓
Service/Utils/llm_client.py
  └── stream_chat(messages, ...)        # 全局共用一个 Provider
  └── complete_chat(messages, ...)      # 全局共用一个 Provider
       ↓
所有 Agent / Service 调用方
```

**当前 stream_chat 不接受 provider_id 参数。** 切换模型需要修改 `.env` 并重启服务。

---

## Phase 1 — 后端 Provider 注册表（未实现）

### ORM 模型设计

```python
# Service/Utils/databases/models/llm_provider_model.py（未来新增）
class LlmProvider(Base):
    __tablename__ = "llm_providers"

    id:         Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:       Mapped[str]  = mapped_column(String(128), nullable=False, unique=True)
    base_url:   Mapped[str]  = mapped_column(String(512), nullable=False)
    api_key:    Mapped[str]  = mapped_column(String(512), nullable=False)
    model_name: Mapped[str]  = mapped_column(String(128), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status:     Mapped[str]  = mapped_column(String(32), nullable=False, default="healthy")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### 种子数据策略

- 服务启动时（`main.py` lifespan）检查 `llm_providers` 表是否为空
- 若为空：用当前 `LLM_*` 环境变量插入一条 `is_default=true, is_active=true, status=healthy` 的默认 Provider
- 这保证 Phase 1 上线后行为与 Phase 0（当前）完全一致

### llm_client 扩展（向后兼容）

```python
# Service/Utils/llm_client.py（未来扩展，当前保持不变）
async def stream_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 120.0,
    provider_id: Optional[int] = None,    # 新增
    db: Optional[AsyncSession] = None,    # 新增
) -> AsyncGenerator[str, None]:
    if provider_id is not None and db is not None:
        provider = await _resolve_provider(db, provider_id)
        api_key, base_url, model_name = provider.api_key, provider.base_url, provider.model_name
    else:
        # 完全兼容现状：不传 provider_id 时走环境变量
        api_key, base_url, model_name = LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME

    # 后续逻辑与当前完全一致
    ...
```

**关键约束**：所有现有调用方（dispatcher_agent / interview_agent / resume_agent / career_agent）
不传 `provider_id`，自动走环境变量，**无需任何改动**。

### 管理 API 路由

- `Router/admin_llm_providers.py`（未来新增）
  - 强依赖管理员角色（用户表需要 `role` 字段，目前没有）
  - 响应中 `api_key` 字段必须脱敏：`"sk-...wxyz"`（保留前 3 + 后 4，中间 ...）
  - DELETE 操作：禁止删除 `is_default=true` 的 Provider
  - PATCH set-default：原子操作，先把所有 Provider 的 is_default 设为 false，再设新默认

### 公开 API 路由

- `Router/llm_providers_public.py`（未来新增）
  - `GET /api/llm-providers/active` — 仅返回 `is_active=true and status != 'down'` 的 Provider
  - 响应字段白名单（**严格**）：`id`、`name`、`model_name`、`status`
  - **响应中绝不出现** `api_key`、`base_url`、`is_default`

---

## Phase 2 — Dashboard 模型选择器（未实现）

### Pinia Store 结构

```js
// frontend/src/stores/llmProviderStore.js（未来新增）
export const useLlmProviderStore = defineStore('llmProvider', {
  state: () => ({
    providerList: [],          // 形如 [{ id, name, model_name, status }]
    currentProviderId: null    // null = 使用服务端默认
  }),
  getters: {
    currentProvider: (state) =>
      state.providerList.find(p => p.id === state.currentProviderId) || null
  },
  actions: {
    async fetchProviders() {
      const res = await fetch('/api/llm-providers/active', { headers: { ...getAuthHeaders() } })
      if (res.ok) {
        const data = await res.json()
        this.providerList = data.records || []
      }
    },
    setCurrentProvider(id) {
      this.currentProviderId = id
      try { localStorage.setItem('llm_provider_id', String(id)) } catch {}
    }
  }
})
```

**前端永远不存储 `api_key`。** 即使后端返回了，Pinia Store 在 `fetchProviders` 中也应做白名单过滤。

### Dashboard UI 集成点

- 位置：顶部状态栏 `<DeepSeek V4 Online>` 徽章替换为下拉选择器
- 组件：复用 `<CustomDropdown>`（已存在），接 `providerList`
- 选项渲染：`{ name } · { model_name }` + status 圆点
- 选中后：调用 `llmProviderStore.setCurrentProvider(id)`

### 请求体扩展

```js
// frontend/src/services/llm_service.js（未来扩展）
async function streamChat({ endpoint, payload, ... }) {
  const provider = useLlmProviderStore().currentProviderId
  const finalPayload = provider ? { ...payload, provider_id: provider } : payload
  // 后续逻辑不变
}
```

后端 `AgentChatRequest` 新增 `provider_id: Optional[int] = None`，透传到 `stream_chat()`。

---

## Phase 3 — Fallback、健康检查、自动切换（未实现）

### 健康检查任务

- 实现位置：`Service/Tasks/llm_health_checker.py`（未来新增）
- 触发方式：FastAPI lifespan 启动后台 asyncio.Task，每 60 秒轮询所有 `is_active=true` 的 Provider
- 探测请求：`stream=False, max_tokens=1, messages=[{role:'user', content:'ping'}]`
- 状态机：
  ```
  healthy ──连续3次失败──▶ down
  down ────任意一次成功──▶ healthy
  healthy ──部分失败──▶ degraded（响应慢但能返回）
  ```
- 状态变更写入 `llm_providers.status` 字段

### Fallback 路由策略

```python
# 伪代码
async def stream_chat_with_fallback(messages, provider_id=None, db=None):
    primary = await _resolve_provider(db, provider_id)
    fallback_chain = [primary] + await _get_fallback_chain(db, primary.id)

    for attempt, p in enumerate(fallback_chain[:3]):  # 最多尝试 3 个
        try:
            async for chunk in _call_provider(p, messages):
                yield chunk
            return  # 成功
        except (httpx.ConnectError, RuntimeError) as exc:
            if attempt < 2:  # 还有备用
                yield sse_warning(f"主模型失败，自动切换至 {fallback_chain[attempt+1].name}")
                continue
            yield sse_error("所有模型均不可用，请稍后重试")
            return
```

### Fallback 决策表

| 主 Provider 状态 | 用户选择 | 实际调用 |
|---|---|---|
| healthy | 用户选 A | A |
| down | 用户选 A | fallback_chain[1] + warning 通知 |
| degraded | 用户选 A | A（仍尝试，超时后 fallback） |
| 未指定 | 默认 | `is_default=true` 的 Provider |

### 监控埋点

- 每次 fallback 触发写入日志：
  ```
  [fallback] user_id=42 from=mimo-pro to=deepseek-v4 reason=timeout duration=12.3s
  ```
- 管理员后台展示：
  - 每个 Provider 24 小时成功率
  - Fallback 触发频次 TOP 5
  - Provider 平均响应时间趋势

---

## 安全设计

### API Key 流向

```
.env / 数据库  ──▶  后端 Service 层  ──▶  httpx 请求
                          ↑
                          └── 前端永远不接触
```

- 公开接口响应过滤：`{ id, name, model_name, status }`，无 `api_key`、无 `base_url`
- 管理员接口响应：`api_key` 脱敏为 `sk-***xyz4`
- 创建/编辑接口的请求体 `api_key` 字段写入数据库后立即从内存清除，不写日志

### 防探测

- 公开接口只返回 `status != 'down'` 的 Provider，避免泄露已下线供应商列表
- `provider_id` 不存在时：后端静默回退默认 Provider，不返回 404
- 游客模式忽略 `provider_id` 参数

---

## 不变约束

- 所有业务调用方（ResumeDiagnosis / PremiumInterview / CareerPlanning / ChatDock）
  在 Phase 1-3 落地过程中**不需要任何改动**。
- `stream_chat()` 必须始终保持向后兼容：不传 `provider_id` 时行为与现在完全一致。
- `Service/Utils/llm_client.py` 现有的三层防波堤（JSON 解析 / choices 越界 / 顶层异常）
  在 Phase 1 扩展时必须保留。
