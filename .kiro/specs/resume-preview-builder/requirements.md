# Requirements Document

## Introduction

本特性（Resume Preview / Resume Builder，下称「简历预览构建器」）在已有的 `/files` 文档工作台之上，增加一条「自由草稿 → 结构化简历 JSON → 模板预览 → PDF / DOCX 导出」的产品链路，目标是把用户在富文本编辑器里的非结构化草稿，安全地转化为可被 ATS 解析、可被招聘者一眼读完的成品简历，同时坚决不让 AI 自己「编造」简历事实。

`/files` 工作台已经具备：Tiptap 富文本编辑、localStorage 草稿、TXT / PDF / DOCX 导出、对选中文本的 AI 润色（Polish / Suggest Completion / Creative Draft 三种模式）、事实安全锁（Fact-safety lock）。本特性在这些能力之上扩展，**不替换**现有 `/files` 工作台，也**不**改写现有富文本编辑器的语义。

v1 的核心定位是：

1. AI 仅做「抽取 + 重新组织」，不做「无中生有」。
2. 用户必须显式确认结构化结果后才能进入预览 / 导出。
3. v1 仅交付两个模板（ATS 单栏、技术岗双栏），且模板只负责样式。
4. v1 不接入 RAG / ChatDock / knowledge_chunks，不引入后端持久化（仍可继续使用 localStorage）。

本文档只描述需求（What / Why），不描述实现（How）。具体技术方案见 `design.md`，工程拆分见 `tasks.md`。

## Glossary

- **Resume_JSON**：本特性定义的结构化简历数据对象。固定包含 `basics`、`education`、`skills`、`projects`、`experience`、`awards`、`certificates`、`meta` 八个 Section，每个 Section 内部含一份 `missingFields` 列表。所有模板、预览、导出环节都以 Resume_JSON 为唯一数据源（Single Source of Truth）。
- **Field_Status（字段状态枚举）**：用于标注 Resume_JSON 中每个原子字段的来源与可信度，取值范围固定为 `confirmed`、`inferred_from_text`、`missing`、`needs_confirmation` 四种之一。
- **missingFields（缺失字段列表）**：每个 Resume_JSON Section 内挂载的字符串数组，列出该 Section 中状态为 `missing` 或 `needs_confirmation` 的字段键名，供前端高亮与导出风险判断使用。
- **confirmedByUser（用户确认标志）**：Resume_JSON `meta.confirmedByUser` 上的布尔值，表示用户已经在结构化表单里完成最终确认。仅当其为 `true` 且不存在未解决的缺失占位符时，预览与导出才被允许。
- **Fact_Safety_Lock（事实安全锁）**：贯穿本特性的核心约束机制。它要求 AI 抽取流程严格基于用户草稿，禁止补全外部知识或编造事实；任何无法从草稿中证据化的内容必须落入 missing / needs_confirmation 状态而不是直接写入字段值。
- **ATS_Template（ATS 单栏模板）**：v1 内置的第一个模板，标识符 `ats_single_column`，单栏线性排版，强调机器可解析性，纯 HTML / CSS 实现，只读消费 Resume_JSON。
- **Tech_Two_Column_Template（技术岗双栏模板）**：v1 内置的第二个模板，标识符 `tech_two_column`，左侧侧栏（基础信息 / 技能 / 证书）+ 右侧主栏（项目 / 工作 / 教育），纯 HTML / CSS 实现，只读消费 Resume_JSON。
- **Resume_Builder_Workspace（简历预览构建器工作区）**：本特性新增的 UI 区域，承载「左：草稿 / 中：结构化表单 / 右：预览」三栏式编辑体验，作为 `/files` 内部的全屏 Modal 呈现，不新建顶级路由。
- **Extract_Resume_API**：本特性新增的后端 AI 抽取接口，路径 `POST /api/document/extract-resume`，请求 `{document_id, plain_text, content_json, provider_id}`，响应 `{success, resume_json, warnings, missing_questions}`。
- **missing_questions（追问问题列表）**：Extract_Resume_API 返回的字符串数组，每条是 AI 对用户的一个具体补全提问，用于在结构化表单中作为「AI 建议追问」展示。
- **Document_Workbench（文档工作台）**：已有的 `/files` 页面，含 Tiptap 编辑器、localStorage 草稿、TXT / PDF / DOCX 导出、AI 选中润色（Polish / Suggest Completion / Creative Draft）。本特性以它为入口，不重写它。

## Requirements

### Requirement 1: 从文档工作台进入简历预览构建器

**User Story:** 作为已经在 `/files` 写好简历草稿的用户，我希望在不离开当前文档的前提下，一键把草稿送入「简历预览构建器」，从而避免反复复制粘贴。

#### Acceptance Criteria

