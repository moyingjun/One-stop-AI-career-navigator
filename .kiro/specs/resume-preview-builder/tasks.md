# Implementation Plan: Resume Preview Builder（简历预览构建器）

> 本任务列表严格对齐 `requirements.md`(11 个 Requirement, 84 条 Acceptance Criteria) 与 `design.md`(21 条 Correctness Properties)。每条任务都标注 `_Requirements: X.Y_`,property 测试子任务额外标注其覆盖的 Property 编号。
>
> 工程红线遵循 `.kiro/steering/`:
> - 后端四层分离(Router → Service → Agents → Utils),Prompt 全量放 `Service/Agents/prompts/`,LLM 调用统一走 `Service/Utils/llm_client.py`,环境变量统一走 `Settings/config.py`。
> - 前端 SFC 扁平放 `frontend/src/`,复用组件放 `frontend/src/components/`,弹窗基于 `BaseModal.vue`,Toast 基于 `Toast.vue`,加载态基于 `StreamingLoader.vue`,坚持 Dark Cyberpunk + Glassmorphism。
> - 全部用户可见文案使用简体中文,业务注释 / docstring 使用中文,变量与标识符使用英文。
> - **禁止** `vue-tsc` / `tsc` / `vite build` / `npm run build`。后端验证使用 `pytest`,前端验证使用 `vitest --run`。

## Overview

把 `/files` 文档工作台(`frontend/src/KnowledgeBase.vue`)上的 Tiptap 草稿,通过新增的后端接口 `POST /api/document/extract-resume` 一次性抽取为 Resume_JSON;前端在 `BaseModal` 全屏 Modal 中渲染三栏式 `Resume_Builder_Workspace`(只读草稿 / 结构化表单 / 模板预览),用户确认后通过浏览器打印导出 PDF、通过 `docx` 包结构化导出 DOCX。

实现节奏:

1. 后端:Pydantic 模型 → Resume_JSON 工具层 → Prompt 模板 → Agent → Service 编排 → Router 接口
2. 前端:纯函数工具 → Pinia Store → HTTP 客户端 → 三栏 Workspace 与子组件 → 模板与预览 → 导出工具栏 → 接入 `/files`
3. 收尾:整体回归,确保所有测试通过

## Tasks

- [ ] 1. 扩展 Pydantic 请求 / 响应模型(`Router/models/document_model.py`)

  - [ ] 1.1 新增 `ExtractResumeRequest` / `ExtractResumeResponse` / `FieldStatus` 枚举
    - 在 `Router/models/document_model.py` 追加 `ExtractResumeRequest`(`document_id` 1..128、`plain_text` ≤ 200000、`content_json` 序列化 ≤ 1 MiB、`provider_id` 1..64 可空)与 `ExtractResumeResponse`(`success`、`resume_json` 永不为 null、`warnings` 取自 5 元素白名单、`missing_questions`)。
    - 实现 `content_json` 字段 1 MiB 边界校验、`warnings` 元素白名单校验。
    - 引入 `FieldStatus` 枚举 `{confirmed, inferred_from_text, missing, needs_confirmation}` 供后续模块复用。
    - _Requirements: 4.2, 4.3, 4.9, 2.4, 3.6_

  - [ ]* 1.2 边界单元测试 — `tests/Router/test_extract_request_validation.py`
    - 覆盖 `document_id` 长度越界、`plain_text` 超过 200000、`content_json` 序列化超过 1 MiB、`warnings` 越界 code 等用例。
    - _Requirements: 4.2, 4.9_

