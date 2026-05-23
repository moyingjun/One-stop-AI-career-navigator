# Feature Mission Console Shell — 端到端手工验收清单

> Spec: `frontend-mission-console-shell`
> 用途：发版前的人工核对单。本清单不包含任何用户文档 / 营销 / 部署内容。
> 执行环境：本地 `uvicorn main:app --reload --port 8000` + `npm run dev`（前端）。
> 适用页面：`Resume_Page`（`frontend/src/ResumeDiagnosis.vue`）/ `Career_Page`（`frontend/src/CareerPlanning.vue`）/ `Interview_Page`（`frontend/src/PremiumInterview.vue`）。
> 视觉基准：`frontend/src/Dashboard.vue`（read-only，禁止修改）。

---

## 0. 前置准备

- [ ] 后端 `uvicorn` 进程已启动并监听 `127.0.0.1:8000`
- [ ] 前端 `npm run dev` 已启动并监听 `127.0.0.1:5173`
- [ ] 已使用真实账号完成登录（JWT 写入 localStorage）
- [ ] 浏览器开发者工具已打开「Network」面板，过滤为「EventStream / Fetch」
- [ ] 浏览器开发者工具已打开「Console」面板，确认无未捕获报错
- [ ] 当前分支 `git status` 干净（用于后续 §3 git diff 检查）

---

## 1. 三页 Happy Path 业务闭环验收

### 1.1 Resume_Page — 上传 → 触发诊断 → 接收 SSE → 渲染报告 + 雷达图

- [ ] 通过左侧导航或路由进入 `Resume_Page`
- [ ] 页面渲染出 Hero / Control Grid / Result Zone 三段式骨架（`FeaturePageShell` 容器存在）
- [ ] Hero 区可见标题「简历诊断」与三阶段徽章「扫描 / 诊断 / 报告」
- [ ] Control Grid 区可见：文件上传 dropzone、目标岗位输入、JD 文本框、`ActionDock` 中的「触发诊断」主操作按钮
- [ ] 上传一份 PDF / DOCX 简历，确认上传组件返回成功（无 console error）
- [ ] 输入目标岗位与 JD 文本，点击「触发诊断」
- [ ] Network 面板出现一条 `POST /api/resume/diagnose` 请求，类型为 `eventsource`/`text/event-stream`
- [ ] 请求体 JSON 字段集合与重构前一致（不增、不减）
- [ ] EventStream 中按顺序观测到事件类型：`meta`（≤1）→ `reply`（多条）→ 可选 `warning` → `done`（携带 `record_id`）
- [ ] Result Zone 中的报告文本随 `reply` 事件**增量追加**（非整段替换），文本拼接顺序与事件顺序一致
- [ ] 诊断完成后，`CyberRadarChart` 六维评分容器渲染出雷达图，所有维度数值非空
- [ ] 报告区可见 `data-test="report-title"` 与 `data-test="report-item"` 等关键业务节点
- [ ] 主动制造错误场景（如断网后重试）：SSE `error` 事件文案在 Result Zone 错误区域**原文展示**，不带任何项目自创前缀（如「请求失败」「系统错误」「服务异常」「出错了」「错误：」）
- [ ] 侧边栏可见 `SidebarEducationPlaceholder`：图标 `GraduationCap`，文案「工程师正在玩命开发中，敬请期待！🚀」，悬停 tooltip 与文案一致，点击无任何路由跳转
- [ ] `SidebarEducationPlaceholder` 根元素 `aria-disabled="true"`、`tabindex="-1"`

### 1.2 Career_Page — 输入背景 → 触发规划 → 阶段路线 + 能力缺口

- [ ] 通过路由进入 `Career_Page`
- [ ] 页面渲染出三段式骨架，Hero 区标题「职业规划」与徽章「路线图 / 阶段目标 / 能力缺口」
- [ ] Control Grid 区可见：简历文本（来自 `userStore`）、用户困惑输入、推荐问题 chips
- [ ] `ActionDock` 中可见主操作「生成蓝图」与次操作「复制」「导出」
- [ ] 推荐问题 chips 拉取走 `GET /api/career/suggestions`（如适用）；字段集合与重构前一致
- [ ] 填写背景信息后点击「生成蓝图」
- [ ] Network 面板出现一条 `POST /api/career/plan` 请求，类型为 SSE
- [ ] 请求体字段集合与重构前一致（不增、不减）
- [ ] EventStream 事件序列：`meta`（≤1）→ `reply`（多条）→ 可选 `warning` → `done`（携带 `record_id`）
- [ ] Result Zone 流式 Markdown 蓝图按 `reply` 事件累加渲染
- [ ] 规划结果中可见**阶段路线**条目（`data-test="stage-item"` 或等价节点），每个阶段含目标与时间窗
- [ ] 规划结果中可见**能力缺口**条目（`data-test="gap-item"` 或等价节点），缺口描述非空
- [ ] 「复制」次操作能将蓝图文本写入剪贴板；「导出」次操作触发下载或预览
- [ ] 主动制造 SSE `error` 场景：错误文案原文展示，不被二次包装
- [ ] 侧边栏 `SidebarEducationPlaceholder` 渲染、文案、disabled 状态与 §1.1 一致

