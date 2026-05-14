# Requirements Document

## Introduction

本文档定义了"Profile-RAG 解耦"重构的功能需求。该重构将系统中"轻资产 (Profile)"与"重资产 (RAG)"彻底分离：Dashboard 侧边栏"全局资产"卡片仅管理用户个人信息（通过 SetupModal），知识库文件管理独立在 `/files` 路由页面完成；后端 OCR 调用从 HTTP 自调用改为直接 SDK 导入，消除死锁风险。

## Glossary

- **Dashboard**: 系统主工作区页面 (`Dashboard.vue`)，包含侧边栏导航和主内容区
- **SetupModal**: 轻资产管理弹窗组件 (`SetupModal.vue`)，负责收集用户姓名和简历文本
- **KnowledgeBase_Page**: 重资产管理页面 (`KnowledgeBase.vue`)，路由为 `/files`，负责文件上传和向量化索引
- **RAG_Service**: 后端知识库服务 (`rag_service.py`)，负责文件解析、文本分块和向量检索
- **OCR_SDK**: 后端 OCR 识别模块 (`Service/Utils/ocr_sdk.py`)，提供 `recognize_image_text()` 函数
- **Profile**: 轻资产数据，包括用户姓名和简历文本，存储在浏览器 localStorage 中
- **RAG_Asset**: 重资产数据，包括上传至后端的知识库文件及其向量索引
- **GlobalResumeStatus**: Dashboard 中的响应式状态变量，指示用户 Profile 是否已就绪
- **Ghost_Interceptor**: 残留在代码中的硬编码文件格式校验字符串（"仅支持 PDF、TXT 和 MD 文件"）

## Requirements

### Requirement 1: 全局资产卡片触发 SetupModal

**User Story:** 作为用户，我希望点击 Dashboard 侧边栏的"全局资产"卡片时弹出个人信息编辑弹窗，以便我可以快速完善个人资料而不会误触知识库上传。

#### Acceptance Criteria

1. WHEN 用户点击 Dashboard 侧边栏"全局资产"区域内的简历状态卡片, THE Dashboard SHALL 将 `showSetupModal` 设为 `true` 并渲染 SetupModal 弹窗，弹窗须在 300ms 内完成显示
2. WHEN 用户点击"全局资产"卡片, THE Dashboard SHALL NOT 发起任何指向 `/api/knowledge/upload` 的 HTTP 请求，也不得触发文件选择对话框（`<input type="file">`）或拖拽上传逻辑
3. WHEN SetupModal 弹窗已显示, THE SetupModal SHALL 预填充 localStorage 中已有的 `candidate_name` 和 `resume_text` 值到对应输入框，并允许用户修改姓名（最大 50 字符）和简历文本（最少 20 字符）
4. WHEN 用户点击 SetupModal 的关闭按钮或遮罩层, THE Dashboard SHALL 将 `showSetupModal` 设为 `false` 并移除 SetupModal 弹窗，不保存未提交的修改
5. WHEN 用户通过任意交互方式（包括但不限于点击"完成设置"按钮、键盘快捷键提交、文件解析自动完成后确认）触发提交操作且姓名和简历均通过验证, THE SetupModal SHALL 将姓名和简历文本写入 localStorage 并触发 `complete` 事件通知 Dashboard 关闭弹窗

### Requirement 2: SetupModal 数据仅存储在前端 localStorage

**User Story:** 作为用户，我希望在 SetupModal 中提交的个人信息仅保存在浏览器本地，以便我的隐私数据不会被上传到知识库后端。

#### Acceptance Criteria

1. WHEN 用户在 SetupModal 中提交表单, THE SetupModal SHALL 将 `candidate_name` 写入 localStorage
2. WHEN 用户在 SetupModal 中提交表单, THE SetupModal SHALL 将 `resume_text` 写入 localStorage
3. WHEN 用户在 SetupModal 中提交表单, THE SetupModal SHALL NOT 发起任何指向 `/api/knowledge` 路径的 HTTP 请求
4. WHEN 用户提交的姓名为空或去除首尾空白后为空或超过 50 字符, THE SetupModal SHALL 阻止提交并显示验证错误提示
5. WHEN 用户提交的简历文本去除首尾空白后少于 20 字符, THE SetupModal SHALL 阻止提交并显示验证错误提示
6. WHEN 用户提交的简历文本超过 10000 字符, THE SetupModal SHALL 阻止提交并显示验证错误提示

### Requirement 3: SetupModal 完成后更新 Dashboard 状态

**User Story:** 作为用户，我希望完善个人信息后侧边栏状态指示器立即更新为"已就绪"，以便我能直观确认信息已保存成功。

#### Acceptance Criteria