- [ ] 2. 实现 Resume_JSON 工具层(`Service/Utils/resume_json_validator.py` 新增)

  - [ ] 2.1 实现纯函数模块
    - 新建文件,导出 `validate_resume_json_contract`、`build_safe_skeleton`、`parse_resume_json`、`enforce_missing_fields_invariant`、`detect_fabrication`、`detect_non_resume_content`。
    - `validate_resume_json_contract`:校验 8 个顶级 Section、`basics` 6 字段、Field_Status 枚举、`meta.templateId` 枚举、数组长度上限(`education/projects/experience/awards/certificates ≤ 50`,`skills.items ≤ 10`,单分组 `items ≤ 30`)。
    - `parse_resume_json`:容忍 ` ```json ... ``` ` 围栏,解析失败、夹带解释段、多 JSON 片段一律返回 `None`。
    - `build_safe_skeleton(document_id)`:输出所有 Section 全 missing 的安全骨架,`meta.templateId="ats_single_column"`,`confirmedByUser=False`,`generatedAt=ISO8601 UTC`,`sourceDocumentId=document_id`。
    - `enforce_missing_fields_invariant`:让 `missingFields` ⟺ `Field_Status ∈ {missing, needs_confirmation, inferred_from_text}` 强一致 + 幂等;对 `Field_Status==="missing"` 的标量字段强制空值。
    - `detect_fabrication`:对 `Field_Status ∈ {confirmed, inferred_from_text}` 的标量字段做 NFKC + casefold + 压平空白 + 剔除标点的子串可定位检查;返回不可定位字段键名集合。
    - `detect_non_resume_content`:基于关键词 / 占比的启发式判定。
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.5, 4.6, 4.8, 5.2, 5.6, 5.5, 11.2_

  - [ ]* 2.2 Property 7 测试 — `tests/Service/test_resume_json_contract_pbt.py`
    - **Property 7: Resume_JSON 契约校验**
    - **Validates: Requirements 2.4, 3.1, 3.2, 3.3, 3.4, 3.6, 3.8, 5.2, 7.1**

  - [ ]* 2.3 Property 9 测试 — `tests/Service/test_parse_resume_json_pbt.py`
    - **Property 9: parse_resume_json 鲁棒性(围栏剥离 / 多 JSON 拒收 / 解释段拒收)**
    - **Validates: Requirements 2.8, 4.6, 5.6**

  - [ ]* 2.4 Property 10 测试 — `tests/Service/test_safe_skeleton_pbt.py`
    - **Property 10: 安全骨架默认值(契约通过 / templateId / confirmedByUser / sourceDocumentId)**
    - **Validates: Requirements 3.7, 4.5, 4.6, 4.8, 7.9, 11.2**

  - [ ]* 2.5 Property 6 测试 — `tests/Service/test_missing_fields_invariant_pbt.py`
    - **Property 6: missingFields ↔ Field_Status 互蕴 + 幂等 + missing 字段值为空**
    - **Validates: Requirements 2.2, 2.3, 2.5, 3.5, 6.5, 6.6**

  - [ ]* 2.6 Property 5 测试 — `tests/Service/test_resume_extract_fabrication_pbt.py`
    - **Property 5: Fact_Safety_Lock 反编造可定位(NFKC + casefold + 压平空白匹配)**
    - **Validates: Requirements 2.1, 2.5, 2.7, 11.7**

  - [ ]* 2.7 非简历内容启发式边界测试 — `tests/Service/test_non_resume_content_example.py`
    - 覆盖日记 / 待办 / 聊天 / 边缘正常简历四类样本,断言 `detect_non_resume_content` 返回值。
    - _Requirements: 5.5_

- [ ] 3. 抽取 Prompt 模板(`Service/Agents/prompts/resume_extract_prompts.py` 新增)

  - [ ] 3.1 新建 Prompt 模板模块
    - 导出 `SYSTEM_PROMPT`(声明角色、Fact_Safety_Lock、8 个 Section 列表、Field_Status 4 枚举、`templateId` 取值、严格 JSON、不允许 Markdown 围栏 / 解释段 / 多个 JSON 片段)、`USER_PROMPT_TEMPLATE`、`RETRY_REMINDER`、`FACT_SAFETY_RULES`、`build_extract_messages(plain_text, content_json, is_retry)`。
    - 严禁在 `Router/document.py` 或 `Service/Agents/resume_extract_agent.py` 中硬编码任何 SYSTEM_PROMPT 字符串。
    - _Requirements: 5.1, 5.6, 2.1, 2.6, 5.4_

- [ ] 4. 抽取 Agent(`Service/Agents/resume_extract_agent.py` 新增)

  - [ ] 4.1 实现 `ResumeExtractAgent.extract(...)`
    - 仅负责构造 `messages` 与调用 `Service/Utils/llm_client.complete_chat(messages=..., temperature=0.1, max_tokens=4096, timeout=30.0, provider_id=...)`。
    - `is_retry=True` 时在 user prompt 末尾追加 `RETRY_REMINDER`。
    - LLM 返回为 `None` / 空白时抛 `LLMClientError`。
    - 不做契约校验、不做反编造比对(那些归 Service 层)。
    - _Requirements: 5.1, 5.3, 11.6, 4.8_

  - [ ]* 4.2 Agent 静态约束烟测 — `tests/Service/test_extract_agent_no_hardcoded_prompt.py`
    - 静态 grep `Service/Agents/resume_extract_agent.py`,断言不含三引号 SYSTEM 字符串、不直接 `import httpx`。
    - _Requirements: 5.1, 11.6_

