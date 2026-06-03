# Task Log

本文件记录 Agent 任务流水，方便跨工具交接。

## 2026-05-29

任务名称：PremiumInterview Feedback Coach v1 收工记录。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：AI_MEMORY 更新

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 模拟面试结束评估已增强。
- 新增六维评分解释（`*_explanation` 字段）。
- 新增 3 条下一轮改进动作（`improvement_suggestions` 数组）。
- 保留 `radarScores` 数字结构不变。
- 旧历史记录缺失 explanation/suggestions 时降级隐藏，不报错。
- 未做扣分原因数组、参考回答、总分。
- 未改 `record_type`、History 主路径、Provider、TTS、VoiceInput。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：Hermes Project Steward v0.1 阶段开发收工记录。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：AI_MEMORY 更新 + 阶段收工

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- Agent Harness v1.2 已落地。
- Hermes Project Steward v0.1 已定版。
- OpenCode 定位为 Harness Caretaker / Memory Steward。
- TTS 手动朗读 Beta 完成。
- TTSButton Polish v1 完成。
- Dashboard 下一步行动 + Layout Polish 完成。
- PremiumInterview Voice Input MVP 审计完成。
- 当前禁止继续扩展：不做全局自动朗读、不做自动发送、不做 RAG 主流程、不做大规模业务重构。
- 下一步候选：模拟面试评分解释增强、职业规划导出增强、Dashboard 第二轮体验优化。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：只读核对 TTS 手动朗读边界并完成 Hermes Steward v0.1 阶段收口。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读核对 + AI_MEMORY 更新 + 阶段收口

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- TTS 完全保持手动触发，不存在默认自动播放、流式 chunk 自动朗读或每条 AI 回复自动请求 TTS。
- Hermes Steward v0.1 阶段可收口：Agent Harness v1.2 稳定，Hermes Project Steward v0.1 定版。
- 已确认事实：PostgreSQL 主路径、RAG 云端 embedding、ChatDock/History/userStore/Provider 边界、TTS 手动朗读。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：只读核对 ChatDock / History / userStore 边界并更新 CURRENT_STATE。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读核对 + AI_MEMORY 更新

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- ChatDock / History / userStore / Provider 边界符合 D009 / D010。
- 未发现 History 反向污染 userStore。
- 未发现 Provider / History / User Profile 混用。
- 未发现 ChatDock 越权替代三大功能页。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：收紧 OpenCode 定位措辞。

任务类型：Markdown 规则修正 + AI_MEMORY 更新

修改文件：

- `OPENCODE_USAGE.md`
- `HERMES_STEWARD.md`
- `MODEL_ROLES.md`
- `WORKFLOW.md`
- `AGENTS.md`
- `AI_MEMORY/CHANGELOG_AI.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- OpenCode 已从 “Harness Runner” 术语收紧为本地项目管家控制台 / Harness Caretaker。
- OpenCode 当前偏 AI_MEMORY、规则维护、只读核对、交接摘要和低风险 Markdown 维护。
- OpenCode 不是 Hermes 本体，也不是默认业务开发主力。
- 业务开发执行器应从 Trae / Kiro / Cursor / Codex / WorkBuddy / Antigravity 等可替换 coding tools 中按当期模型能力和性价比选择。

未执行：

- 未修改业务代码。
- 未修改 frontend / Router / Service / Settings。
- 未修改 `.env`、`requirements.txt`、`package.json`。
- 未运行 npm / pip / build / test。
- 未执行 `git add`。
- 未执行 `git commit`。
- 未删除文件。

## 2026-05-29

任务名称：Hermes Project Steward 概念纠偏文档修正。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档修正 + AI_MEMORY 更新

修改文件：

- `HERMES_STEWARD.md`（新增）
- `AGENTS.md`
- `PROJECT_MAP.md`
- `WORKFLOW.md`
- `MODEL_ROLES.md`
- `OPENCODE_USAGE.md`
- `AI_MEMORY/CHANGELOG_AI.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 正式引入 Hermes Project Steward 概念，明确其与 Agent Harness 和 OpenCode 的关系。
- Agent Harness v1.2：规则、记忆、模板、检查清单和执行边界已建立。
- Hermes Project Steward v0.1：开始孵化，由用户人工触发。
- OpenCode 不等于 Hermes Steward 本体，只是当前可选执行器之一。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。
- 未执行 git 检查。

## 2026-05-29

任务名称：D007 决策修正与 AI_MEMORY 同步。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档修正 + AI_MEMORY 更新

修改文件：