1. WHEN SetupModal 触发 `complete` 事件, THE Dashboard SHALL 在同一事件循环内将 `globalResumeStatus` 设为 `'ready'`，且侧边栏状态指示器从 `'missing'` 状态切换为 `'ready'` 状态的视觉变化在 100ms 内对用户可见
2. WHEN SetupModal 触发 `complete` 事件, THE Dashboard SHALL 将 `showSetupModal` 设为 `false`，使 SetupModal 弹窗从 DOM 中移除（不再渲染）
3. WHEN SetupModal 触发 `complete` 事件, THE Dashboard SHALL 从 localStorage 读取 `candidate_name` 键的值并将其赋给 `userName` 响应式变量，使侧边栏用户名显示区域的文本内容与 localStorage 中存储的值一致
4. WHEN Dashboard 页面首次挂载, THE Dashboard SHALL 读取 localStorage 中的 `resume_text` 键，若值非空则将 `globalResumeStatus` 初始化为 `'ready'`，否则初始化为 `'missing'`

### Requirement 4: globalResumeStatus 与 localStorage 保持同步

**User Story:** 作为用户，我希望 Dashboard 的状态指示器始终准确反映我的个人信息是否已填写，以便我不会看到过时或错误的状态。

#### Acceptance Criteria

1. WHILE localStorage 中存在 `resume_text` 且其去除首尾空白后长度大于 0, THE Dashboard SHALL 将 `globalResumeStatus` 显示为 `'ready'`
2. WHILE localStorage 中不存在 `resume_text` 键，或其值去除首尾空白后长度等于 0, THE Dashboard SHALL 将 `globalResumeStatus` 显示为 `'missing'`
3. WHEN Dashboard 组件挂载时, THE Dashboard SHALL 从 localStorage 读取 `resume_text` 键的值，若该值去除首尾空白后长度大于 0 则将 `globalResumeStatus` 初始化为 `'ready'`，否则初始化为 `'missing'`
4. WHEN 其他浏览器标签页修改了 localStorage 中的 `resume_text` 键（触发 `storage` 事件）, THE Dashboard SHALL 在 100ms 内将 `globalResumeStatus` 更新为与新值一致的状态（非空为 `'ready'`，空或删除为 `'missing'`）
5. WHEN 用户在当前 Dashboard 页面内通过确认操作写入 `resume_text` 到 localStorage, THE Dashboard SHALL 在同一事件循环内将 `globalResumeStatus` 同步更新为 `'ready'`

### Requirement 5: 知识库文件管理独立在 /files 路由

**User Story:** 作为用户，我希望通过菜单导航到独立的文件管理页面来上传知识库文件，以便文件上传流程与个人信息管理完全分离。

#### Acceptance Criteria

1. WHEN 用户点击 Dashboard 菜单中的"文件管理"项, THE Dashboard SHALL 通过 `router.push('/files')` 导航至 KnowledgeBase_Page
2. THE Dashboard 菜单 SHALL 有且仅有一个指向 `/files` 路由的菜单项用于知识库管理
3. WHEN 用户在 KnowledgeBase_Page 选择或拖拽文件, THE KnowledgeBase_Page SHALL 仅接受 PDF、DOCX、TXT、JPG、PNG、WEBP 格式且单文件不超过 10 MB 的文件，并调用 `POST /api/knowledge/upload` 将文件发送至后端
4. IF 文件上传请求返回非 2xx 响应或网络超时（30 秒无响应）, THEN THE KnowledgeBase_Page SHALL 在页面底部显示错误提示信息，说明失败原因，且不将该文件标记为已完成状态
5. WHEN 文件上传成功（后端返回 `success: true` 及 `knowledge_id`）, THE KnowledgeBase_Page SHALL 在文件资产列表中将该文件状态更新为"已完成"，并按上传时间倒序排列展示

### Requirement 6: 后端 OCR 直接调用 SDK 消除死锁

**User Story:** 作为开发者，我希望后端图片 OCR 处理直接调用 SDK 函数而非发起 HTTP 自调用，以便消除单线程事件循环下的死锁问题。

#### Acceptance Criteria

1. WHEN RAG_Service 处理图片文件（.jpg、.jpeg、.png、.webp）时, THE RAG_Service SHALL 通过直接 import 调用 `ocr_sdk.recognize_image_text()` 提取文本
2. WHEN RAG_Service 处理图片文件时, THE RAG_Service SHALL NOT 通过 httpx 或任何 HTTP 客户端向 `/api/ocr/recognize` 或任何本机 HTTP 端点发起请求
3. IF `recognize_image_text()` 返回空字符串或返回值包含"图片解析失败", THEN THE RAG_Service SHALL 抛出 HTTP 400 错误并附带说明 OCR 识别未能提取有效文本的错误信息
4. WHEN RAG_Service 调用 `recognize_image_text()` 时, THE RAG_Service SHALL 将图片原始字节编码为 base64 字符串并添加 `data:image/<格式>;base64,` 前缀后传入
5. WHEN RAG_Service 调用 `recognize_image_text()` 时, THE RAG_Service SHALL 在 60 秒内完成 OCR 处理，IF 超时, THEN THE RAG_Service SHALL 抛出 HTTP 400 错误并附带说明 OCR 处理超时的错误信息