- [ ] 5. Service 业务编排(扩展 `Service/document_service.py`)

  - [ ] 5.1 实现 `extract_resume_from_draft(...)`
    - 空输入分支:`plain_text` 与 `content_json` 同时纯空白时,直接返回安全骨架 + `warnings=[empty_input]`,不调用 LLM。
    - 越界分支(防御):返回安全骨架 + `warnings=[empty_input]`。
    - 调用 `ResumeExtractAgent.extract`,套 `asyncio.wait_for(timeout=EXTRACT_TIMEOUT_SECONDS=30)`;超时返回安全骨架 + `warnings=[extraction_timeout]`;`LLMClientError` 返回安全骨架 + `warnings=[json_parse_failed]`。
    - 解析 + 一次性重试:首次 `parse_resume_json` 失败时调用 `agent.extract(is_retry=True)` 再解析;两次失败返回安全骨架 + `warnings=[json_parse_failed]`。
    - 调 `validate_resume_json_contract` 失败 → 安全骨架 + `warnings=[json_parse_failed]`。
    - 调 `detect_fabrication` 命中 → `warnings.append("fabrication_suspected")`;`detect_non_resume_content` 命中 → `warnings.append("non_resume_content_detected")`。
    - 调 `enforce_missing_fields_invariant`,注入 `meta.sourceDocumentId / generatedAt / templateId / confirmedByUser=False`。
    - 抽取并过滤 `missing_questions`(只保留 8..80 字符的字符串)。
    - 整个流程绝不向上抛出 5xx,Router 始终能拿到 `ExtractResumeResponse`。
    - 提供常量 `EXTRACT_TIMEOUT_SECONDS = 30`(从 `Settings/config.py` 取或在本文件硬编码常量,**不得** 调用 `os.getenv`)。
    - _Requirements: 4.5, 4.8, 4.9, 5.3, 5.4, 5.5, 2.6, 2.7, 11.2, 11.7, 3.7_

  - [ ]* 5.2 Property 11 测试 — `tests/Service/test_extract_retry_pbt.py`
    - **Property 11: LLM 解析失败重试一次(LLM 调用恰好 2 次,success=false,warnings 含 json_parse_failed,resume_json 为安全骨架,不透传原文)**
    - **Validates: Requirements 5.3, 4.6, 11.2**

  - [ ]* 5.3 Property 8 测试 — `tests/Service/test_missing_questions_filter_pbt.py`
    - **Property 8: missing_questions 长度过滤(最终数组每条字符串长度 ∈ [8, 80])**
    - **Validates: Requirements 2.6**

  - [ ]* 5.4 抽取超时与非简历内容例子级测试 — `tests/Service/test_extract_timeout_and_non_resume_example.py`
    - mock LLM 30s 不返回,断言 `warnings=[extraction_timeout]` + 安全骨架。
    - 输入纯日记内容,断言 `warnings` 含 `non_resume_content_detected` 且仍尝试抽取。
    - _Requirements: 4.8, 5.5_

- [ ] 6. Router 接口(扩展 `Router/document.py`)

  - [ ] 6.1 暴露 `POST /api/document/extract-resume`
    - 依赖 `get_current_user`(JWT),入参 `ExtractResumeRequest`,出参 `ExtractResumeResponse`。
    - 仅 `await extract_resume_from_draft(...)` + 兜底 `HTTPException(500, "简历抽取服务异常: <type>")`;不构造 Prompt、不直接 `import httpx`、不调用任何 LLM 端点。
    - 与 `/api/document/rewrite` 不同,`extract-resume` 永远返回 200 + 业务级 `success` 字段。
    - _Requirements: 4.1, 4.2, 4.7, 11.6, 11.2_

  - [ ]* 6.2 路由烟测 — `tests/Router/test_extract_resume_route_smoke.py`
    - 启动 TestClient,断言 `POST /api/document/extract-resume` 在无 JWT 时返回 401 / 403,带 JWT 时 200。
    - 断言 `GET /openapi.json` 中存在该路径且声明依赖 JWT。
    - mock LLM 立即返回合法 JSON,断言端到端 200ms 内返回(不计 LLM 时延)。
    - _Requirements: 4.1, 4.4, 4.7_

  - [ ]* 6.3 Router 不直接调 LLM 静态扫描 — `tests/Router/test_no_direct_httpx_in_router.py`
    - grep `Router/document.py`,断言不 `import httpx`,不出现任何 LLM Provider URL 字面量。
    - grep `frontend/src/services/resumeBuilderClient.js`,断言只命中 `/api/document/extract-resume`,不命中 `/api/resume`、`/api/interview`、`/api/career`、`/api/rag`、`/api/knowledge`、`/api/agent`、`/api/history`。
    - _Requirements: 11.5, 11.6, 10.4_

- [ ] 7. 后端检查点
  - 运行 `pytest tests/ -q`,确保 Task 1-6 全部通过;若 LLM 行为类断言不稳定先修 mock。Ensure all tests pass, ask the user if questions arise.