1. THE Document_Workbench SHALL 在工具栏中提供一个名为「生成简历预览」（Generate Resume Preview）的入口按钮。
2. WHEN 用户点击「生成简历预览」按钮且当前文档存在可用草稿，THE Document_Workbench SHALL 在 1 秒内打开 Resume_Builder_Workspace，并把当前文档的 `plain_text`、`content_json`、`document_id` 作为输入透传给抽取流程;若 `plain_text` 长度超过 50000 字符,THE Document_Workbench SHALL 截断到 50000 字符并在 Resume_Builder_Workspace 中显示「草稿已截断到 50000 字符以内」提示。
3. THE Resume_Builder_Workspace SHALL 作为 `/files` 内部的全屏 Modal 呈现，不新增顶级路由;关闭 Resume_Builder_Workspace 后用户 SHALL 回到打开前所在的 Document_Workbench 视图,且原文档内容保持与打开前一致。
4. WHILE 当前文档去除所有 Unicode 空白字符（包括但不限于空格、制表符、换行符、零宽空格）后剩余可见字符数小于 10，THE Document_Workbench SHALL 同时满足以下三项可观测条件:(a) 「生成简历预览」按钮处于禁用态(disabled);(b) 用户对该按钮的点击动作不触发任何打开 Resume_Builder_Workspace 的行为;(c) 在按钮的固定关联位置(如 tooltip 或紧邻位置)展示提示文案「请先在文档中填写简历草稿」。
5. WHERE 用户在 Resume_Builder_Workspace 的结构化表单中已存在尚未保存的编辑(即当前 Resume_JSON 与上一次抽取结果存在差异),IF 用户再次点击「生成简历预览」,THEN THE Resume_Builder_Workspace SHALL 弹出确认提示,该提示必须包含且仅包含两个互斥按钮「确认覆盖」和「取消」:点击「确认覆盖」触发新一次抽取并丢弃当前未保存的编辑;点击「取消」关闭提示且 Resume_JSON 状态保持不变。
6. WHEN 用户在第 5 条所述的确认提示中通过点击「取消」按钮、点击关闭图标或按下 Esc 键中的任意一种方式取消操作,THE Resume_Builder_Workspace SHALL 关闭确认提示且当前 Resume_JSON 状态保持零变更。
7. IF 第 2 条所述的输入透传过程因 `plain_text`、`content_json` 或 `document_id` 中任一字段缺失或不可序列化而失败,THEN THE Document_Workbench SHALL 不打开 Resume_Builder_Workspace,展示错误提示「文档数据读取失败:<缺失字段名>」,且原 Document_Workbench 文档内容保持零变更。

### Requirement 2: AI 抽取的事实安全锁（Fact_Safety_Lock）

**User Story:** 作为不希望 AI 在我简历里造假的用户，我希望 AI 只整理我写过的内容，对于我没写过的部分必须如实标注「缺失」，而不是自行编造。

#### Acceptance Criteria

1. THE Extract_Resume_API SHALL 仅以用户提交的草稿（`plain_text` 与 `content_json`）作为事实来源，不得在任意原子字段的内容值中写入未在草稿中以字面或词形归一化（大小写/空白/标点归一化）形式出现的实体值，包括但不限于：人名、公司名、机构名、职位名、技能名、产品名、地名、时间值、数字指标、奖项名称、证书名称、链接 URL。
2. IF 草稿中找不到任何与某字段语义相关的可定位片段，THEN THE Extract_Resume_API SHALL 把该字段的 Field_Status 标记为 `missing`，且该字段的内容值必须为空字符串、`null` 或对应类型的空集合，不得写入示例值、占位符文案（如「待补充」「示例」「N/A」）或推断值。
3. IF 草稿中存在与某字段语义相关的片段但同时满足以下任一条件:(a) 存在两种及以上互斥解读;(b) 需要跨段落、跨条目或跨章节进行推断才能得出值;(c) 字段值依赖草稿未写明的事实(如时间区间缺失起止年份),THEN THE Extract_Resume_API SHALL 把该字段的 Field_Status 标记为 `needs_confirmation`,并将该字段键名加入对应 Section 的 missingFields 列表。
4. THE Extract_Resume_API SHALL 对每个原子字段输出 Field_Status，取值必须严格属于枚举集合 `{confirmed, inferred_from_text, missing, needs_confirmation}`;IF 输出包含枚举集合外的取值,THEN 调用方 SHALL 拒绝接收该响应并按 Requirement 4 第 5 条所述的 `json_parse_failed` 路径处理。
5. IF AI 在某条经历的时间、岗位名、公司名、项目名等关键事实上输出了非草稿原文逐字给出、而是基于上下文推断的值,THEN THE Extract_Resume_API SHALL 把该字段的 Field_Status 设为 `inferred_from_text`，并将该字段键名加入对应 Section 的 missingFields 列表，提示用户复核。
6. THE Extract_Resume_API SHALL 在响应的 `missing_questions` 数组中,针对每个 Field_Status 为 `missing` 或 `needs_confirmation` 的字段输出至少一条追问问题文案,每条文案必须满足:(a) 简体中文;(b) 长度在 8 至 80 个字符之间;(c) 包含目标字段对应的人类可读名称(如「在校时间」「公司名称」),不得仅给出字段键名。
7. IF AI 在响应中产生了草稿之外的内容（无法在 `plain_text` 或 `content_json` 中找到字面或词形归一化后的对应片段），THEN THE Extract_Resume_API SHALL 在 `warnings` 数组中追加一项,该项必须包含 `code=fabrication_suspected` 与受影响字段的键名列表,并要求前端在 UI 中向用户提示。
8. THE Extract_Resume_API SHALL 在响应中拒绝输出 Resume_JSON 之外的自由叙述、聊天式回复、Markdown 解释段落或多段 JSON 片段;IF 实际响应中检测到此类内容,THEN 调用方 SHALL 拒绝接收该响应并按 Requirement 4 第 5 条所述的 `json_parse_failed` 路径处理。

