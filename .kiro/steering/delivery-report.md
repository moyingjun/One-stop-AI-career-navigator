# AI 协作交付报告规范

## 适用范围

本规范适用于本项目中所有由 AI Agent 执行的开发、重构、修复、审计、迁移任务。

目标是让每一轮任务完成后，都能形成可交接、可审计、可回滚、可继续开发的标准化报告，方便用户在 Kiro / Codex / Gemini / ChatGPT / Claude 之间传递上下文。

任何任务完成后，不允许只说“完成了”。必须输出完整交付报告。

---

## 总原则

1. **区分“已实现”和“已验证”**
   - 已写代码 ≠ 已完成。
   - getDiagnostics 通过 ≠ 功能已通过。
   - 页面看起来正常 ≠ 数据流闭环。
   - 后端启动成功 ≠ API 语义正确。
   - 必须明确哪些已实现、哪些已验证、哪些需要人工验收。

2. **禁止假闭环**
   - 如果没有实际验证，不得写“功能已闭环”。
   - 应写“代码已接入，待人工验收”。
   - 对用户可见功能必须给出可观察验收路径。

3. **必须报告 untracked 文件**
   - `git diff` 不显示 untracked 文件。
   - 如果新增文件没有 `git add`，必须在报告中单独标出。
   - 尤其是新组件、新 store、新 service、新模型、新 migration 文件。

4. **必须报告数据库变化**
   - 新增表、字段、索引、migration、权限、连接配置，都必须单独说明。
   - 如果需要用户手动执行 SQL，必须列出 SQL。
   - 不得打印 `.env` 密码、API Key、JWT Secret 等敏感信息。

5. **必须报告 API / 数据流变化**
   - 新增或修改 endpoint。
   - 请求体字段变化。
   - 响应结构变化。
   - SSE / WebSocket 事件变化。
   - Store / localStorage / PostgreSQL 的数据流变化。

6. **尊重项目架构**
   - Router 只处理 HTTP 协议层。
   - Service 负责业务编排。
   - Agents 负责 Prompt 和 LLM 调用。
   - Utils / db 负责通用工具和数据库访问。
   - 前端页面 SFC 放在 `src/`，复用组件放在 `src/components/`。
   - 所有用户可见文案使用简体中文。
   - 业务注释和 docstring 使用中文。
   - 不引入与暗黑赛博毛玻璃风格冲突的 UI 库。
   - 弹窗优先复用 BaseModal，轻提示优先复用 Toast，加载态优先复用 StreamingLoader。

7. **执行命令红线**
   - 不要运行 `npm run build`、`vite build`、`tsc`、`vue-tsc`，除非用户明确要求。
   - 可以运行 `git status`、`git diff`、`grep/rg`、getDiagnostics、后端局部 smoke test。
   - 不要删除 `.git`。
   - 不要执行大范围不可逆删除。
   - 不要打印 secrets。

---

# 标准交付报告模板

每次任务完成后，必须按以下结构输出。

## 1. 任务概述

- 本轮任务名称：
- 用户目标：
- 本轮实际处理范围：
- 本轮未处理范围：
- 当前结论：
  - 已实现 / 待验证 / 需修复 / 高风险

示例：