- [ ] 8. 前端纯函数工具层(`frontend/src/utils/`)

  - [ ] 8.1 新建 `resumeJsonSchema.js`
    - 导出 `applyFieldEdit(json, path, value)` / `patchField` / `switchTemplate(json, templateId)` / `addArrayItem(json, sectionPath, template)` / `removeArrayItem(json, sectionPath, index)` / `isEmptyValue(v)` / `readField(json, path)` / `containsMissing(json, path)` / `iterAtomicFields(json)` / `isValidResumeJson(json)`。
    - 全部为纯函数,不读 store、不读 DOM、不发 HTTP。
    - `switchTemplate` 仅写 `meta.templateId`,其他字段值与 `Field_Status` 严格不变;模板 ID 越界返回原对象。
    - 字段路径示例:`basics.name`、`education.items[0].school`、`skills.items[1].items[3].name`。
    - _Requirements: 6.5, 6.6, 7.5, 7.6, 7.10, 3.5_

  - [ ]* 8.2 Property 12 测试 — `frontend/tests/utils/patchField.pbt.test.js`
    - **Property 12: patchField 状态一致(空值 → missing 且加入 missingFields,非空 → confirmed 且移除;其他字段深相等)**
    - **Validates: Requirements 6.5, 6.6**

  - [ ]* 8.3 Property 14 测试 — `frontend/tests/utils/switchTemplate.pbt.test.js`
    - **Property 14: switchTemplate 窄影响(只改 meta.templateId,其余深相等;越界 templateId 回滚)**
    - **Validates: Requirements 7.5, 7.6, 7.10**

  - [ ] 8.4 新建 `truncatePlainText.js` 与 `canOpenWorkspace.js`
    - `truncatePlainText(s, max=50000)`:返回长度不超过 `max` 的截断字符串;`s` 本身不超时直接返回 `s`。
    - `stripUnicodeWhitespace(s)`:剥离全部 Unicode 空白(空格 / Tab / 换行 / 零宽 / U+3000 等)。
    - `canOpenWorkspace(s)`:返回 `stripUnicodeWhitespace(s).length >= 10`。
    - _Requirements: 1.2, 1.4_

  - [ ]* 8.5 Property 1 测试 — `frontend/tests/utils/truncatePlainText.pbt.test.js`
    - **Property 1: 草稿截断保持上限(out.length ≤ 50000;s.length ≤ 50000 时 out === s)**
    - **Validates: Requirements 1.2**

  - [ ]* 8.6 Property 3 测试 — `frontend/tests/utils/canOpenWorkspace.pbt.test.js`
    - **Property 3: 「生成简历预览」按钮启用规则(canOpenWorkspace ⟺ stripUnicodeWhitespace(s).length ≥ 10)**
    - **Validates: Requirements 1.4**

  - [ ] 8.7 新建 `resumeFilename.js`
    - `buildExportFilename(basics, ext)`:按 `<姓名>_<目标岗位>_<时间戳>.<扩展名>` 组装;`basics.name` 为空 / null / 缺失时前缀回落 `resume`;替换跨平台非法字符 `/ \ : * ? " < > |` 为 `_`;不含扩展名部分截断到 100 字符;扩展名严格匹配 `pdf` / `docx`,其他值兜底 `pdf`。
    - _Requirements: 9.7_

  - [ ]* 8.8 Property 20 测试 — `frontend/tests/utils/resumeFilename.pbt.test.js`
    - **Property 20: 导出文件名规则(无非法字符 / 长度 ≤ 100 / 扩展名 ∈ {pdf, docx} / 缺名前缀为 resume)**
    - **Validates: Requirements 9.7**

  - [ ] 8.9 新建 `resumeDocxBuilder.js`
    - 基于 `docx` 包(已有依赖)直接消费 Resume_JSON 构造 `Document` 对象,生成 Heading 1 / 2 / 3、Paragraph、UnorderedList / OrderedList、Run({bold, italics})。
    - 严禁 Tiptap HTML → DOCX 直管道。
    - 失败时抛 `ResumeDocxBuildError`,由 `ExportToolbar.vue` 捕获。
    - _Requirements: 9.3, 9.4, 9.8_

  - [ ]* 8.10 DOCX 结构属性测试 — `frontend/tests/utils/resumeDocxBuilder.pbt.test.js`
    - 任意非空 Resume_JSON,调用 `buildDocxBlob` 后用 `JSZip` 解压 `word/document.xml`,断言至少含一个 `Heading1` 段落、含 `<w:numPr>` 列表元素、不引用 Tiptap state。
    - _Requirements: 9.3, 9.4_

- [ ] 9. 前端 Pinia Store(`frontend/src/stores/resumeBuilderStore.js` 新增)

  - [ ] 9.1 实现 `useResumeBuilderStore`
    - state:`resumeJson`、`missingQuestions`、`dismissedQuestions: Set`、`warnings`、`isDirty`、`lastExtractAt`、`documentId`。
    - actions:`initFromDraft(draft)` / `reextractFromDraft(draft)` / `patchField(path, value)`(内部调用 8.1 纯函数)/ `addArrayItem(sectionPath, template)` / `removeArrayItem(sectionPath, index)` / `switchTemplate(templateId)`(检测到非法字段变更则回滚 + Toast)/ `confirmResume(force=false)`(返回值或事件:`{ok, missingFields}`)/ `dismissQuestion(idx)` / `saveLocalStorage()` / `loadLocalStorage(documentId)` / `clearDismissedQuestions()`。
    - localStorage 写入键名严格以 `resume_builder:` 前缀开头,其中 `resume_builder:current:{documentId}`、`resume_builder:dismissed:{documentId}`、`resume_builder:meta`。
    - 写入失败(`QuotaExceededError` / `SecurityError`)时 try/catch 兜底 + Toast「本地存储写入失败,请检查浏览器存储配额」。
    - 每个 action 末尾 try/catch 兜底,绝不抛未捕获异常。
    - _Requirements: 6.7, 6.8, 6.9, 7.5, 7.10, 8.3, 10.5, 10.6, 11.7_

  - [ ]* 9.2 Property 13 测试 — `frontend/tests/stores/confirmResume.pbt.test.js`
    - **Property 13: confirmResume 状态机(force=false 含 missing 时不变 + 弹窗事件;force=true 始终置 true 且其他字段深相等;取消路径保留原 confirmedByUser)**
    - **Validates: Requirements 6.7, 6.8, 6.9, 6.10**

  - [ ]* 9.3 Property 21 测试 — `frontend/tests/stores/storageNamespace.pbt.test.js`
    - **Property 21: localStorage 命名空间隔离(所有 setItem key 严格以 `resume_builder:` 前缀开头,从不写 `files:` / 工作台前缀)**
    - **Validates: Requirements 10.5**

  - [ ]* 9.4 Property 18 测试 — `frontend/tests/stores/noHttpDuringEdit.pbt.test.js`
    - **Property 18: 编辑 / 切换不触发 HTTP(任意 patchField / switchTemplate / addArrayItem / removeArrayItem 序列,fetch / XHR / EventSource 调用次数严格为 0)**
    - **Validates: Requirements 8.3, 10.1, 10.2, 10.4, 11.5**

  - [ ]* 9.5 存储配额异常测试 — `frontend/tests/stores/handleStorageQuotaError.test.js`
    - mock `Storage.prototype.setItem` 抛 `QuotaExceededError`,断言内存状态保留 + Toast 调用 + 不抛未捕获异常。
    - _Requirements: 10.6_