### Requirement 3: Resume_JSON 数据结构与字段覆盖

**User Story:** 作为下游模板与导出环节的开发者 / 用户，我希望简历数据有一个稳定、可预期的结构契约，让模板和导出可以放心消费。

#### Acceptance Criteria

1. THE Extract_Resume_API SHALL 输出固定包含且仅包含以下八个顶级 Section 键的 Resume_JSON 对象：`basics`、`education`、`skills`、`projects`、`experience`、`awards`、`certificates`、`meta`，缺失任一键或多出未定义的顶级键均视为非法响应。
2. THE Resume_JSON `basics` Section SHALL 固定包含字段键：`name`、`targetRole`、`email`、`phone`、`city`、`websiteOrRepo`，每个字段独立携带 Field_Status，取值范围 `{confirmed, missing, needs_confirmation}`。
3. THE Resume_JSON `education`、`projects`、`experience`、`awards`、`certificates` Section SHALL 以条目数组形式存在，数组下界为 0（即可以为空数组），单 Section 条目数量上限为 50；每个条目内每个字段独立携带 Field_Status，取值范围 `{confirmed, missing, needs_confirmation}`。
4. THE Resume_JSON `skills` Section SHALL 以分组数组形式组织，每个分组包含 `category`（字符串）与 `items`（字符串数组）两个键；分组数量上限为 10，单分组下 `items` 数量上限为 30；每一项技能独立携带 Field_Status，取值范围 `{confirmed, missing, needs_confirmation}`。
5. THE Resume_JSON 每个 Section（`basics`、`education`、`skills`、`projects`、`experience`、`awards`、`certificates`）SHALL 携带一个 `missingFields` 字符串数组，列出该 Section 中状态为 `missing` 或 `needs_confirmation` 的字段键名；该数组与该 Section 内字段 Field_Status 的并集必须保持一致，即不得出现 `missingFields` 与 Field_Status 互相矛盾的情况。
6. THE Resume_JSON `meta` Section SHALL 固定包含且仅包含字段键：`confirmedByUser`（布尔，默认 `false`）、`templateId`（字符串，取值范围严格限定为 `{ats_single_column, tech_two_column}`）、`generatedAt`（ISO 8601 UTC 时间字符串）、`sourceDocumentId`（非空字符串）。
7. WHEN 用户首次进入 Resume_Builder_Workspace，THE Resume_JSON `meta.confirmedByUser` SHALL 默认设置为 `false`，且 `meta.templateId` SHALL 默认设置为 `ats_single_column`。
8. IF Resume_JSON 出现以下任一情况：(a) 顶级键缺失或多余；(b) 任一字段的 Field_Status 取值越出枚举集合；(c) `meta.templateId` 取值越出 `{ats_single_column, tech_two_column}` 集合，THEN 调用方 SHALL 拒绝接收该响应并按 Requirement 4 第 5 条所述的 `json_parse_failed` 路径处理。

### Requirement 4: Extract_Resume_API 接口契约

**User Story:** 作为前端开发者，我希望 AI 抽取接口的请求与响应结构稳定，便于在 `/files` 工作台与 Resume_Builder_Workspace 之间安全集成。

#### Acceptance Criteria