- `DECISIONS.md`
- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`
- `CHECKLISTS.md`

结论：

- D007 已修正为更精确的表述：主入口冻结，后端 /api/kb/* 作为 JWT 保护的实验性接口保留。
- CURRENT_STATE.md 已同步更新，移除 D007 偏差待确认项。
- CHECKLISTS.md 已补充 RAG 检查项说明。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：只读核对 RAG / 文件上传入口暴露面。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读核对 + AI_MEMORY 更新

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 旧 `/api/knowledge/upload` 已返回 410 Gone。
- 新 `/api/kb/upload` 需 JWT 但后端仍可用。
- 前端 `ChatComposer.vue` 附件按钮已禁用。
- Dashboard 中 `showKnowledgePanel` 不再被任何按钮触发。
- `KnowledgePanel.vue` 和 `kbService.js` 仍存在但未被用户可点击入口激活。
- D007 决策存在偏差：后端接口仍暴露，前端组件仍存在。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：旧 CTO 窗口交接确认与 RAG embedding 路径核对。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读核对 + AI_MEMORY 更新

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- Harness 第一阶段方向被旧 CTO 窗口认可。
- OpenCode 继续作为低风险本地项目管家控制台 / AI_MEMORY 管家。
- RAG embedding 主路径已确认使用云端 API（`Service/Utils/embedding_client.py` 调用 `https://tokenrai.com/v1`）。
- `embedding_client.py` 和 `rag_service.py` 均明确禁止 torch/sentence-transformers。
- `requirements.txt` 中无重型 ML 依赖。
- 发现残留：`Settings/config.py` 中 `RAG_EMBEDDING_MODEL` 配置为本地模型名称但未被使用。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：只读核对数据库运行路径并更新 CURRENT_STATE。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读核对 + AI_MEMORY 更新

修改文件：

- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 主运行路径已确认使用 PostgreSQL；SQLite 主要残留在 `legacy_sqlite_history_db.py`、`history.db` 和测试文件中。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：OpenCode 使用 Mimo-2.5 Pro 完成低风险写入边界测试。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：低风险写入测试

修改文件：

- `AI_MEMORY/TASK_LOG.md`

结论：

- 仅追加任务日志，未修改业务代码。

未执行：

- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：OpenCode 使用 Mimo-2.5 Pro 完成只读自检。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：只读自检

读取文件：

- `AGENTS.md`
- `OPENCODE_USAGE.md`
- `DECISIONS.md`
- `PROJECT_MAP.md`
- `MODEL_ROLES.md`
- `WORKFLOW.md`
- `CHECKLISTS.md`
- `TASK_TEMPLATES.md`
- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/CONTEXT_BRIEF.md`

结论：

- 自检通过。
- 能正确识别 OpenCode 定位、允许任务、禁止事项、高风险模块、文档冲突和待确认事项。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：补充工具可替换原则与日常任务模板。

执行范围：

- 更新 `AGENTS.md`，新增“工具可替换原则”。
- 新增 `TASK_TEMPLATES.md`。
- 更新 `AI_MEMORY/CHANGELOG_AI.md`。
- 更新 `AI_MEMORY/TASK_LOG.md`。

未执行：

- 未修改业务代码。
- 未修改 Router / Service / frontend。
- 未修改 `.env`、`requirements.txt`、`package.json`。
- 未运行 `npm install`。
- 未运行 `npm run build`。
- 未运行 `pip install`。
- 未执行 `git add`。
- 未执行 `git commit`。
- 未删除文件。

## 2026-05-29

任务名称：调整工具分工文档为角色优先、工具可替换策略。

执行范围：

- 修改 `MODEL_ROLES.md`。
- 小幅同步 `WORKFLOW.md`。
- 小幅同步 `OPENCODE_USAGE.md`。
- 更新 `AI_MEMORY/CHANGELOG_AI.md`。
- 更新 `AI_MEMORY/TASK_LOG.md`。

主要结果：

- 不再把 Kiro / OpenCode / Codex / Trae / Antigravity / Cursor / WorkBuddy 等工具写成长期固定岗位。
- 保留稳定任务角色，并补充默认权限、禁止事项和交付物。
- 将工具匹配改为按成本、模型能力、上下文、本地读写能力和任务风险临时选择。
- 保留 OpenCode 当前第一阶段定位，但明确它不是唯一管家工具。

未执行：

- 未修改业务代码。
- 未修改 Router / Service / frontend。
- 未修改 `.env`、`requirements.txt`、`package.json`。
- 未运行 `npm install`。
- 未运行 `npm run build`。
- 未运行 `pip install`。
- 未执行 `git add`。
- 未执行 `git commit`。
- 未删除文件。

## 2026-05-29

任务名称：创建个人开发者版 Agent Harness 规则体系。

执行范围：

- 读取 `.kiro/steering/product.md`。
- 读取 `.kiro/steering/structure.md`。
- 读取 `.kiro/steering/tech.md`。
- 读取 `.kiro/steering/delivery-report.md`。
- 只读核对项目文件清单。
- 创建根目录 Harness Markdown 文件。
- 创建 `AI_MEMORY` 目录下记忆 Markdown 文件。

未执行：

- 未修改业务代码。
- 未运行 `npm install`。
- 未运行 `npm run build`。
- 未运行 `pip install`。
- 未执行 `git add`。
- 未执行 `git commit`。
- 未删除文件。

结论：

- 规则体系已建立。
- 旧 steering 中与当前明确决策冲突的部分已在新文档中裁决。
- 代码实际完成度未验证，相关问题已写入 `AI_MEMORY/CURRENT_STATE.md` 待确认。

## 任务记录模板

```text
日期：
任务名称：
执行工具：
任务类型：
读取文件：
修改文件：
未处理范围：
已执行验证：
未执行验证：
风险：
待确认：
下一步：
```