- [ ] 10. 前端 HTTP 客户端(`frontend/src/services/resumeBuilderClient.js` 新增)

  - [ ] 10.1 实现 `extractResumeFromDraft(payload)`
    - 使用原生 `fetch` 调用 `POST /api/document/extract-resume`,带 `authHeaders()`。
    - 非 2xx / JSON 解析失败 / 缺顶级 Section 时回退到本地安全骨架 `buildClientFallback()`,确保 Workspace 不白屏 / 不跳路由 / 不抛未捕获异常。
    - 仅命中 `/api/document/extract-resume` 一个端点,严禁触达 `/api/resume`、`/api/interview`、`/api/career`、`/api/rag`、`/api/knowledge`、`/api/agent`、`/api/history`。
    - _Requirements: 4.1, 4.7, 11.2, 11.5, 10.4_

  - [ ]* 10.2 客户端命中端点静态扫描 — `frontend/tests/services/resumeBuilderClient.scope.test.js`
    - grep 该文件源文本,断言只命中 `/api/document/extract-resume`,不命中 7 类禁用前缀。
    - _Requirements: 10.4, 11.5_

- [ ] 11. Resume Builder 三栏 Workspace 与子组件(`frontend/src/components/`)

  - [ ] 11.1 新建 `ResumeBuilderWorkspace.vue`(基于 `BaseModal.vue`,`size="full"`)
    - 顶栏:标题「简历预览构建器」+ 模板下拉切换 + 关闭按钮。
    - 三栏:左 320px(`DraftReadonlyPanel`) / 中 flex-1(`StructuredResumeForm`) / 右 480-640px(`ResumePreviewPanel` + `ExportToolbar`)。
    - props.draft 进入时:`plain_text.length > 50000` 已被 `/files` 截断,顶部展示「草稿已截断到 50000 字符以内」提示;1 秒内调用 `resumeBuilderStore.initFromDraft(draft)` 或加载 localStorage。
    - 关闭路径(顶栏关闭、Esc、遮罩点击):emit 通知父级,Workbench `content_json` 与 `plain_text` 零变更;Resume_JSON 仍保留在 store / localStorage。
    - 无 localStorage 数据时展示空状态:「暂无本地结构化简历」+ 引导按钮「从当前文档生成」。
    - 顶部红色横幅:`warnings.includes("fabrication_suspected")` 时持续展示「AI 可能编造内容,请逐项核对」,直到用户主动点关闭或对应字段全部 confirmed。
    - 视觉坚守 Dark Cyberpunk + Glassmorphism。
    - _Requirements: 1.2, 1.3, 6.4, 8.3, 10.1, 10.2, 11.4, 11.7_

  - [ ] 11.2 新建 `DraftReadonlyPanel.vue`
    - 直接复用 `KnowledgeBase.vue` 的 Tiptap 配置,`editable=false`,只读消费 props 中的 `content_json`。
    - 不通过任何接口写回 Workbench 的存储,不调用其保存 / 同步 / 自动保存路径,不修改 Workbench 内存对象引用所指向的字段值。
    - _Requirements: 10.1, 10.3_

  - [ ] 11.3 新建 `StructuredResumeForm.vue`
    - 按 `basics → education → skills → projects → experience → awards → certificates` 顺序渲染。
    - 标量字段控件携带 Field_Status 角标(右上角)+ 边框警示色:`missing` 红 / `needs_confirmation` 橙 / `inferred_from_text` 黄 / `confirmed` 灰;焦点 / 悬停时展示状态释义 tooltip(如「AI 未在草稿中找到该字段」「需要你确认」)。
    - 编辑触发 500ms 内通过 `resumeBuilderStore.patchField(path, value)` 写回(内部维护 Field_Status / missingFields)。
    - 数组型 Section 提供「+ 新增条目」「删除该条目」按钮,数组上限按 Requirement 3.3 / 3.4 强校验;删除条目通过 Toast 5 秒撤销。
    - 顶部嵌 `MissingQuestionsCard` + 底部嵌 `ConfirmResumeButton`。
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6, 3.3, 3.4_

  - [ ] 11.4 新建 `MissingQuestionsCard.vue`
    - 展示 `missing_questions` 列表,每条问题旁两个按钮「采纳」「忽略」。
    - 「采纳」:`scrollIntoView({behavior:'smooth'})` + 字段元素 `focus()`,**不修改** Resume_JSON。
    - 「忽略」:仅本前端会话内移除该条目,store 标记为 `dismissed`,不写 localStorage。
    - 列表条目 > 20 时启用 `overflow-y: auto` 内部滚动,不无限增高。
    - _Requirements: 6.4_

  - [ ] 11.5 新建 `ConfirmResumeButton.vue` 与 `ConfirmWithMissingModal.vue`(基于 `BaseModal.vue`)
    - 点击「确认结构化结果」:
      - 不含 missing / needs_confirmation → `meta.confirmedByUser = true`,Toast「已确认结构化结果」。
      - 含 missing / needs_confirmation → 弹 `ConfirmWithMissingModal`,列出缺失字段(≤10 全展示,>10 折叠展示前 10 条 + 「等其余 N 项」),提供「仍然确认」/「返回补全」二选一。
    - 「仍然确认」:`confirmedByUser = true`,Toast「已强制确认(仍含缺失字段)」。
    - 「返回补全」/ Esc / 关闭图标:关闭弹窗,Resume_JSON 与 `confirmedByUser` 零变更。
    - _Requirements: 6.7, 6.8, 6.9, 6.10_

  - [ ]* 11.6 Workspace 打开 / 关闭交互测试 — `frontend/tests/components/ResumeBuilderWorkspace.test.js`
    - 1 秒内打开 + 截断提示展示;关闭后 Workbench `content_json` 与 `plain_text` 零变更;无 localStorage 时展示空状态。
    - _Requirements: 1.2, 1.3, 11.4_

  - [ ]* 11.7 结构化表单与 missing_questions 卡片测试 — `frontend/tests/components/StructuredResumeForm.test.js`
    - 渲染顺序、Field_Status 视觉差异、tooltip 文案、数组上限校验、`MissingQuestionsCard` 采纳 / 忽略行为、>20 条滚动。
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 11.8 ConfirmResume 流程测试 — `frontend/tests/components/ConfirmResumeFlow.test.js`
    - 三种路径:无缺失直接 Toast、含缺失弹窗 + 「仍然确认」、含缺失弹窗 + 「返回补全」/ Esc / 关闭图标。
    - _Requirements: 6.7, 6.8, 6.9, 6.10_

  - [ ]* 11.9 Property 4 测试 — `frontend/tests/components/cancelZeroChange.pbt.test.js`
    - **Property 4: 取消操作零变更(取消按钮 / 关闭图标 / Esc / 点击遮罩任一路径后,Resume_JSON 与 confirmedByUser 深相等)**
    - **Validates: Requirements 1.6, 6.10, 7.10**