1. THE Extract_Resume_API SHALL 暴露在路径 `POST /api/document/extract-resume`。
2. THE Extract_Resume_API SHALL 接受请求体字段 `document_id`（字符串，长度 1-128 字符）、`plain_text`（字符串，长度 ≤ 200000 字符）、`content_json`（对象，Tiptap content；序列化后 ≤ 1 MiB）、`provider_id`（字符串，长度 1-64 字符，标识 LLM 提供方）。
3. THE Extract_Resume_API SHALL 返回顶级字段 `success`（布尔）、`resume_json`（对象，结构遵循 Resume_JSON 契约，永不为 `null`）、`warnings`（字符串数组，元素必须取自预定义标识符集合 `{empty_input, json_parse_failed, extraction_timeout, fabrication_suspected, non_resume_content_detected}`）、`missing_questions`（字符串数组）。
4. WHEN AI 抽取成功完成，THE Extract_Resume_API SHALL 在 200 毫秒内（不计 LLM 调用时延）返回 `success=true`，`resume_json` 完整符合 Resume_JSON 契约，`warnings` 数组允许为空数组也允许包含 `fabrication_suspected` / `non_resume_content_detected` 之一或两者。
5. IF 请求体中 `plain_text` 与 `content_json` 同时为空、仅含空白字符（空格、制表符、回车、换行）或 `content_json` 缺失/为 `null`/为 `{}`/展开后纯空白，THEN THE Extract_Resume_API SHALL 不调用 LLM，返回 `success=false` 并在 `warnings` 中追加 `empty_input` 标识，`resume_json` 字段返回所有 Section 全部 missing 的安全骨架对象。
6. IF AI 返回的内容无法被解析为合法 Resume_JSON（包括 JSON 解析失败、顶级 Section 缺失、Field_Status 越出枚举、`meta.templateId` 越出枚举等任一情况），THEN THE Extract_Resume_API SHALL 返回 `success=false` 并在 `warnings` 中追加 `json_parse_failed` 标识，且 `resume_json` 字段返回一个所有 Section 全部 missing 的安全骨架对象，而不是 `null`。
7. THE Extract_Resume_API SHALL 把对 LLM 的调用与提示词构造完整委托给后端，前端不得直接拼接 LLM Prompt 或直接命中 LLM 提供方。
8. WHEN AI 抽取耗时超过 30 秒，THE Extract_Resume_API SHALL 返回 `success=false` 并在 `warnings` 中追加 `extraction_timeout` 标识，且 `resume_json` 字段返回所有 Section 全部 missing 的安全骨架对象。
9. IF 请求体中 `document_id` 缺失/空字符串/超出长度上限，或 `provider_id` 缺失/空字符串/超出长度上限，或 `plain_text` 超出 200000 字符，或 `content_json` 序列化后超出 1 MiB，THEN THE Extract_Resume_API SHALL 不调用 LLM，返回 `success=false`，`warnings` 中至少包含一项预定义标识符（如 `empty_input` 或新增的合法值）。

### Requirement 5: 抽取 Prompt 行为约束

**User Story:** 作为产品负责人，我希望抽取 Prompt 的行为有强约束，避免不同 LLM 提供方下出现「胡编」「越权改写」等不一致表现。

#### Acceptance Criteria