### 1.3 Interview_Page — 进入训练舱 → 一轮问答 → 实时评分 → 复盘

- [ ] 通过路由进入 `Interview_Page`
- [ ] 页面渲染出三段式骨架，Hero 区标题「模拟面试」与徽章「训练舱 / 实时评分 / 复盘」
- [ ] Control Grid 区可见：难度选择（温和 / 标准 / P8）、消息输入框
- [ ] `ActionDock` 中可见主操作「发送」与次操作「结束面试」
- [ ] 选择一种难度，输入一句答复，点击「发送」
- [ ] Network 面板出现 `POST /api/interview/chat` 请求（来自 `streamInterviewChat`），类型为 SSE
- [ ] 请求体字段集合（含 `messages`、`difficulty` 等）与重构前一致
- [ ] EventStream 事件序列：`meta`（≤1）→ `reply`（多条）→ 可选 `warning` → `done`
- [ ] Result Zone 对话气泡流按 `reply` 增量追加，AI 气泡与用户气泡分色显示
- [ ] 答题过程中**压力分 `MetricCard`** 实时更新（`data-test="stress-score"` 或等价节点）
- [ ] 完成一轮问答后，点击「结束面试」
- [ ] Network 面板出现 `POST /api/interview/evaluate` 请求；请求体字段与重构前一致
- [ ] 复盘 Modal 弹出（基于既有 `BaseModal.vue` 扩展，不改 BaseModal 本身）
- [ ] 复盘 Modal 中渲染六维评分 `CyberRadarChart`，雷达图维度齐全
- [ ] 复盘按钮 `data-test="review-button"` 等关键业务节点存在
- [ ] 主动制造 SSE `error` 场景：错误文案原文展示，不被二次包装
- [ ] 侧边栏 `SidebarEducationPlaceholder` 渲染、文案、disabled 状态与 §1.1 一致

---

## 2. 视觉抽样对比 — 三页 vs `Dashboard.vue` 同源性

> 截图取样：每页至少 1 张全页截图，三页共 3 张；与 `Dashboard.vue` 截图同框对比。

- [ ] **字体层级**：标题（`text-white font-bold`、字号档位）、副标题（`text-cyan-200/200`、字号档位）、正文（`text-gray-300/400`、字号档位）三档与 `Dashboard.vue` 一致
- [ ] **圆角**：所有卡片容器圆角为 `16px`（来自 `CyberGlassCard.vue` 复用），与 `Dashboard.vue` 卡片一致
- [ ] **阴影**：卡片 hover / focus 阴影 `shadow-[0_0_30px_rgba(...)]` 强度与 `Dashboard.vue` 同款，无新增阴影预设
- [ ] **边框透明度**：毛玻璃卡片 `backdrop-blur(16px)` + `conic-gradient` 边框流光，透明度档位与 `Dashboard.vue` 一致
- [ ] **页面背景**：底色 `bg-[#020205]` + 三层 ambient blur（紫 / 青 / 靛蓝），与 `Dashboard.vue` 同源
- [ ] **强调色谱**：紫 `#a855f7`（简历）/ 蓝 `#3b82f6`（职业规划）/ 粉 `#ec4899` / 青 `#06b6d4`（评分通道）取色与 `Dashboard.vue` 一致
- [ ] 三页之间互相切换时，骨架结构（Hero → Control → Result 顺序）保持稳定，无塌陷或重复渲染
- [ ] PR 描述中已附 1-2 张三页与 `Dashboard.vue` 同框对比截图

---

## 3. Git Diff 检查 — 受保护文件清单未被触碰

> 命令参考：`git diff --name-only origin/main...HEAD`
> 目标：以下文件 **不应** 出现在 diff 输出中。

后端层（绝对禁止改动）：

- [ ] `Router/**` 下任意文件未被修改
- [ ] `Service/**` 下任意文件未被修改（含 `Service/Games/Avalon/**`）

前端关键文件（绝对禁止改动）：

