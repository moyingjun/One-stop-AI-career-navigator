# Implementation Plan: 全局文件格式解禁 & 知识库资产舱搭建

## Overview
实现全局文件格式常量模块、统一所有上传组件格式限制、创建知识库 Pinia Store、重构知识库页面（含拖拽上传和文件列表）、实现 OCR 解析逻辑。

## Tasks

- [x] 1. 创建全局文件格式常量模块
  - [x] 1.1 创建 `frontend/src/utils/fileConstants.js` 文件
  - [x] 1.2 导出 `ACCEPTED_EXTENSIONS` 常量，值为 `.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp`
  - [x] 1.3 导出 `ACCEPTED_MIME_TYPES` 数组，包含对应的 8 种 MIME 类型
  - [x] 1.4 导出 `FILE_TYPE_MAP` 对象，为每种扩展名映射 `{ label, icon, color }`
  - [x] 1.5 导出 `MAX_FILE_SIZE` 常量 (20MB)
  - [x] 1.6 导出 `getFileType(filename)` 函数，返回文件类型信息
  - [x] 1.7 导出 `validateFile(file)` 函数，校验扩展名和文件大小

- [x] 2. 统一 ResumeDiagnosis.vue 的文件格式
  - [x] 2.1 在 `ResumeDiagnosis.vue` 中导入 `ACCEPTED_EXTENSIONS` 和 `validateFile`
  - [x] 2.2 将 `<input type="file" accept=".txt,.pdf,.docx,image/*">` 替换为 `:accept="ACCEPTED_EXTENSIONS"`
  - [x] 2.3 更新格式提示文案为"支持文档与图片格式上传（PDF/Word/TXT/JPG/PNG/WEBP）"
  - [x] 2.4 在 `processFile` 中使用 `validateFile` 进行格式校验

- [x] 3. 创建 knowledgeBaseStore (Pinia)
  - [x] 3.1 创建 `frontend/src/stores/knowledgeBaseStore.js` 文件
  - [x] 3.2 定义 `state.files` 数组（存储 FileItem 对象）
  - [x] 3.3 实现 `addFile(fileMetadata)` action，将新文件插入数组头部
  - [x] 3.4 实现 `updateFileStatus(id, status, extractedText, errorMessage)` action
  - [x] 3.5 实现 `removeFile(id)` action
  - [x] 3.6 实现 `fileCount` / `parsingFiles` / `completedFiles` getters

- [x] 4. 重构 KnowledgeBase.vue 页面骨架
  - [x] 4.1 重写 `FilesPlaceholder.vue` 内容（保留文件名或重命名为 KnowledgeBase.vue）
  - [x] 4.2 页面使用暗黑背景 (#020205) + 紫/青 blur 背景层
  - [x] 4.3 使用 `CyberGlassCard` 组件包裹上传区和列表区
  - [x] 4.4 实现赛博朋克风格的 Dropzone（虚线边框 + hover 发光 + 拖拽激活态）
  - [x] 4.5 Dropzone 支持点击触发文件选择对话框，`accept` 使用 `ACCEPTED_EXTENSIONS`
  - [x] 4.6 Dropzone 支持拖拽文件进入（dragover/dragleave/drop 事件处理）
  - [x] 4.7 页面顶部包含返回按钮，点击导航至 `/dashboard`
  - [x] 4.8 响应式布局：桌面端左右分栏，移动端上下堆叠
  - [x] 4.9 如果重命名了文件，更新 `router/index.js` 中的路由导入

- [x] 5. 实现文件资产列表 UI
  - [x] 5.1 文件列表从 `knowledgeBaseStore.files` 读取数据
  - [x] 5.2 每个文件条目显示：文件名、类型图标（来自 `getFileType`）、文件大小
  - [x] 5.3 解析中状态：显示 Loader2 spinner + "解析中" 文字（紫色）
  - [x] 5.4 已完成状态：显示绿色圆点 + "已完成" 文字
  - [x] 5.5 失败状态：显示红色标识 + 错误信息
  - [x] 5.6 列表按 `createdAt` 降序排列（最新在前）
  - [x] 5.7 每个条目包含删除按钮，点击调用 `store.removeFile(id)`
  - [x] 5.8 列表为空时显示空状态占位提示

- [x] 6. 实现文件上传 & OCR 解析逻辑
  - [x] 6.1 实现 `handleFileUpload(file)` 函数，调用 `validateFile` 校验后调用 `parseFile`
  - [x] 6.2 上传前创建 FileItem 并通过 `store.addFile` 加入列表（status: 'parsing'）
  - [x] 6.3 解析成功后调用 `store.updateFileStatus(id, 'completed', text)`
  - [x] 6.4 解析失败后调用 `store.updateFileStatus(id, 'failed', '', error.message)`
  - [x] 6.5 `handleFileDrop` 支持多文件拖拽，逐个调用 `handleFileUpload`
  - [x] 6.6 `handleFileSelect` 处理点击选择的文件
  - [x] 6.7 不合法文件显示错误 toast 提示（3 秒后自动消失）

- [x] 7. 扫描其他上传组件并统一格式
  - [x] 7.1 扫描 `src/` 目录下所有包含 `<input type="file"` 或文件上传逻辑的组件
  - [x] 7.2 将所有硬编码的 accept 属性替换为 `:accept="ACCEPTED_EXTENSIONS"`
  - [x] 7.3 确保所有上传组件的格式提示文案统一更新
  - [x] 7.4 验证所有上传入口均支持图片格式（JPG/PNG/WEBP）

## Task Dependency Graph
```
1 --> 2
1 --> 3
1,3 --> 4
1,3,4 --> 5
1,3,4 --> 6
1,2 --> 7
```

## Notes
- Task 1 是基础模块，所有其他任务依赖它
- Task 3 (Pinia Store) 需要在 Task 4/5/6 之前完成
- Task 5 和 Task 6 可以并行执行（都依赖 Task 4）
- Task 7 依赖 Task 1 和 Task 2 完成后再扫描统一