1. THE Extract_Resume_API SHALL 在调用 LLM 时使用一份存放于 `Service/Agents/prompts/` 目录下的 System Prompt 模板（不得在 Router 或 Agent 文件中硬编码 Prompt 字符串），该 Prompt 必须明确禁止编造未在草稿中出现的事实、姓名、岗位、公司、时间、技能等级等具体内容。
2. THE Extract_Resume_API SHALL 在调用 LLM 时强制要求 LLM 仅输出严格 JSON，且响应必须满足以下三项可观察条件：(a) 可被标准 JSON 解析器解析无错；(b) 顶级键集合严格等于 Resume_JSON 契约定义的八个 Section；(c) 每个原子字段类型与 Resume_JSON 契约一致。
3. IF LLM 首次响应不满足第 2 条任一条件，THEN THE Extract_Resume_API SHALL 重试 1 次（仅 1 次）；IF 重试后仍不满足，THEN THE Extract_Resume_API SHALL 返回 `success=false` 并在 `warnings` 中追加 `json_parse_failed` 标识，`resume_json` 返回安全骨架对象，且不得把 LLM 原始文本透传到前端响应中。
4. WHEN 用户草稿中存在自相矛盾或重复内容（包括但不限于：互斥的岗位描述、时间区间重叠的同期任职、对同一项目给出不一致的技术栈描述），THE Extract_Resume_API SHALL 在对应字段标记为 `needs_confirmation`，并在 `missing_questions` 中针对该矛盾点向用户提出至少一条澄清问题。
5. IF 草稿中包含明显与简历无关的内容（如日记、心情、待办事项、社交聊天记录），THEN THE Extract_Resume_API SHALL 在 `warnings` 数组中追加 `non_resume_content_detected` 标识，但仍尝试对疑似简历部分进行抽取，并不得因此中止整体抽取流程。
6. THE Extract_Resume_API SHALL 不在响应中夹带任何形式的 Markdown 代码块标记（如 ```json```、```、`<pre>` 等）、解释性自然语言、前后缀文本，也不得在同一响应中返回多个 JSON 片段；响应必须是一个且仅一个合法 JSON 对象。

### Requirement 6: 结构化确认表单的编辑能力

**User Story:** 作为用户，我希望在最终预览之前，能够在一个结构化表单里逐字段查看、修改、删除、补全 AI 抽取出的简历内容，并清晰看到 AI 没把握的字段。

#### Acceptance Criteria

1. THE Resume_Builder_Workspace SHALL 在中栏提供一个结构化表单，按 `basics`、`education`、`skills`、`projects`、`experience`、`awards`、`certificates` 分组渲染 Resume_JSON 的字段。
2. THE Resume_Builder_Workspace SHALL 允许用户对 Resume_JSON 中每个标量类型的原子字段进行编辑、清空操作，对数组型 Section（`education`、`projects`、`experience`、`awards`、`certificates`、`skills` 分组）进行新增条目、删除条目操作；任一变更必须在 500ms 内写回当前的 Resume_JSON 状态。
3. WHILE 某字段的 Field_Status 为 `missing` 或 `needs_confirmation`，THE Resume_Builder_Workspace SHALL 同时满足以下三项可观测条件：(a) 该字段输入框使用警示色边框；(b) 字段右上角展示警示角标；(c) 用户悬停或聚焦该字段时展示该状态的简短文案释义（如「AI 未在草稿中找到该字段」「需要你确认」）。
4. THE Resume_Builder_Workspace SHALL 在结构化表单顶部独立卡片中展示 Extract_Resume_API 返回的 `missing_questions` 列表；每条问题旁必须提供「采纳」与「忽略」两个互斥按钮；点击「采纳」SHALL 把焦点跳转并滚动到该问题对应的目标字段，且不修改 Resume_JSON；点击「忽略」SHALL 仅在前端会话中移除该条目，且不修改 Resume_JSON；当 `missing_questions` 条目数超过 20 时，该卡片 SHALL 启用内部滚动而不是无限增高。
5. WHEN 用户编辑了一个原本为 `missing`、`needs_confirmation` 或 `inferred_from_text` 的字段并填入符合以下任一定义的非空内容：(a) 字符串字段：trim 后长度 ≥ 1；(b) 数字字段：有限非 NaN 值；(c) 数组字段：长度 ≥ 1，THE Resume_Builder_Workspace SHALL 把该字段的 Field_Status 转为 `confirmed`，并把该字段键名从所属 Section 的 `missingFields` 数组中移除。
6. WHEN 用户清空了一个原本为 `confirmed` 或 `inferred_from_text` 的字段（清空判定与第 5 条非空判定互斥），THE Resume_Builder_Workspace SHALL 把该字段的 Field_Status 转为 `missing`，并把该字段键名加入所属 Section 的 `missingFields` 数组。
7. THE Resume_Builder_Workspace SHALL 提供一个「确认结构化结果」（Confirm Resume）操作；WHEN 用户点击该操作且 Resume_JSON 中不存在 Field_Status 为 `missing` 或 `needs_confirmation` 的字段，THE Resume_Builder_Workspace SHALL 把 `meta.confirmedByUser` 置为 `true`，并通过现有 Toast 组件展示「已确认结构化结果」轻提示。
8. IF Resume_JSON 中仍存在 Field_Status 为 `missing` 或 `needs_confirmation` 的字段，THEN THE Resume_Builder_Workspace SHALL 在用户点击「确认结构化结果」时弹出一个基于 BaseModal.vue 扩展的二次确认弹窗，弹窗内必须列出存在缺失的字段名（≤ 10 条时全部列出，> 10 条时折叠展示前 10 条 + 「等其余 N 项」），并提供「仍然确认」与「返回补全」两个互斥按钮。
9. WHEN 用户在第 8 条弹窗中点击「仍然确认」，THE Resume_Builder_Workspace SHALL 关闭弹窗、把 `meta.confirmedByUser` 置为 `true`，并通过 Toast 展示「已强制确认（仍含缺失字段）」提示。
10. WHEN 用户在第 8 条弹窗中点击「返回补全」、点击关闭图标或按下 Esc 键中的任意一种方式，THE Resume_Builder_Workspace SHALL 关闭弹窗，`meta.confirmedByUser` 保持原值（`false`），且 Resume_JSON 任何字段值与 Field_Status 保持零变更。

### Requirement 7: 模板系统（v1 仅两个模板，模板只决定样式）

**User Story:** 作为用户，我希望可以在两种业内常用的简历版式之间切换预览效果，但我不希望切换模板会改变我已经确认过的内容。

#### Acceptance Criteria

1. THE Resume_Builder_Workspace SHALL 在 v1 中提供且仅提供两个内置模板：标识符 `ats_single_column`（ATS 单栏）和 `tech_two_column`（技术岗双栏）；写入 `meta.templateId` 的值必须严格等于这两个标识符之一，超出枚举的取值视为非法。
2. THE ATS_Template SHALL 以单栏线性版式呈现，优先保证 ATS（Applicant Tracking System）可解析性，且不得使用以下任一布局元素：多栏 CSS Grid/Flex 多列布局、嵌套表格、`<textarea>` 文本框、固定页眉页脚、绝对定位（`position: absolute` / `fixed`）。
3. THE Tech_Two_Column_Template SHALL 以左侧侧栏（基础信息 / 技能 / 证书）+ 右侧主栏（项目 / 工作经历 / 教育）的双栏版式呈现，定位于技术岗候选人；同一字段值不得同时出现在左右两栏中（不得跨栏重复呈现同一原子字段）。
4. THE Resume_Builder_Workspace SHALL 把当前选中的模板标识符写入 Resume_JSON `meta.templateId`。
5. WHEN 用户在两个模板之间切换，THE Resume_Builder_Workspace SHALL 仅改变预览样式（CSS 类名、版式结构），不得修改 Resume_JSON 中除 `meta.templateId` 之外的任何字段值，也不得改变任何字段的 Field_Status；切换完成后预览样式更新过程不得触发整页刷新。
6. THE 内置模板 SHALL 仅以只读方式消费 Resume_JSON，不得在模板内部对字段做改写、补全、生成性扩写、文案润色或合并字段值。
7. THE 内置模板 SHALL 以 HTML / CSS 实现（不得引入运行时模板编译、`eval`、动态字符串拼接 HTML 等机制）。
8. WHERE 某 Section 在 Resume_JSON 中不存在、为空数组、或全部字段值为空 / `null`，THE 内置模板 SHALL 同时隐藏该 Section 的标题、分隔线、占位元素，不得渲染空白占位标题或空内容容器。
9. WHEN 用户首次进入 Resume_Builder_Workspace 且 `meta.templateId` 为空、缺失或不在合法枚举集合内，THE Resume_Builder_Workspace SHALL 把 `meta.templateId` 默认设置为 `ats_single_column` 并使用该模板渲染预览。
10. IF 模板切换过程中检测到 Resume_JSON 中除 `meta.templateId` 之外的任何字段值或 Field_Status 发生变化，THEN THE Resume_Builder_Workspace SHALL 回滚 `meta.templateId` 为切换前的值，并通过 Toast 展示「模板切换失败：检测到非法字段变更」提示。

### Requirement 8: 预览渲染与文本可拷贝性

**User Story:** 作为投递简历的用户，我希望预览出的简历能被招聘者复制粘贴，也能在 ATS 系统中被解析成文本，而不是变成一张图片。

#### Acceptance Criteria

1. WHEN Resume_Builder_Workspace 加载、Resume_JSON 任意字段被编辑、或用户切换模板，THE Resume_Builder_Workspace SHALL 在右栏渲染当前 Resume_JSON + 当前模板组合下的所见即所得（WYSIWYG）预览，且 `basics`、`education`、`skills`、`projects`、`experience`、`awards`、`certificates` 七个 Section 的字段必须以 DOM 文字节点（Text Node）方式呈现。
2. THE 预览区域 SHALL 渲染为可复制的 HTML 文本（使用 DOM 文字节点 + CSS 样式），且必须同时满足以下四项可观察条件：(a) 用户可通过鼠标拖选选中预览区域内任一文字片段；(b) `Ctrl+A` / `Cmd+A` 可全选预览区域文字；(c) `Ctrl+C` / `Cmd+C` 与浏览器右键「复制」可将选中文字写入剪贴板；(d) 预览区域内任一字段元素的 `user-select` 不得为 `none`，`pointer-events` 不得为 `none`。
3. WHEN Resume_JSON 任意字段被编辑或用户切换模板，THE 预览区域 SHALL 在不超过 500ms 内反映最新内容，且该反映过程必须基于本地 reactive state 完成，不得在该 500ms 窗口内对 Extract_Resume_API 或任何后端 HTTP/SSE 端点发起请求。
4. WHILE 内容总高度超过预览容器可视区域高度，THE 预览区域 SHALL 通过滚动或自动分页支持查看全部字段；THE 预览区域 SHALL 不得通过以下任一手段隐藏字段：截断字符串、折叠条目、对预览容器使用 `overflow: hidden` 且无替代滚动机制、通过 CSS 设置字段元素 `display: none` 或 `visibility: hidden`。
5. WHERE Resume_JSON 中某字段值为空字符串、`null`、或对应类型的空集合（且其 Field_Status 为 `missing` 或字段为可选字段），THE 预览区域 SHALL 跳过该字段的渲染（不渲染任何节点），且不得抛出渲染异常或中断当前预览过程。

### Requirement 9: 导出 PDF 与 DOCX

**User Story:** 作为最终要把简历投递出去的用户，我希望能从预览界面直接导出 PDF 和 DOCX，并保留可被解析的文本内容。

#### Acceptance Criteria

1. THE Resume_Builder_Workspace SHALL 提供「导出 PDF」与「导出 DOCX」两个操作入口。
2. WHEN 用户点击「导出 PDF」，THE 导出 PDF 流程（v1） SHALL 通过浏览器原生打印（`window.print()`）配合专用打印样式（print CSS）实现；导出结果中的简历正文文本 SHALL 保持为可被 PDF 文本抽取工具（如 `pdftotext`、PyMuPDF）完整提取的文本流，不得为位图、Canvas 文本或 SVG `<text>` 路径化呈现。
3. WHEN 用户点击「导出 DOCX」，THE 导出 DOCX 流程 SHALL 基于当前 Resume_JSON 进行结构化生成（使用现有 `docx` 包），不得通过把 Tiptap HTML 直接管道转 DOCX 来产出最终简历。
4. THE 导出 DOCX 结果 SHALL 同时保留以下四类结构化元素以便 ATS 与 Word 类编辑器解析：(a) 段落（Paragraph）结构；(b) 列表（无序列表 / 有序列表）结构；(c) 标题层级（Heading 1 / Heading 2 / Heading 3）；(d) 字符级排版（加粗、斜体、项目符号）。
5. IF Resume_JSON `meta.confirmedByUser` 为 `false`，THEN THE Resume_Builder_Workspace SHALL 同时满足：(a) 「导出 PDF」与「导出 DOCX」按钮处于禁用态（`disabled`）；(b) 用户对该按钮的点击不触发任何导出动作；(c) 在按钮的 tooltip 或紧邻位置展示提示文案「请先确认结构化结果」。
6. IF Resume_JSON 中仍存在 Field_Status 为 `missing` 或 `needs_confirmation` 的字段，THEN THE Resume_Builder_Workspace SHALL 在用户点击导出按钮时弹出基于 BaseModal.vue 扩展的风险确认弹窗，弹窗必须列出存在缺失的字段名（≤ 10 条时全部列出，> 10 条时展示前 10 条 + 「等其余 N 项」），并提供「忽略缺失继续导出」与「返回补全」两个互斥按钮，用户必须显式选择其一才能继续。
7. THE Resume_Builder_Workspace SHALL 按以下规则生成导出文件名：默认格式为 `<姓名>_<目标岗位>_<时间戳>.<扩展名>`；若 `basics.name` 为空字符串、`null` 或缺失，使用 `resume` 作为兜底前缀；文件名中所有跨平台非法字符（`/`、`\`、`:`、`*`、`?`、`"`、`<`、`>`、`|`）SHALL 替换为 `_`；文件名长度（不含扩展名）SHALL 截断至 100 字符以内；扩展名 SHALL 严格匹配导出格式（`.pdf` 或 `.docx`）。
8. IF 导出 DOCX 流程因生成异常（如 `docx` 包写入失败、Resume_JSON 数据非法）失败，THEN THE Resume_Builder_Workspace SHALL 不输出任何部分文件，保留 Resume_JSON 与编辑状态零变更，并通过 Toast 展示「导出失败，请重试」提示。