```text
本轮目标是修复 Dashboard 雷达图、ChatDock 归档和历史恢复。
实际完成：雷达图数据源修复、ChatDock 归档按钮接入、history session upsert 后端接口。
未完成：服务器部署验证、生产数据库迁移验证。
当前结论：代码已实现，待人工 npm run dev + 后端 smoke test 验收。



2. 根因分析

如果是修 Bug 或功能不闭环，必须说明根因。

格式：

问题	表现	根因	修复方式
问题 A	用户看到什么	代码 / 数据 / 配置根因	本轮如何修

要求：

不要只说“已修复”。
要说明为什么原来不工作。
如果根因不确定，必须写“不确定，需要进一步验证”。
3. 修改文件清单

必须分组列出。

3.1 已修改 tracked 文件
文件	修改类型	说明
frontend/src/Dashboard.vue	modified	接入 ChatDock / 修复 radar
Router/history_router.py	modified	新增 session API
3.2 新增 untracked 文件
文件	用途	是否必须 git add
frontend/src/components/chat/ChatDock.vue	ChatDock 组件	是
frontend/src/services/historyClient.js	历史 API 客户端	是
3.3 删除文件
文件	删除原因	是否确认安全
3.4 未触碰但相关文件

列出关键受影响但未修改的文件，避免误会。

4. 数据库变化

如果本轮涉及数据库，必须填写。

4.1 数据库类型
当前运行数据库：
是否仍依赖 SQLite：
是否涉及 PostgreSQL：
是否影响云端数据库：
4.2 表结构变化
表	字段 / 索引	变化	是否幂等
history_records	session_id	新增	是
history_records	record_type	新增	是
4.3 Migration / create_all 说明

说明：

是否使用 Base.metadata.create_all
是否手写 ALTER TABLE
是否使用 Alembic
是否存在重复索引风险
是否需要用户手动执行 SQL
4.4 用户需要手动执行的 SQL

如果没有，写“无”。

-- 示例
DROP INDEX IF EXISTS ix_history_records_record_type;
4.5 数据安全说明
是否清空数据库：
是否删除数据：
是否需要备份：
是否影响旧数据：
是否兼容旧 records：
5. API 变化

如果新增或修改 API，必须填写。

方法	路径	用途	是否新增	是否兼容旧前端
PUT	/api/history/session/{session_id}	会话归档 upsert	新增	是
GET	/api/history/session/{session_id}	按 session 恢复	新增	是

同时说明：

是否需要鉴权：
是否按 user_id 隔离：
请求体字段：
响应字段：
是否影响旧接口：
6. 前端状态和数据流

如果改了前端 store、localStorage、组件状态，必须说明。

6.1 Store 变化
Store	字段 / Action	用途
chatSessionStore	currentSessionId	当前会话 ID
userStore	radarFromResume	简历诊断雷达快照
6.2 localStorage 变化
Key	用途	何时写入	何时读取
6.3 数据流说明

用箭头描述真实数据流。

示例：

用户在 ChatDock 输入
  → appendUserMessage()
  → SSE 获取 AI 回复
  → appendAIMessage()
  → localStorage 自动保存
  → 用户点击“归档本次对话”
  → PUT /api/history/session/{session_id}
  → PostgreSQL history_records upsert
  → HistoryArchive 可恢复
7. 用户可见功能验收

必须列出肉眼可验证路径。

7.1 功能 A 验收
1. 打开 Dashboard。
2. 输入一句话。
3. 点击发送。
4. AI 正常 streaming。
5. 点击归档。
6. HistoryArchive 出现一条 Agent 对话。
7.2 功能 B 验收
1. 完成简历诊断。
2. 回到 Dashboard。
3. 雷达图显示非 0 数据。
4. F5 刷新。
5. 雷达图仍保留。

要求：

必须写清楚用户要点哪里。
必须写清楚预期看到什么。
如果某功能尚未人工验证，写“待人工验收”。
8. 已执行验证

列出实际执行过的检查。

检查	结果
getDiagnostics Dashboard.vue	通过
git diff --name-only	已输出
uvicorn 启动	未执行 / 通过 / 失败
API smoke test	未执行 / 通过 / 失败

不得伪造验证结果。没有跑就写“未执行”。

9. 未执行验证

必须明确列出没做的。

示例：

未执行：
- npm run build
- vue-tsc
- 生产环境部署验证
- 云端数据库 migration 验证
- 多用户权限隔离测试
10. 风险与待修复问题

分级：

P0 必须立即修
问题	影响	建议
P1 应尽快修
问题	影响	建议
P2 可后置
问题	影响	建议
11. 回滚建议

说明如果出问题如何回滚。

示例：

如果 ChatDock 出问题：
- 回滚 Dashboard.vue 对 ChatDock 的接入
- 保留旧输入框逻辑
- 不影响 PostgreSQL migration

如果数据库 migration 出问题：
- 停止服务
- 恢复最近一次 pg_dump
- 回滚 history_db.py / ORM model

如果涉及数据库，必须说明是否需要备份。

12. git 状态

必须输出：

git status --short
git diff --name-only

并解释：

哪些是本轮改动。
哪些是历史遗留脏文件。
哪些 untracked 必须 git add。
哪些不应该提交。
13. 下一步建议

输出：

建议立即做什么。
建议暂停什么。
是否建议进入下一 Phase。
是否需要 Codex 只读审计。
是否需要人工验收。

示例：

建议：
1. 先人工 npm run dev 验收 ChatDock。
2. 再让 Codex 只读审计后端 history upsert。
3. 暂停阿瓦隆开发。
4. 暂停新 UI 功能。
完成定义

除非同时满足以下条件，否则不得说“完成”：

代码已写入。
无明显 diagnostics 错误。
关键数据流已解释。
验收路径已给出。
风险已标注。
untracked 文件已提醒。
如果需要用户手动 SQL / 配置 / 重启，已明确写出。
对未验证部分没有假装通过。

如果只满足前半部分，应写：

代码实现完成，待人工验收。

而不是：

功能完成。
任务结束固定输出格式

每次任务结束时，最后必须输出：

当前状态：
- 已实现：
- 已验证：
- 待人工验收：
- 必须修复：
- 可后置：
- 是否建议继续下一阶段：