- [ ] 12. 模板与预览(`frontend/src/components/`)

  - [ ] 12.1 新建 `AtsSingleColumnTemplate.vue`
    - 单栏纯 `<section>` + `<h2>` + `<ul>` 布局,只读消费 Resume_JSON。
    - **禁止** multi-column / nested table / `<textarea>` / fixed header / `position: absolute|fixed`、`v-html` 字符串拼接 / `eval` / `new Function`。
    - 任一 Section `items` 为空 / 全字段空 时**整体隐藏**标题 + 分隔线 + 占位元素。
    - 字段值通过 DOM 文字节点输出,不使用 Canvas / SVG `<text>` / 图片;预览容器 `user-select: text` + `pointer-events: auto`。
    - _Requirements: 7.1, 7.2, 7.6, 7.7, 7.8, 8.1, 8.2, 8.5_

  - [ ] 12.2 新建 `TechTwoColumnTemplate.vue`
    - CSS Grid `grid-template-columns: 240px 1fr`;左侧 `basics + skills + certificates`,右侧 `projects + experience + education`。
    - 同一字段值不出现在两栏中;只读消费 Resume_JSON。
    - 同样禁止 `eval` / `v-html` 拼接 / `position: absolute|fixed`。
    - _Requirements: 7.1, 7.3, 7.6, 7.7, 7.8_

  - [ ] 12.3 新建 `ResumePreviewPanel.vue`
    - 通过 `<component :is="currentTemplate" :resume="resumeJson" />` 动态切换模板;切换仅写 `meta.templateId`。
    - 检测到非法字段变更 → store 回滚 + Toast「模板切换失败:检测到非法字段变更」。
    - 内容超出可视区时使用 `overflow-y: auto` 滚动或自动分页;**禁止** `overflow: hidden` 无替代滚动 / `display: none` / `visibility: hidden` / `text-overflow: ellipsis` 隐藏正文。
    - 任意字段编辑 / 模板切换 → 500ms 内更新(纯 reactive,无 HTTP)。
    - 首次进入 `meta.templateId` 缺失 / 越界 → 默认 `ats_single_column`。
    - _Requirements: 7.4, 7.5, 7.9, 7.10, 8.3, 8.4, 11.3_

  - [ ]* 12.4 Property 15 测试 — `frontend/tests/components/twoColumnNoDuplicate.pbt.test.js`
    - **Property 15: 双栏模板字段不跨栏重复(任一长度 ≥ 2 字符的非空原子字段值,不同时出现在 .left-column 与 .right-column)**
    - **Validates: Requirements 7.3**

  - [ ]* 12.5 Property 16 测试 — `frontend/tests/components/emptySectionHide.pbt.test.js`
    - **Property 16: 空 Section 隐藏(items.length===0 或全字段空 → 标题 / 分隔线 / 占位元素均不渲染)**
    - **Validates: Requirements 7.8, 8.5, 11.3**

  - [ ]* 12.6 Property 17 测试 — `frontend/tests/components/previewSelectableLocatable.pbt.test.js`
    - **Property 17: 预览可选可定位(所有非空原子字段值都能在 .preview textContent 子串定位;后代元素 user-select ≠ none、pointer-events ≠ none)**
    - **Validates: Requirements 8.1, 8.2, 8.5**

  - [ ]* 12.7 模板静态约束烟测 — `frontend/tests/components/templates.smoke.test.js`
    - grep `AtsSingleColumnTemplate.vue` / `TechTwoColumnTemplate.vue` / `ResumePreviewPanel.vue`,断言不含 `eval` / `new Function` / `v-html` / `position: absolute` / `position: fixed` / `<textarea>` / 嵌套 `<table><table>`。
    - _Requirements: 7.2, 7.7_