### Requirement 10: 与 `/files` 工作台既有能力的协作约束

**User Story:** 作为产品负责人，我不希望「简历预览构建器」破坏 `/files` 已有的草稿与 AI 润色体验，也不希望两边产生数据冲突。

#### Acceptance Criteria

1. THE Resume_Builder_Workspace SHALL 仅以只读方式访问 Document_Workbench 的 `content_json` 与 `plain_text`，且必须同时满足：(a) 不通过任何接口写回 Document_Workbench 的文档存储；(b) 不调用 Document_Workbench 的保存 / 同步 / 自动保存路径；(c) 不修改 Document_Workbench 在内存中的草稿对象引用所指向的字段值。
2. WHEN 用户在 Resume_Builder_Workspace 与 Document_Workbench 之间切换视图，THE Resume_Builder_Workspace 与 Document_Workbench SHALL 同时保留各自的本地编辑状态：(a) Document_Workbench 保留 Tiptap `content_json` 不变；(b) Resume_Builder_Workspace 保留当前 Resume_JSON 与每个字段的 Field_Status 不变；切换过程不得触发对后端任何接口的调用以避免数据冲突。
3. THE Document_Workbench 的 AI 润色（Polish / Suggest Completion / Creative Draft）能力 SHALL 仅作用于 Tiptap 选中文本，不得读取或写入 Resume_Builder_Workspace 中 Resume_JSON 的任何字段，也不得作用于结构化表单字段。
4. THE Resume_Builder_Workspace SHALL 不调用以下任一现有业务接口的 HTTP 端点或 SSE 端点：简历诊断（`/api/resume/*`）、模拟面试（`/api/interview/*`）、职业规划（`/api/career/*`）、RAG 检索（`/api/rag/*`、`/api/knowledge/*`）、ChatDock / 多智能体分发（`/api/agent/*`）、历史归档（`/api/history/*`）。
5. WHERE Document_Workbench 已使用 localStorage 维护草稿，THE Resume_Builder_Workspace SHALL 复用 localStorage 作为 v1 的临时存储方案，但必须使用与 Document_Workbench 草稿键不同的独立命名空间前缀（如 `resume_builder:` 前缀），以避免键冲突。
6. IF localStorage 写入失败（包括但不限于配额超限、浏览器禁用 localStorage、隐私模式下抛出 `QuotaExceededError`），THEN THE Resume_Builder_Workspace SHALL 保留当前内存状态不丢失，并通过 Toast 展示「本地存储写入失败，请检查浏览器存储配额」提示，不得静默丢弃 Resume_JSON 数据。

