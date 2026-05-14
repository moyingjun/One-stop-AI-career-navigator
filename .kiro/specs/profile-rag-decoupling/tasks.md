# Implementation Plan: Profile-RAG Decoupling (核心数据架构解耦)

## Overview

本实现计划将系统中"轻资产 (Profile)"与"重资产 (RAG)"彻底分离。重构涉及前端 Dashboard 侧边栏交互改造、SetupModal 数据流修正、后端 OCR 死锁修复、幽灵拦截器清除，以及 globalResumeStatus 状态同步机制建立。

## Tasks

- [x] 1. 后端 OCR 死锁修复
  - [x] 1.1 重构 rag_service.py 图片处理函数，替换 httpx 自调用为直接 SDK import
    - 在 `Service/rag_service.py` 中找到 `_extract_text_from_image()` 函数
    - 移除 `httpx.post("/api/ocr/recognize")` 调用
    - 添加 `from Service.Utils.ocr_sdk import recognize_image_text`
    - 实现直接调用：将图片 bytes 编码为 base64，添加 `data:image/<格式>;base64,` 前缀，传入 `recognize_image_text()`
    - 验证返回值：若为空或包含"图片解析失败"则抛出 `HTTPException(status_code=400)`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 1.2 编写 rag_service OCR 直接调用的单元测试
    - 使用 pytest + unittest.mock 模拟 `recognize_image_text()`
    - 验证正常图片返回文本、空结果抛出 400、不发起 HTTP 请求
    - **Property 5: 后端 OCR 无 HTTP 自调用**
    - **Property 6: OCR 失败正确抛出异常**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 2. Dashboard 侧边栏全局资产卡片重构
  - [x] 2.1 移除 Dashboard.vue 中旧版全局资产上传逻辑
    - 删除 `handleGlobalFileDrop` 函数
    - 删除 `handleGlobalFileSelect` 函数
    - 删除 `processGlobalResume` 函数
    - 删除 `isGlobalDragging` 响应式变量
    - 删除 `<input ref="globalFileInput">` 隐藏文件输入元素
    - 删除全局资产卡片容器上的 `@dragover`、`@drop` 事件绑定
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 2.2 实现全局资产卡片点击弹出 SetupModal
    - 导入 `SetupModal` 组件：`import SetupModal from '@/components/SetupModal.vue'`
    - 声明 `const showSetupModal = ref(false)`
    - 全局资产卡片 `@click="showSetupModal = true"`
    - 在 template 中挂载 `<SetupModal v-if="showSetupModal" @close="showSetupModal = false" @complete="handleSetupComplete" />`
    - 实现 `handleSetupComplete()`：关闭弹窗、设置 `globalResumeStatus = 'ready'`、从 localStorage 读取 `candidate_name` 更新 `userName`
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 3.1, 3.2, 3.3_

  - [x] 2.3 实现 globalResumeStatus 与 localStorage 同步机制
    - 在 `onMounted` 中读取 localStorage `resume_text`，非空则设 `globalResumeStatus = 'ready'`，否则 `'missing'`
    - 添加 `window.addEventListener('storage', handler)` 监听跨标签页变化
    - storage handler 中检测 `resume_text` key 变化，100ms 内更新 `globalResumeStatus`
    - 在 `onUnmounted` 中移除 storage 事件监听
    - _Requirements: 3.4, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 2.4 编写 Dashboard 全局资产卡片交互的单元测试
    - 验证点击卡片后 `showSetupModal` 为 `true`
    - 验证不触发任何 HTTP 请求
    - 验证 `handleSetupComplete` 正确更新状态
    - **Property 1: Profile 与 RAG 完全隔离**
    - **Property 4: globalResumeStatus 双向同步**
    - **Validates: Requirements 1.1, 1.2, 4.1, 4.2, 4.3**