- [ ] 13. 导出工具栏与打印样式(`frontend/src/components/ExportToolbar.vue` 新增)

  - [ ] 13.1 新建 `ExportToolbar.vue` 与 `ExportRiskModal.vue`(基于 `BaseModal.vue`)
    - 「导出 PDF」/「导出 DOCX」按钮,`confirmedByUser===false` 时 disabled + tooltip「请先确认结构化结果」。
    - 点击时:
      - `confirmedByUser===false` → Toast「请先在表单底部点击『确认结构化结果』」展示 ≥ 3 秒,零变更。
      - 含 missing / needs_confirmation → 弹 `ExportRiskModal` 列出缺失(≤10 全展示,>10 折叠展示前 10 条 + 「等其余 N 项」),「忽略缺失继续导出」/「返回补全」二选一。
    - PDF 流:`document.body` 添加 `print-only-resume-preview` class → `window.print()` → `afterprint` 移除 class。
    - DOCX 流:调用 `resumeDocxBuilder.buildDocxBlob(resumeJson, templateId)` → `URL.createObjectURL` → `<a download>` → click;捕获 `ResumeDocxBuildError` → Toast「导出失败,请重试」+ 不输出任何文件 + Resume_JSON 零变更。
    - 文件名通过 `buildExportFilename(basics, ext)` 生成。
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 11.1_

  - [ ] 13.2 新建打印样式
    - 在 `ResumePreviewPanel.vue` 或 `frontend/src/style.css` 中追加 `@media print` 规则:`print-only-resume-preview` 激活时隐藏除 `.preview` 容器之外的所有元素;预览正文文字保持为可被 `pdftotext` / PyMuPDF 抽取的文本流。
    - 禁止 Canvas / SVG 路径化文本。
    - _Requirements: 9.2, 8.4_

  - [ ]* 13.3 Property 19 测试 — `frontend/tests/components/exportStateMachine.pbt.test.js`
    - **Property 19: 导出守护状态机(confirmedByUser=false → 不调用导出函数 + Toast ≥3s + 零变更;含 missing → 风险弹窗,只有「忽略缺失继续导出」分支才调用导出函数;导出失败 → 不输出文件 + 零变更 + Toast)**
    - **Validates: Requirements 9.5, 9.6, 9.8, 11.1**

  - [ ]* 13.4 ExportToolbar 例子级测试 — `frontend/tests/components/ExportToolbar.test.js`
    - 覆盖 9.1 按钮渲染、9.5 disabled 与 tooltip、9.6 风险弹窗、9.8 DOCX 异常、11.1 三项守护(零变更 + Toast 时长 + 提示文案)。
    - _Requirements: 9.1, 9.5, 9.6, 9.8, 11.1_