### Requirement 11: 风险约束与失败处理（对应已识别风险项）

**User Story:** 作为风险负责人，我希望在需求层就把已知高风险项以可测试的形式锁住，避免它们在实现阶段被悄悄绕过。

#### Acceptance Criteria

1. IF 用户在 `meta.confirmedByUser=false` 的状态下点击「导出 PDF」或「导出 DOCX」按钮，THEN THE Resume_Builder_Workspace SHALL 同时满足：(a) 不触发任何导出动作；(b) 保留用户当前所有编辑数据零变更；(c) 通过现有 Toast 组件展示「请先在表单底部点击『确认结构化结果』」提示，提示展示时长 ≥ 3 秒。
2. IF Extract_Resume_API 调用响应 HTTP 非 2xx、或响应 body 无法被 JSON 解析、或解析后缺失 `basics` / `education` / `experience` / `projects` / `skills` 任一顶级 Section，THEN THE Resume_Builder_Workspace SHALL 同时满足：(a) 在中栏展示「AI 抽取失败，可手工填写」提示；(b) 加载一份所有顶级 Section 全部存在但字段全部为空 / `missing` 的安全骨架 Resume_JSON 供用户手工填写；(c) 不卸载当前页面，不跳转路由，不抛出未捕获异常。
3. IF 内置模板渲染时任一 Section 的内容总高度超出当前模板定义的单页可视范围（如 A4 页面尺寸），THEN THE 内置模板 SHALL 通过滚动或自动分页处理保持所有字段可见；THE 内置模板 SHALL 不得使用以下任一手段压缩内容：DOM 节点 `display: none` / `visibility: hidden`、容器 `overflow: hidden` 且无替代滚动机制、对字符串截断（如 `text-overflow: ellipsis` 用于隐藏正文）。
4. WHEN 用户清除浏览器缓存或在新设备打开 `/files` 后进入 Resume_Builder_Workspace，THE Resume_Builder_Workspace SHALL 在 1 秒内同时满足：(a) 展示空状态视图；(b) 视图包含标题文案「暂无本地结构化简历」；(c) 视图包含引导按钮「从当前文档生成」；(d) 不抛出未捕获异常，不渲染白屏。
5. THE Resume_Builder_Workspace SHALL 不向 `/files` 之外的核心业务接口（包括但不限于简历诊断 `Router/resumeDiagnosis.py`、知识库、历史归档、面试、职业规划）写入或同步任何字段，以避免与现有数据流耦合。
6. THE Extract_Resume_API SHALL 通过统一 LLM 调用入口（`Service/Utils/llm_client.py`）发起对 LLM 的调用；THE Router 层 SHALL 不直接通过 `httpx`、`requests` 或其他 HTTP 客户端发起对 LLM 提供方的请求。
7. WHEN AI 抽取过程中 `warnings` 数组中包含 `fabrication_suspected` 标识，THE Resume_Builder_Workspace SHALL 在结构化表单顶部展示一条复用现有横幅样式的红色警告横幅，文案为「AI 可能编造内容，请逐项核对」；该横幅 SHALL 在用户主动点击关闭按钮或在受影响字段全部完成 `confirmed` 转换之前持续可见，不得自动消失。