- [x] 3. Checkpoint - 确保后端 OCR 和 Dashboard 重构正常
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. SetupModal 数据流与验证完善
  - [x] 4.1 确保 SetupModal 表单验证逻辑完整
    - 验证 `candidate_name`：非空、去除空白后非空、≤50 字符
    - 验证 `resume_text`：去除空白后 ≥20 字符、≤10000 字符
    - 验证失败时在对应字段下方显示红色错误提示，阻止提交
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 4.2 确保 SetupModal 提交仅写入 localStorage
    - `handleSubmit()` 中写入 `localStorage.setItem('candidate_name', name)`
    - 写入 `localStorage.setItem('resume_text', text)`
    - 确认不存在任何指向 `/api/knowledge` 的请求调用
    - 提交成功后 `emit('complete')`
    - _Requirements: 2.1, 2.2, 2.3, 1.5_

  - [x] 4.3 实现 SetupModal 预填充已有数据
    - 组件挂载时从 localStorage 读取 `candidate_name` 和 `resume_text`
    - 将已有值填充到对应输入框
    - 允许用户修改已有数据
    - _Requirements: 1.3_

  - [x] 4.4 实现 SetupModal 前端文件解析功能
    - PDF 文件：使用 pdfjs-dist 在浏览器端解析提取文本
    - DOCX/DOC 文件：使用 mammoth 在浏览器端解析提取文本
    - TXT 文件：使用 FileReader 以 UTF-8 编码读取
    - 图片文件（JPG/JPEG/PNG/WEBP）：发送至后端 OCR 接口识别
    - 文件大小限制：超过 20MB 拒绝并提示
    - 格式限制：不在支持列表中的格式拒绝并提示
    - 解析成功后填充到简历文本输入区域，显示文件名
    - 解析失败时显示错误提示 4 秒后消失，保持输入区可编辑
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 4.5 编写 SetupModal 数据持久化和验证的单元测试
    - 验证合法输入写入 localStorage 后可正确读回
    - 验证非法输入被拒绝且 localStorage 不变
    - **Property 2: SetupModal 数据持久化 round-trip**
    - **Property 3: 表单验证拒绝无效输入**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6**

  - [x] 4.6 编写 SetupModal 前端文件解析的单元测试
    - 验证 PDF/DOCX/TXT 文件解析后文本非空
    - 验证超大文件和不支持格式被拒绝
    - **Property 7: 前端文件解析 round-trip**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.6, 8.7**

- [x] 5. 幽灵拦截器清除与知识库路由确认
  - [x] 5.1 扫描并移除前端代码中的幽灵拦截器
    - 在 `frontend/src/**/*.vue` 和 `frontend/src/**/*.js` 中搜索 "仅支持 PDF、TXT 和 MD 文件"
    - 移除包含该字符串的条件分支或 alert/toast 调用的完整代码块
    - 确保移除后不影响同一函数中其他逻辑的正常执行
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.2 确认 Dashboard 菜单中"文件管理"项正确路由到 /files
    - 验证菜单中有且仅有一个指向 `/files` 的菜单项
    - 确认点击后通过 `router.push('/files')` 导航至 KnowledgeBase_Page
    - _Requirements: 5.1, 5.2_

  - [x] 5.3 验证 KnowledgeBase.vue 文件上传调用正确的后端接口
    - 确认文件上传调用 `POST /api/knowledge/upload`
    - 确认接受格式为 PDF、DOCX、TXT、JPG、PNG、WEBP，单文件 ≤10MB
    - 确认上传失败时显示错误提示，成功时更新文件列表
    - _Requirements: 5.3, 5.4, 5.5_

- [x] 6. 构建验证与集成
  - [x] 6.1 执行前端构建验证
    - 运行 `npm run build` 确保零错误完成
    - 确认移除幽灵拦截器后构建正常
    - 确认所有组件导入和引用正确
    - _Requirements: 7.4_

  - [x] 6.2 编写端到端集成测试
    - 测试流程：点击全局资产 → SetupModal 弹出 → 填写提交 → 状态更新为"已就绪"
    - 测试流程：菜单"文件管理" → 跳转 /files → 确认页面渲染
    - **Property 8: 菜单唯一重资产入口**
    - **Validates: Requirements 1.1, 3.1, 5.1, 5.2**

- [x] 7. Final checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- 本次重构不引入新的第三方依赖，仅调整现有代码的调用关系
- 前端使用 Vue 3 Composition API (`<script setup>`)，后端使用 FastAPI + Python

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "4.1", "5.2"] },
    { "id": 2, "tasks": ["2.3", "4.2", "4.3", "5.3"] },
    { "id": 3, "tasks": ["2.4", "4.4"] },
    { "id": 4, "tasks": ["4.5", "4.6", "6.1"] },
    { "id": 5, "tasks": ["6.2"] }
  ]
}
```
