# Task Log

本文件记录 Agent 任务流水，方便跨工具交接。

## 2026-05-29

任务名称：最小收口补丁，统一默认入口 5 件套与 INBOX 规则。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档收口 + 规则修正

修改文件：

- `AGENTS.md`
- `PROJECT_BRIEF.md`
- `MODEL_ROLES.md`
- `WORKFLOW.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 默认入口 5 件套已统一为：`PROJECT_BRIEF.md`、`AGENTS.md`、`DECISIONS.md`、`HERMES_TOOL_POLICY.md`、`AI_MEMORY/CURRENT_STATE.md`。
- `PROJECT_MAP.md`、`AI_MEMORY/CONTEXT_BRIEF.md`、`MODEL_ROLES.md`、`WORKFLOW.md`、`TASK_TEMPLATES.md`、`CHECKLISTS.md`、`HERMES_STEWARD.md`、`OPENCODE_USAGE.md`、`.kiro/steering/*` 已降级为二级参考 / 按需读取。
- 已补强 AGENTS 中的 INBOX 规则，明确 INBOX 是待消化记录，不是已确认事实。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装 Skill / MCP。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：新增 AI_MEMORY INBOX 标准报告模板。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档修正 + 模板补充

修改文件：

- `AI_MEMORY/INBOX/TEMPLATE.md`
- `AI_MEMORY/INBOX/README.md`
- `TASK_TEMPLATES.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 已新增 `AI_MEMORY/INBOX/TEMPLATE.md`，统一 Vibe Coding Tools 写入 INBOX 的报告格式。
- `AI_MEMORY/INBOX/README.md` 已补充“写入时优先参考 TEMPLATE.md”。
- `TASK_TEMPLATES.md` 已补充 INBOX 报告模板引用。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装 Skill / MCP。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：建立 Vibe Coding Tools → Hermes 的交付记录入口。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：规则扩展 + 文档修正

修改文件：

- `AI_MEMORY/INBOX/README.md`
- `AGENTS.md`
- `WORKFLOW.md`
- `TASK_TEMPLATES.md`
- `PROJECT_BRIEF.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- 已建立 `AI_MEMORY/INBOX/` 作为 Hermes Project Steward 的交付报告收件箱。
- 已明确重要任务完成后，vibe coding tools 可将结构化报告写入 INBOX，供 Hermes / OpenCode 后续消化。
- 已补充 AGENTS / WORKFLOW / TASK_TEMPLATES / PROJECT_BRIEF 中的统一入口说明。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装 Skill / MCP。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：Steering 精华迁移 v1。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：规则迁移 + 文档修正

修改文件：

- `.kiro/steering/README.md`
- `TASK_TEMPLATES.md`
- `CHECKLISTS.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- `.kiro/steering/` 已正式降级标注为 Legacy Kiro Steering / 历史 Skill Source。
- 已将仍有效的交付纪律最小吸收到 `TASK_TEMPLATES.md` 与 `CHECKLISTS.md`。
- 未吸收 SQLite、本地 embedding、阿瓦隆主线、RAG 上传主流程等过期内容。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：将 HERMES_TOOL_POLICY.md 纳入默认读取清单。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档修正 + AI_MEMORY 更新

修改文件：

- `AGENTS.md`
- `PROJECT_BRIEF.md`
- `HERMES_STEWARD.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- `HERMES_TOOL_POLICY.md` 已纳入 `AGENTS.md` 默认读取清单。
- `PROJECT_BRIEF.md` 已补充“开始任务前先读 `HERMES_TOOL_POLICY.md`”。
- `HERMES_STEWARD.md` 已补充 Hermes 安装 Skill / MCP 前必须先遵守 `HERMES_TOOL_POLICY.md`。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装 Skill / MCP。
- 未构建。
- 未提交。

## 2026-05-29

任务名称：新增 Hermes Tool Policy 并同步工具治理状态。

执行工具：OpenCode

使用模型：Mimo-2.5 Pro

任务类型：文档修正 + AI_MEMORY 更新

修改文件：

- `HERMES_TOOL_POLICY.md`
- `AI_MEMORY/CURRENT_STATE.md`
- `AI_MEMORY/TASK_LOG.md`

结论：

- Hermes Tool Policy 已建立。
- 已明确 Hermes / OpenCode / Codex / Claude Code / CCSwitch 的工具分层。
- Hermes 当前只允许低风险 Skills / MCP，暂不授予数据库写入、全盘写入、GitHub push/merge/release、Secrets、SSH 高权限等能力。
- Hermes 已成功接入 MiMo，不强行走 CCSwitch local router。

未执行：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

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

## 2026-06-06

任务名称：修复 Vibe Coding Tool Pool 同步后的文档冲突与模板污染。

执行工具：Hermes（MiMo）

任务类型：文档修正 + AI_MEMORY 更新

读取文件：

- `DECISIONS.md`
- `AGENTS.md`
- `HERMES_STEWARD.md`
- `OPENCODE_USAGE.md`
- `PROJECT_BRIEF.md`
- `MODEL_ROLES.md`
- `AI_MEMORY/TASK_LOG.md`

修改文件：

- `DECISIONS.md`：D012 从"OpenCode 是本地 Harness Runner"重写为"Vibe Coding Tool Pool 与可替换执行器"。
- `PROJECT_BRIEF.md`：INBOX 消化表述改为"由 Hermes 主导消化，或由用户指定的 Vibe Coding Tool 辅助整理"；D012 摘要同步。
- `AGENTS.md`：INBOX 消化表述从"Hermes / OpenCode"改为"Hermes 主导消化"。
- `HERMES_STEWARD.md`：第 7 节 OpenCode 从"本地项目管家控制台 / Harness Caretaker"改为"当前常用于 Memory Maintainer / Rule Maintainer，但属于 Vibe Coding Tool Pool，不是固定岗位"。
- `OPENCODE_USAGE.md`：标题加注"Vibe Coding Tool Pool 参考"，开头重新定位为"当 Vibe Coding Tool 被分配 Memory Maintainer / Rule Maintainer 角色时的使用边界"。
- `MODEL_ROLES.md`：工具选择参考补回"前端体验能力"和"审计能力"两个维度。
- `AI_MEMORY/TASK_LOG.md`：恢复被污染的通用模板，追加本轮记录。

未处理范围：

- 未修改业务代码。
- 未运行命令。
- 未安装依赖。
- 未构建。
- 未提交。

已执行验证：

- 已读取修正后 `DECISIONS.md` D012，确认已改为 Vibe Coding Tool Pool 表述。
- 已读取修正后 `PROJECT_BRIEF.md` 第 1 段和 D012 摘要，确认一致。
- 已读取修正后 `AGENTS.md` 第 26-27 行，确认不再写死 OpenCode。
- 已读取修正后 `HERMES_STEWARD.md` 第 81 行，确认不再写死 OpenCode 为 Harness Caretaker。
- 已读取修正后 `OPENCODE_USAGE.md` 标题和开头，确认已重新定位。
- 已读取修正后 `MODEL_ROLES.md` 工具选择参考，确认补回前端体验和审计维度。
- 已确认 TASK_LOG 模板已恢复为通用占位模板。

未执行验证：

- 未验证 WORKFLOW.md 中是否存在遗漏的 OpenCode 固定岗位表述。
- 未验证 Obsidian Vault Graph View。

风险：

- 低：WORKFLOW.md 可能仍有 OpenCode 固定岗位残留，但当前不阻塞主流程。
- 低：历史 TASK_LOG 中的旧记录仍写"执行工具：OpenCode"，属于历史事实，不需要回溯修改。

待确认：

- WORKFLOW.md 是否需要同步修正？（当前未在允许修改列表中）

下一步：

- 用户确认后，可检查 WORKFLOW.md。
- 或用 Obsidian 打开 Vault 确认 Graph View 正常。

## 2026-06-06

修复 WORKFLOW.md 中 OpenCode 固定配对残留。第 158 行 "→ Hermes / OpenCode 定期消化" 改为 "→ Hermes 主导消化，或由用户指定的 Vibe Coding Tool 辅助整理"。仅修改 WORKFLOW.md，其余文件未动。

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