- [ ] 14. 接入 `/files` 工作台(扩展 `frontend/src/KnowledgeBase.vue`)

  - [ ] 14.1 添加「生成简历预览」按钮 + 挂载 `ResumeBuilderWorkspace`
    - 工具栏新增按钮,启用条件 `canOpenWorkspace(plainText) === true`(去除全部 Unicode 空白后剩余字符 ≥ 10);disabled 时 tooltip「请先在文档中填写简历草稿」,点击不触发任何打开行为。
    - 点击时若 `resumeBuilderStore.isDirty===true` → 弹「确认覆盖 / 取消」二选一确认框(基于 `BaseModal`):「确认覆盖」→ `reextractFromDraft({document_id, plain_text, content_json, provider_id})`;「取消」/ Esc / 关闭图标 → 状态零变更。
    - 点击成功:1 秒内挂载 `ResumeBuilderWorkspace` 全屏 Modal,**不新建顶级路由**,关闭后回到 Workbench 视图,Tiptap `content_json` 保持原值。
    - 透传字段(`document_id` / `plain_text` / `content_json`)缺失或不可序列化 → 不打开 Modal + Toast「文档数据读取失败:<字段名>」+ Workbench 零变更。
    - `plain_text.length > 50000` → 截断到 50000 字符再透传给 Workspace。
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 10.1, 10.2_

  - [ ]* 14.2 工具栏按钮例子级测试 — `frontend/tests/components/FilesToolbarButton.test.js`
    - 覆盖 1.1 按钮存在性、1.4 disabled 与 tooltip 文案、1.5 isDirty 二次确认、1.7 透传失败 Toast。
    - _Requirements: 1.1, 1.4, 1.5, 1.7_

  - [ ]* 14.3 Property 2 测试 — `frontend/tests/integration/workspaceDoesNotMutateWorkbench.pbt.test.js`
    - **Property 2: Workspace 不破坏 Workbench(打开 → 任意 patchField/switchTemplate 操作序列 → 关闭后,Workbench content_json 与 plain_text 严格深相等)**
    - **Validates: Requirements 1.3, 10.1, 10.2_**

- [ ] 15. 最终检查点
  - 后端运行 `pytest tests/ -q`,前端运行 `npm run test`(等价 `vitest --run`),确保所有 PBT 与例子级测试通过。
  - 静态扫描通过:Router 不直接 `import httpx`、Prompt 全在 `Service/Agents/prompts/`、前端客户端只命中 `/api/document/extract-resume`、模板组件无 `eval` / `v-html` 拼接 / `position: absolute|fixed` / `<textarea>`。
  - **不允许**运行 `vue-tsc` / `tsc` / `vite build` / `npm run build`。
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 标记 `*` 的子任务为可选测试(property test / 例子级 unit test / 静态扫描烟测),可在 MVP 中跳过,但属于交付完整度验收口径。
- 顶级任务 1-15 均不带 `*`,实现 sub-task(无 `*`)必须实现;property test sub-task 推荐随实现并行落地以提早暴露反例。
- Property 测试覆盖矩阵:Property 1=8.5、Property 2=14.3、Property 3=8.6、Property 4=11.9、Property 5=2.6、Property 6=2.5、Property 7=2.2、Property 8=5.3、Property 9=2.3、Property 10=2.4、Property 11=5.2、Property 12=8.2、Property 13=9.2、Property 14=8.3、Property 15=12.4、Property 16=12.5、Property 17=12.6、Property 18=9.4、Property 19=13.3、Property 20=8.8、Property 21=9.3。21 条 Properties 全覆盖。
- 所有 property test 文件顶部注释必须包含 `Feature: resume-preview-builder, Property X: <text>` 标签,与 design.md 对齐。
- 后端 Hypothesis 默认 100 次迭代,关键 property `@settings(max_examples=200)`;前端 fast-check 默认 100 次,关键 property `numRuns: 200`。
- 所有用户可见文案使用简体中文;弹窗基于 `BaseModal.vue`,Toast 基于 `Toast.vue`,加载态基于 `StreamingLoader.vue`;视觉坚守 Dark Cyberpunk + Glassmorphism。
- `extract-resume` 接口 HTTP 始终返回 200(除 Pydantic 422 与 Router 兜底 500);失败语义通过 `success=false` + `warnings` 表达,`resume_json` 永不为 null,前端始终能渲染骨架。
- v1 不接 RAG / ChatDock / 历史 / 简历诊断 / 面试 / 职业规划接口,前端客户端硬性绑定 `/api/document/extract-resume` 单一端点。
- v1 不在 SQLite / PostgreSQL 中新建任何表,Resume_JSON 仅在前端 `localStorage`(`resume_builder:` 命名空间)与内存中维护。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1", "8.1", "8.4", "8.7", "8.9", "13.2"] },
    { "id": 1, "tasks": ["1.2", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "4.1", "8.2", "8.3", "8.5", "8.6", "8.8", "8.10", "9.1", "10.1", "11.2", "12.1", "12.2"] },
    { "id": 2, "tasks": ["4.2", "5.1", "9.2", "9.3", "9.4", "9.5", "10.2", "11.3", "11.4", "11.5", "12.3", "12.7", "13.1"] },
    { "id": 3, "tasks": ["5.2", "5.3", "5.4", "6.1", "11.1", "11.7", "11.8", "12.4", "12.5", "12.6", "13.3", "13.4"] },
    { "id": 4, "tasks": ["6.2", "6.3", "11.6", "11.9", "14.1"] },
    { "id": 5, "tasks": ["14.2", "14.3"] }
  ]
}
```
