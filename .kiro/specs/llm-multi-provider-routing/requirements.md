# 多模型动态路由 — 需求文档

> ⚠️ 本文档记录**未来规划**，当前系统尚未实现任何多 Provider 功能。
> AI Agent 阅读本文档时，请勿将下列条目视为已实现能力，也不要据此修改现有业务代码。

---

## 一、当前已实现状态（截至 2026-05）

### 真实运行架构

LLM 调用为**单供应商配置**，由 `.env` 三个环境变量驱动：

```
LLM_API_KEY=...
LLM_BASE_URL=https://api.xiaomimimo.com/v1/chat/completions
LLM_MODEL_NAME=mimo-v2.5-pro
```

实现位置：
- 配置入口：`Settings/config.py`、`Service/Settings/config.py`
- 调用入口：`Service/Utils/llm_client.py` 的 `stream_chat()` 和 `complete_chat()`
- 切换方式：修改 `.env` 后重启服务

### 已实现的稳定能力

- 三个 `LLM_*` 环境变量统一通用化，可切换 MIMO / DeepSeek / Claude（OpenAI 兼容格式）
- `stream_chat()` 三层防波堤（JSON 解析失败、`choices` 越界、顶层异常），不会因单条非法 chunk 中断 SSE
- 兼容 `tool_calls`、空 `delta` 等非文本 chunk，安全跳过
- `[系统异常]` 文本作为兜底降级返回给前端

---

## 二、当前未实现（明确边界）

以下能力**全部尚未实现**，本文档仅记录规划：

| 项目 | 状态 |
|---|---|
| `llm_providers` 数据库表 | ❌ 不存在 |
| `LlmProvider` ORM 模型 | ❌ 不存在 |
| `provider_id` 请求参数 | ❌ `stream_chat` 不接受此参数 |
| Admin Provider 管理 API | ❌ `/api/admin/llm-providers/*` 路由不存在 |
| 公开 Provider 列表 API | ❌ `/api/llm-providers/active` 路由不存在 |
| Dashboard 模型下拉选择器 | ❌ 当前 Dashboard 顶部只显示静态"DeepSeek V4 Online"徽章 |
| `llmProviderStore` Pinia Store | ❌ 不存在 |
| Provider 健康检查 / 自动 fallback | ❌ 不存在 |
| Provider 失败自动切换 | ❌ 不存在 |

---

## 三、未来 Phase 1 — 后端 Provider 注册表与管理 API

### R1.1 数据层：llm_providers 表

新增 PostgreSQL 表，字段：
- `id` INTEGER PK
- `name` VARCHAR(128) UNIQUE NOT NULL（如 `"MIMO Pro"` / `"DeepSeek V4"`）
- `base_url` VARCHAR(512) NOT NULL
- `api_key` VARCHAR(512) NOT NULL（**加密存储或仅服务端可读**）
- `model_name` VARCHAR(128) NOT NULL
- `is_default` BOOLEAN DEFAULT FALSE
- `is_active` BOOLEAN DEFAULT TRUE
- `status` VARCHAR(32)（`healthy` / `degraded` / `down`，由健康检查更新，初版可全设 `healthy`）
- `created_at` / `updated_at` TIMESTAMP

### R1.2 服务层：动态路由扩展

`stream_chat()` / `complete_chat()` 新增可选参数 `provider_id`：
- 不传 → 使用 `is_default=true` 的 Provider（兼容现有调用方，零改动）
- 传入 → 从数据库查询对应 Provider 配置发起请求
- 数据库未初始化时回退到 `LLM_*` 环境变量

### R1.3 API 层：Provider 管理接口（仅管理员）

- `GET /api/admin/llm-providers` — 列表（响应中 `api_key` 字段必须脱敏，仅显示尾 4 位）
- `POST /api/admin/llm-providers` — 新增
- `PATCH /api/admin/llm-providers/{id}` — 编辑
- `DELETE /api/admin/llm-providers/{id}` — 删除
- `PATCH /api/admin/llm-providers/{id}/set-default` — 设为默认

### R1.4 公开列表接口（普通用户可见）

- `GET /api/llm-providers/active` — 返回 `is_active=true` 的 Provider 列表
- 响应字段**仅包含**：`id`、`name`、`model_name`、`status`
- **绝对不能包含**：`api_key`、`base_url`（避免暴露内部端点）

---

## 四、未来 Phase 2 — Dashboard 模型选择器

### R2.1 前端 Pinia Store

新建 `frontend/src/stores/llmProviderStore.js`：
- `state`：`providerList: []`、`currentProviderId: number|null`
- `action`：`fetchProviders()`、`setCurrentProvider(id)`
- `getter`：`currentProvider` — 当前选中的 Provider 信息

### R2.2 Dashboard UI

- 位置：Dashboard 顶部状态徽章旁，或设置面板
- 形态：暗黑赛博风格下拉选择器
- 数据：`llmProviderStore.providerList`
- 显示字段：`name`（主）+ `model_name`（次）+ status 圆点（绿/黄/红）
- **绝不显示** `api_key` 或 `base_url`

### R2.3 LLM 请求自动附加 provider_id

- 所有 `/api/agent/chat`、`/api/interview/chat` 等 SSE 请求 body 自动带 `provider_id`
- 游客模式（未登录）禁用下拉，强制使用服务端默认 Provider

---

## 五、未来 Phase 3 — Fallback、健康检查、自动切换

### R3.1 健康检查

- 后台定时任务（建议 60 秒一次）对每个 `is_active=true` 的 Provider 发送轻量探测请求
- 探测内容：`POST {base_url}` 带最小 messages（如 `"ping"`）
- 失败累计 3 次 → `status` 改为 `down`，恢复后改回 `healthy`

### R3.2 自动 Fallback

- 主 Provider 调用失败（HTTP 5xx / 超时）时，按预设优先级链路自动切换备用 Provider
- 切换路径：`current_provider → next_active_provider → default_provider`
- 切换次数上限：每次请求最多重试 2 次，避免雪崩
- Fallback 触发后通过 SSE `event: warning` 通知前端：`"已自动切换至备用模型 X"`

### R3.3 用户手动选择 vs 自动切换的优先级

- 用户在 Dashboard 显式选择的 Provider 优先级最高
- 该 Provider 失败时仍触发 fallback，但不修改用户选中状态（用户下一次请求仍尝试原选择）
- 连续 N 次失败后才将 `status` 改为 `down`

### R3.4 监控与日志

- 每次 fallback 触发记入日志：`time / user_id / from_provider / to_provider / reason`
- 管理员后台可查看 fallback 频率统计

---

## 六、安全约束（强制）

### S1 — API Key 不允许回传前端

- 任何公开接口（包括 `GET /api/llm-providers/active`）响应中**必须不包含** `api_key` 字段
- 管理员接口的 `api_key` 字段必须脱敏（仅显示尾 4 位）
- 前端 Pinia Store **永远不存储 api_key**
- 前端只能通过 `provider_id` 引用 Provider，由后端查询真实密钥

### S2 — 游客模式锁定

- `user_id=None` 的游客请求**忽略** `provider_id` 参数，强制使用服务端默认 Provider
- 防止游客遍历 `provider_id` 探测系统配置

### S3 — provider_id 合法性校验

- 后端收到 `provider_id` 时必须校验：
  - Provider 存在
  - `is_active=true`
  - `status` 不是 `down`
- 校验失败时回退默认 Provider，不向前端暴露 Provider 不存在的信息（防探测）
