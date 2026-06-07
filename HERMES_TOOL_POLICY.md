# Hermes Tool Policy

本文件定义 AI Career Navigator 当前阶段对 Hermes / OpenCode / Codex / Claude Code / CCSwitch 的轻量工具治理策略。

更新时间：2026-05-29

## 1. 固定角色与 Vibe Coding Tool Pool

固定角色（有明确职责边界）：

- Hermes：Project Steward / 管家 / 记录员 / 交接摘要 / Skill 治理。
- CCSwitch：Provider / 路由 / 配置 / Skills / MCP / WebUI 管理中枢。

Vibe Coding Tool Pool（可替换执行器，没有永久固定职责）：

- Codex、OpenCode、Trae、Kiro、Antigravity、Cursor、Qoder、WorkBuddy、Claude Code、未来新增的任何 vibe coding 工具。
- 这些工具的本轮角色由任务提示词临时指定（Implementer / Auditor / Reviewer / UI Polisher / Backend Fixer / Memory Maintainer / Rule Maintainer / Experiment Runner 等）。
- 工具名不决定角色，任务模式决定角色。
- OpenCode 当前常用于 Memory Maintainer / Rule Maintainer，但不是固定岗位，也不是 Hermes 本体。

## 2. Skill 与 MCP 区别

- Skill = 可复用任务方法 / 操作手册 / 程序化知识。
- MCP = 外部工具连接 / GitHub / 文件系统 / 浏览器 / 数据库 / API。

## 3. Hermes 当前允许

- 项目简报 Skill。
- 收工报告 Skill。
- AI_MEMORY 总结 Skill。
- 只读审计 Skill。
- 任务拆分 Skill。
- Hermes Steward Discipline Skill。

## 4. Hermes 当前暂不允许

- 数据库写入 MCP。
- 全盘文件写入 MCP。
- GitHub merge / push / release MCP。
- Secrets 管理 MCP。
- 云服务器 SSH 高权限 MCP。
- 自动 npm install / pip install / build / test。

## 5. 安装原则

- 一次只装一个 Skill 或 MCP。
- 先只读，后写入。
- 先低风险，后高风险。
- 每次安装后写 `AI_MEMORY/TASK_LOG.md`。
- 高风险 MCP 必须用户明确授权。

## 6. 模型分工

- Hermes 默认：MiMo。
- Hermes 高难度审计：DeepSeek V4 Pro。
- Hermes 中文规则维护：GLM 5.1。
- 重大 CTO 判断：GPT-5.5 / Claude 顶级模型人工复核。
- OpenCode 默认：MiMo / GLM。
- Codex / Claude Code：业务代码开发执行器。

## 7. 当前结论

- Hermes 已成功接入 MiMo。
- Hermes 不强行走 CCSwitch local router。
- CCSwitch 继续负责 Codex 路由、配置导入、Skills / Memory / MCP / WebUI 管理。
- Vibe Coding Tool Pool 中的工具没有永久固定职责，由任务提示词临时指定角色。
- Hermes 暂不作为默认业务代码开发器。
