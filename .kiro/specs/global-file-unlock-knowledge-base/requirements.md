# Requirements: 全局文件格式解禁 & 知识库资产舱搭建

## Requirement 1: 全局文件格式常量模块

### Acceptance Criteria

1.1 Given 前端项目中存在 `src/utils/fileConstants.js` 文件, When 任何上传组件需要文件格式白名单, Then 该组件必须从 `fileConstants.js` 导入 `ACCEPTED_EXTENSIONS` 常量而非硬编码

1.2 Given `ACCEPTED_EXTENSIONS` 常量已定义, When 查看其值, Then 必须包含 `.pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .webp` 全部 8 种格式

1.3 Given 用户选择了一个合法格式的文件（如 .png）, When 调用 `validateFile(file)`, Then 返回 `{ valid: true, error: null }`

1.4 Given 用户选择了一个不在白名单中的文件（如 .exe）, When 调用 `validateFile(file)`, Then 返回 `{ valid: false, error: '不支持的文件格式: .exe' }`

1.5 Given 用户选择了一个超过 20MB 的文件, When 调用 `validateFile(file)`, Then 返回 `{ valid: false, error: '文件大小超过限制 (最大 20MB)' }`

1.6 Given `FILE_TYPE_MAP` 已定义, When 调用 `getFileType('resume.pdf')`, Then 返回包含 `label`, `icon`, `color` 三个字段的对象

## Requirement 2: 全局上传组件格式统一

### Acceptance Criteria

2.1 Given `ResumeDiagnosis.vue` 中的文件上传 input, When 检查其 `accept` 属性, Then 其值必须来自 `ACCEPTED_EXTENSIONS` 常量（非硬编码字符串）

2.2 Given 用户在简历诊断页面上传一张 JPG 图片, When 文件被选中, Then 系统接受该文件并调用 OCR 解析（不再被格式限制拦截）

2.3 Given 任何包含文件上传功能的组件, When 显示格式提示文案, Then 必须明确告知用户"支持文档与图片格式上传（PDF/Word/TXT/JPG/PNG/WEBP）"

## Requirement 3: 知识库资产舱页面重构

### Acceptance Criteria

3.1 Given 用户访问 `/files` 路由, When 页面加载完成, Then 显示重构后的知识库资产管理舱（非 FilesPlaceholder 占位内容）

3.2 Given 知识库页面已加载, When 查看页面布局, Then 包含一个拖拽上传区域（Dropzone）和一个文件资产列表区域，均使用 `CyberGlassCard` 组件包裹

3.3 Given 拖拽上传区域已渲染, When 用户将鼠标悬停在 Dropzone 上, Then 显示赛博朋克风格的虚线边框发光效果（border-color 和 glow 变化）

3.4 Given 拖拽上传区域已渲染, When 用户将文件拖入 Dropzone, Then 区域视觉状态变为激活态（背景色变化 + 边框高亮）

3.5 Given 拖拽上传区域已渲染, When 用户点击 Dropzone, Then 触发文件选择对话框，允许选择白名单内的文件格式

3.6 Given 页面顶部导航区域, When 查看返回按钮, Then 存在一个可点击的返回按钮，点击后导航至 `/dashboard`

## Requirement 4: 文件资产列表展示

### Acceptance Criteria

4.1 Given 用户已上传至少一个文件, When 查看文件列表, Then 每个文件条目显示：文件名、文件类型图标、文件大小、OCR 解析状态

4.2 Given 一个文件正在 OCR 解析中, When 查看其列表条目, Then 状态显示为"解析中"并带有加载动画（spinner）

4.3 Given 一个文件 OCR 解析已完成, When 查看其列表条目, Then 状态显示为"已完成"并带有绿色成功标识

4.4 Given 一个文件 OCR 解析失败, When 查看其列表条目, Then 状态显示为"失败"并带有红色错误标识和错误信息

4.5 Given 文件列表中有多个文件, When 查看列表排序, Then 最新上传的文件排在最前面（按 createdAt 降序）

4.6 Given 文件列表中有一个文件, When 用户点击删除按钮, Then 该文件从列表中移除

## Requirement 5: Pinia Store 状态管理

### Acceptance Criteria

5.1 Given `knowledgeBaseStore` 已创建, When 调用 `addFile(fileMetadata)`, Then `state.files` 数组长度增加 1 且新条目位于数组头部

5.2 Given Store 中存在一个 id 为 'abc' 的文件, When 调用 `updateFileStatus('abc', 'completed', '解析文本')`, Then 该文件的 status 变为 'completed' 且 extractedText 变为 '解析文本'

5.3 Given Store 中存在一个 id 为 'abc' 的文件, When 调用 `removeFile('abc')`, Then `state.files` 中不再包含该条目

5.4 Given Store 中有 3 个文件（1 个 parsing, 2 个 completed）, When 访问 `parsingFiles` getter, Then 返回长度为 1 的数组

## Requirement 6: OCR 接口对接

### Acceptance Criteria

6.1 Given 用户上传了一张图片文件, When `handleFileUpload` 被调用, Then 使用 `ocrHelper.js` 的 `parseFile` 函数进行解析，该函数内部通过 `FormData` 或 base64 方式调用后端 `/api/ocr/recognize`

6.2 Given OCR 解析成功返回文本, When 回调执行, Then Store 中对应文件的 status 更新为 'completed' 且 extractedText 存储解析结果

6.3 Given OCR 解析失败（网络错误或后端 500）, When 错误被捕获, Then Store 中对应文件的 status 更新为 'failed' 且 errorMessage 存储错误描述

6.4 Given 用户上传了一个纯文本 PDF, When `parseFile` 被调用, Then 使用 pdfjs 本地解析文本（不调用后端 OCR 接口）

6.5 Given 用户上传了一个扫描件 PDF（文字层 < 50 字符）, When `parseFile` 被调用, Then 自动降级为逐页渲染 + 调用后端 OCR 接口

## Requirement 7: UI 风格一致性

### Acceptance Criteria

7.1 Given 知识库页面已加载, When 查看整体视觉风格, Then 页面背景为暗黑色（#020205 或类似深色），与全站风格一致

7.2 Given 知识库页面已加载, When 查看卡片容器, Then 使用 `CyberGlassCard` 组件，具有毛玻璃效果和流光边框动画

7.3 Given 知识库页面已加载, When 查看配色方案, Then 主色调使用 cyan/purple 渐变，与全站赛博朋克主题一致

7.4 Given 用户使用移动设备访问, When 查看页面布局, Then 页面响应式适配，上传区和列表区垂直堆叠