### Requirement 7: 清除幽灵拦截器

**User Story:** 作为开发者，我希望移除前端代码中残留的硬编码文件格式校验字符串，以便消除与当前架构不一致的遗留逻辑。

#### Acceptance Criteria

1. THE 前端源码 (`frontend/src/**/*.vue` 和 `frontend/src/**/*.js`) SHALL NOT 包含字符串 "仅支持 PDF、TXT 和 MD 文件"
2. THE 前端源码 (`frontend/src/**/*.vue` 和 `frontend/src/**/*.js`) SHALL NOT 包含任何将允许上传格式硬编码为仅 PDF、TXT、MD 子集的条件判断逻辑（即绕过统一格式白名单，独立执行格式拦截的代码）
3. WHEN 在前端源码中发现包含已废弃的格式限制字符串（如 "仅支持 PDF、TXT 和 MD 文件" 或其变体）的条件分支或弹窗调用, THE 重构过程 SHALL 移除该条件分支或弹窗调用的完整代码块，且不影响同一函数中其他无关逻辑的正常执行
4. IF 移除幽灵拦截器代码后, THEN THE 前端源码 SHALL 通过 `npm run build` 构建且零错误完成

### Requirement 8: SetupModal 前端文件解析

**User Story:** 作为用户，我希望在 SetupModal 中上传简历文件时由浏览器本地解析内容，以便无需依赖后端即可快速提取简历文本。

#### Acceptance Criteria

1. WHEN 用户在 SetupModal 中上传 PDF 文件, THE SetupModal SHALL 使用 pdfjs-dist 在浏览器端解析并提取文本
2. WHEN 用户在 SetupModal 中上传 DOCX 或 DOC 文件, THE SetupModal SHALL 使用 mammoth 在浏览器端解析并提取文本
3. WHEN 用户在 SetupModal 中上传 TXT 文件, THE SetupModal SHALL 使用 FileReader 以 UTF-8 编码读取文件内容作为简历文本
4. WHEN 文件解析完成且提取文本非空（去除空白后长度大于 0）, THE SetupModal SHALL 将提取的文本填充到简历文本输入区域，并显示文件名及解析成功状态
5. IF 文件解析过程中发生错误或提取文本为空, THEN THE SetupModal SHALL 显示错误提示信息持续 4 秒后自动消失，简历文本输入区域保持可编辑状态以允许用户手动粘贴文本
6. IF 用户上传的文件大小超过 20MB, THEN THE SetupModal SHALL 拒绝该文件并显示文件大小超限的错误提示
7. IF 用户上传的文件格式不在支持列表（PDF、DOC、DOCX、TXT、JPG、JPEG、PNG、WEBP）中, THEN THE SetupModal SHALL 拒绝该文件并显示不支持该格式的错误提示
8. WHEN 用户在 SetupModal 中上传图片文件（JPG、JPEG、PNG、WEBP）, THE SetupModal SHALL 将图片发送至后端 OCR 接口进行文字识别并提取文本

### Requirement 9: Dashboard 移除旧版全局资产上传逻辑

**User Story:** 作为开发者，我希望 Dashboard 中与全局资产卡片相关的文件上传代码被彻底移除，以便代码库中不存在废弃的上传逻辑。

#### Acceptance Criteria

1. THE Dashboard SHALL NOT 在 `<script setup>` 中定义名为 `handleGlobalFileDrop` 的函数
2. THE Dashboard SHALL NOT 在 `<script setup>` 中定义名为 `handleGlobalFileSelect` 的函数
3. THE Dashboard SHALL NOT 在 `<template>` 中包含通过 `ref="globalFileInput"` 引用且绑定 `@change="handleGlobalFileSelect"` 的 `<input type="file">` 隐藏元素
4. THE Dashboard SHALL NOT 在全局资产卡片（侧边栏中标题为"全局资产"的区域）的容器元素上绑定 `@dragover` 或 `@drop` 事件监听器
5. THE Dashboard SHALL NOT 在 `<script setup>` 中定义名为 `isGlobalDragging` 的响应式变量
6. THE Dashboard SHALL NOT 在 `<script setup>` 中定义名为 `processGlobalResume` 的函数