## Non-Goals (v1)

为避免范围漂移，以下能力**显式不**纳入 v1 范围：

1. **不接入 RAG**：v1 不调用 `Service/Services/rag_service.py`，不读取 `knowledge_chunks`，不基于知识库给简历做「能力补全」。
2. **不集成 ChatDock**：v1 的 Resume_Builder_Workspace 不暴露聊天框 / 多轮 AI 对话面板，所有 AI 交互仅通过 Extract_Resume_API 一次性抽取。
3. **不引入后端持久化**：v1 不在 SQLite / PostgreSQL 中新增 `resume_drafts` 类表，Resume_JSON 仅在前端 localStorage 中维护，后端持久化推迟到后续版本。
4. **不写入 knowledge_chunks**：v1 抽取出的简历结构化数据不进入任何向量库 / 知识库索引。
5. **不做服务端 PDF 渲染**：v1 不引入 Playwright / Puppeteer 等服务端无头浏览器栈，PDF 仅通过浏览器打印 + print CSS 实现，服务端 PDF 推迟到后续版本。
6. **不超过两个模板**：v1 仅内置 `ats_single_column` 与 `tech_two_column`，不开放自定义模板编辑器，不上架第三方模板市场。
7. **不做移动端优先预览**：v1 简历预览体验以桌面端为主，移动端只保证可访问，不保证排版精确度。