- [ ] `frontend/src/router/index.js` 未被修改（已注册路由路径与组件映射保持原状）
- [ ] `frontend/src/services/llm_service.js` 未被修改
- [ ] `frontend/src/Dashboard.vue` 未被修改
- [ ] `frontend/src/components/CyberGlassCard.vue` 未被修改
- [ ] `frontend/src/components/BaseModal.vue` 未被修改
- [ ] `frontend/src/components/CyberRadarChart.vue` 未被修改
- [ ] `frontend/src/AvalonGame.vue` 未被修改
- [ ] `frontend/src/stores/gameStore.js` 未被修改

依赖与构建：

- [ ] `frontend/package.json` 未引入新的第三方 UI 组件库依赖
- [ ] `frontend/package-lock.json` 仅在已声明依赖范围内变化

业务页物理路径：

- [ ] `frontend/src/ResumeDiagnosis.vue` 物理路径未移动
- [ ] `frontend/src/CareerPlanning.vue` 物理路径未移动
- [ ] `frontend/src/PremiumInterview.vue` 物理路径未移动

后端契约：

- [ ] 三页所调用的 HTTP 接口请求路径、方法、响应数据结构均与重构前一致
- [ ] SSE 事件类型清单 `meta` / `reply` / `warning` / `error` / `done` 未变更，`done` 事件携带的 `record_id` 字段处理逻辑未变更

---

## 4. Grep 检查 — Toast / StreamingLoader 直接 import 收口

> 命令参考（PowerShell）：
> `Select-String -Path frontend/src/ResumeDiagnosis.vue,frontend/src/CareerPlanning.vue,frontend/src/PremiumInterview.vue -Pattern "Toast\.vue|StreamingLoader\.vue"`

- [ ] `frontend/src/ResumeDiagnosis.vue` 内对 `components/Toast.vue` 的直接 import 出现次数 ≤ 1，且若存在则仅出现在 `@/utils/uiFallbacks` 调用链中
- [ ] `frontend/src/ResumeDiagnosis.vue` 内对 `components/StreamingLoader.vue` 的直接 import 出现次数 ≤ 1，且若存在则仅出现在 `@/utils/uiFallbacks` 调用链中
- [ ] `frontend/src/CareerPlanning.vue` 内对 `components/Toast.vue` 的直接 import 出现次数 ≤ 1（仅来自 `@/utils/uiFallbacks`）
- [ ] `frontend/src/CareerPlanning.vue` 内对 `components/StreamingLoader.vue` 的直接 import 出现次数 ≤ 1（仅来自 `@/utils/uiFallbacks`）
- [ ] `frontend/src/PremiumInterview.vue` 内对 `components/Toast.vue` 的直接 import 出现次数 ≤ 1（仅来自 `@/utils/uiFallbacks`）
- [ ] `frontend/src/PremiumInterview.vue` 内对 `components/StreamingLoader.vue` 的直接 import 出现次数 ≤ 1（仅来自 `@/utils/uiFallbacks`）
- [ ] 三页中均能搜索到一行 `import { ... } from '@/utils/uiFallbacks'`（统一从降级模块解析 Toast / Loader）
- [ ] 三页中均**未出现**自行实现的 alert / 内联 toast / 自造 loader 组件代码（视觉与提示统一通过 `@/utils/uiFallbacks` 收口）

---

## 5. 构建命令红线 — 严禁执行

> 这一节是构建安全红线，对应 Requirement 7.12 + steering `tech.md`。
> 验收阶段任何操作都不得触发以下命令；如发现已被执行，必须向负责人报备并撤回。

- [ ] 未执行 `npm run build`
- [ ] 未执行 `vite build`
- [ ] 未执行 `tsc`
- [ ] 未执行 `vue-tsc`
- [ ] 类型 / 编译问题（如有）通过直接修改源代码解决，未通过类型检查命令验证
- [ ] 自动化校验仅依赖 `npm run test`（即 `vitest --run`），未触达上述构建命令

---

## 6. 验收结论

- [ ] §1 三页 happy path 全部勾选
- [ ] §2 视觉抽样对比全部勾选，附对比截图
- [ ] §3 git diff 检查全部勾选
- [ ] §4 grep 检查全部勾选
- [ ] §5 构建命令红线全部勾选
- [ ] 13 条 Correctness Properties 对应的属性测试 + EXAMPLE 级 spec 全部 `npm run test` 通过
- [ ] 浏览器 Console 全程无未捕获异常

签字栏：

- 验收人：________________________
- 验收日期：______________________
- PR 链接：_______________________
