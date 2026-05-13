# Implementation Plan: CyberGlassCard UI Unification

## Overview

将 Dashboard 已建立的"暗黑赛博朋克 + Glassmorphism"设计语言提取为全局通用的 `CyberGlassCard.vue` 组件，并将 PremiumInterview 和 CareerPlanning 子页面的外层容器重构为该组件。核心原则："只动皮囊，不动筋骨"——仅替换 UI 容器与样式层，绝不触碰任何业务逻辑。

## Tasks

- [x] 1. 创建并精细打磨 CyberGlassCard.vue 组件
  - [x] 1.1 创建 CyberGlassCard 组件骨架与 Props/Slots 接口
    - 在 `frontend/src/components/CyberGlassCard.vue` 创建组件文件
    - 实现 `<script setup>` 中的 props 定义：title, icon, variant, noPadding, headerless
    - 实现 VARIANT_MAP 配置对象（default, cyan, purple, pink, emerald 五种主题色）
    - 实现 variantClasses computed 属性
    - 定义三个 slot：default（主体内容）、header（自定义 header）、corner（右上角角标）
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [x] 1.2 实现毛玻璃容器与 Header 渲染模板
    - 编写 `<template>` 结构：外层容器 + 内容区域双层结构
    - 实现 backdrop-blur（最小 12px）+ 半透明背景（opacity 0.4-0.7）
    - 实现 Header 区域：条件渲染 title + icon，支持 headerless 隐藏
    - 实现 header slot 覆盖默认 header 的逻辑
    - 实现 corner slot 右上角科技感角标区域
    - 实现 noPadding 条件移除内部 padding
    - _Requirements: 1.1, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 1.3 实现边框流光动画（conic-gradient 旋转）
    - 使用 `::before` 伪元素承载 conic-gradient 旋转动画
    - 实现 `@keyframes borderGlow` 从 0deg 到 360deg 旋转，默认 4s 周期
    - 根据 variant 应用对应的 gradientFrom/gradientTo 颜色
    - 使用 `will-change: transform` 和 GPU 加速确保 60fps
    - _Requirements: 2.1, 2.2, 2.5_

  - [x] 1.4 实现 Hover 视觉增强与过渡动画
    - Hover 时边框流光加速（4s → 2s 周期）
    - Hover 时渐变色 opacity 从 0.6 提升到 0.9
    - Hover 时外发光 box-shadow 增强
    - 所有过渡使用 300ms ease-out timing function
    - 离开时平滑过渡回默认状态
    - _Requirements: 1.11, 2.3, 2.4_

  - [x] 1.5 实现极光阴影与科技感装饰细节
    - 添加 variant 对应的外发光阴影（glowColor from VARIANT_MAP）
    - 实现角标装饰元素的默认样式（cornerColor）
    - 添加容器圆角、边框半透明效果
    - _Requirements: 1.3, 3.3_

  - [x] 1.6 实现响应式布局与滚动条样式
    - 确保 320px-2560px 视口无水平溢出
    - 内容超出时启用 overflow-y-auto 垂直滚动
    - 自定义滚动条样式：宽度 ≤6px，颜色匹配 variant 主题色 40% opacity
    - 移动端（<768px）占满容器宽度，支持触摸滚动
    - _Requirements: 6.1, 6.3, 6.4_

  - [x] 1.7 实现 prefers-reduced-motion 无障碍降级
    - 添加 `@media (prefers-reduced-motion: reduce)` 媒体查询
    - 停止边框流光旋转动画，改为静态边框（gradientFrom 30% opacity）
    - 禁用 hover 过渡动画，状态变化即时生效
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 1.8 实现无效 Variant 容错处理
    - 无效 variant 值回退到 'default' 配置
    - icon 未传入时 header 仅显示 title，不渲染 icon 占位
    - 确保任何 props 组合不产生 JS 运行时错误
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Checkpoint - 确认 CyberGlassCard 组件完成
  - Ensure all tests pass, ask the user if questions arise.
  - 在浏览器中验证组件各 variant 渲染效果、hover 动画、响应式表现

- [x] 3. 将 PremiumInterview.vue 重构为 CyberGlassCard 容器
  - [x] 3.1 修改 PremiumInterview.vue 页面背景与布局结构
    - 将最外层背景色从 `#050505` 改为 `#020205`
    - 移除页面级 aurora-blob 装饰元素，替换为统一的紫/青 blur 背景层
    - 保留 CRT 扫描线等全局装饰（如需要）
    - 修改 radial-gradient vignette 的终止色为 `#020205`
    - **script setup 块保持完全不变**
    - _Requirements: 3.1, 3.4, 4.1, 4.4_

  - [x] 3.2 用 CyberGlassCard 包裹 PremiumInterview 左侧面板
    - 将左侧面板（能力雷达 + 候选人档案）用 `<CyberGlassCard variant="pink">` 包裹
    - 保留所有 slot 内容（雷达图 SVG、简历预览、JD 展示）结构不变
    - 保留所有 v-model、v-if、v-for、@click 等绑定
    - 移除被 CyberGlassCard 替代的内联 backdrop-blur/border 样式
    - _Requirements: 3.2, 4.2_

  - [x] 3.3 用 CyberGlassCard 包裹 PremiumInterview 右侧对话区
    - 将右侧对话区（Header + 消息列表 + 输入框）用 `<CyberGlassCard headerless variant="default" no-padding>` 包裹
    - 保留所有聊天消息渲染逻辑、SSE 流式输出、输入框绑定
    - 保留 focus-glow 专注模式效果
    - _Requirements: 3.2, 4.2_

  - [x] 3.4 统一 PremiumInterview 返回按钮样式
    - 保留 `router.push('/dashboard')` 路由导航功能
    - 统一按钮样式：ArrowLeft 图标 + "返回工作台" 文本
    - 实现 hover 时 arrow 左移 4px（translate-x-1）+ 300ms ease 过渡
    - 文本颜色 cyan-400/70 → hover 时 cyan-400（100% opacity）
    - 按钮位于 CyberGlassCard 容器外部，页面顶部区域
    - 添加键盘 focus 可见指示器（outline/ring，≥3:1 对比度）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 3.5 精简 PremiumInterview 的 scoped style
    - 移除被 CyberGlassCard 替代的样式（aurora-blob、独立 backdrop-blur 容器样式）
    - 保留业务相关样式（消息气泡、雷达图动画、matrix modal 等）
    - 保留 markdown-body 相关样式
    - 确保移动端（<768px）切换为单列堆叠布局
    - _Requirements: 3.4, 6.2_

- [x] 4. Checkpoint - 确认 PremiumInterview 重构完成
  - Ensure all tests pass, ask the user if questions arise.
  - 验证面试功能正常：发送消息、接收 AI 回复、评估报告生成、历史记录恢复

- [x] 5. 将 CareerPlanning.vue 重构为 CyberGlassCard 容器
  - [x] 5.1 修改 CareerPlanning.vue 页面背景与布局结构
    - 将最外层背景色从 `#050505` 改为 `#020205`
    - 移除页面级 aurora-blob 装饰元素，替换为统一的紫/青 blur 背景层
    - 移除 grid-bg 和 CRT 扫描线（由统一背景替代）
    - 修改 radial-gradient vignette 的终止色为 `#020205`
    - **script setup 块保持完全不变**
    - _Requirements: 3.1, 3.4, 4.1, 4.4_

  - [x] 5.2 用 CyberGlassCard 包裹 CareerPlanning 左侧控制台
    - 将左侧控制台（简历预览 + 困惑输入 + 生成按钮）用 `<CyberGlassCard variant="cyan">` 包裹
    - 保留所有 slot 内容（textarea、chips、generate button）结构不变
    - 保留所有 v-model、@click、:disabled 等绑定
    - 移除被 CyberGlassCard 替代的内联 backdrop-blur/border 样式
    - _Requirements: 3.2, 4.2_

  - [x] 5.3 用 CyberGlassCard 包裹 CareerPlanning 右侧报告区
    - 将右侧报告区（Header + Markdown 输出 + 操作按钮）用 `<CyberGlassCard headerless variant="emerald" no-padding>` 包裹
    - 保留所有 Markdown 渲染逻辑、SSE 流式输出、复制/导出功能
    - 保留 loading 状态和空状态展示
    - _Requirements: 3.2, 4.2_

  - [x] 5.4 统一 CareerPlanning 返回按钮样式
    - 保留 `router.push('/dashboard')` 路由导航功能
    - 统一按钮样式：ArrowLeft 图标 + "返回工作台" 文本
    - 实现 hover 时 arrow 左移 4px（translate-x-1）+ 300ms ease 过渡
    - 文本颜色 cyan-400/70 → hover 时 cyan-400（100% opacity）
    - 按钮位于 CyberGlassCard 容器外部，页面顶部区域
    - 添加键盘 focus 可见指示器（outline/ring，≥3:1 对比度）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 5.5 精简 CareerPlanning 的 scoped style
    - 移除被 CyberGlassCard 替代的样式（aurora-blob、grid-bg、crt-overlay 等）
    - 保留业务相关样式（markdown-body、generate-btn-shimmer 等）
    - 保留 fade transition 动画
    - 确保移动端（<768px）切换为单列堆叠布局
    - _Requirements: 3.4, 6.2_

- [x] 6. Final Checkpoint - 全面验证
  - Ensure all tests pass, ask the user if questions arise.
  - 验证 PremiumInterview 所有面试功能正常（发送消息、SSE 流、评估报告、历史恢复）
  - 验证 CareerPlanning 职业规划生成功能正常（SSE 流式输出、Markdown 渲染、复制/导出）
  - 验证两个页面的"返回工作台"路由导航正常
  - 验证移动端响应式布局正确（<768px 单列堆叠）
  - 确认所有 script setup 块与重构前完全一致（零修改）

- [x] 7. 重构 ResumeDiagnosis.vue 为 CyberGlassCard 容器
  - [x] 7.1 修改 ResumeDiagnosis.vue 页面背景与布局结构
    - 移除左侧固定侧边栏，改为页面级返回按钮
    - 将右侧主工作区的外层容器替换为统一的紫/青 blur 背景层
    - 保留 bg-[#020205] 背景色
    - **script setup 块保持完全不变（仅允许添加 CyberGlassCard import）**
    - _Requirements: 3.1, 3.4, 4.1, 4.4_

  - [x] 7.2 用 CyberGlassCard 包裹 ResumeDiagnosis 左侧简历输入区
    - 将左栏（文件上传 + 简历内容 + 目标岗位 + JD + 诊断按钮）用 `<CyberGlassCard variant="purple" headerless no-padding>` 包裹
    - 保留所有 v-model、@click、:disabled 等绑定
    - _Requirements: 3.2, 4.2_

  - [x] 7.3 用 CyberGlassCard 包裹 ResumeDiagnosis 右侧报告区
    - 将右栏（报告标题栏 + 雷达图 + Markdown 输出 + 面试入口按钮）用 `<CyberGlassCard variant="purple" headerless no-padding>` 包裹
    - 保留所有 Markdown 渲染逻辑、SSE 流式输出
    - _Requirements: 3.2, 4.2_

  - [x] 7.4 统一 ResumeDiagnosis 返回按钮样式
    - 移除左侧侧边栏中的返回按钮
    - 在页面级别添加统一的 absolute 定位返回按钮
    - 样式与 PremiumInterview/CareerPlanning 一致（cyan-400/70 + hover + focus ring）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 8. 全站布局瑕疵微调
  - [x] 8.1 修复返回按钮与卡片重叠问题
    - 在 PremiumInterview、CareerPlanning、ResumeDiagnosis 的主内容容器添加 `mt-14` 或 `pt-14`
    - 确保返回按钮不与 CyberGlassCard 内容重叠
    - _Requirements: 5.5, 6.1_

- [ ] 9. Dashboard 首页数据最终同步
  - [ ] 9.1 确认 Dashboard 六维雷达图与进度条数据绑定
    - 验证 CyberRadarChart 组件在 Dashboard 中正确渲染
    - 确认 radarData 从 Pinia userStore 正确获取
    - 确认六根进度条（专业技能、逻辑分析、沟通表达、问题解决、综合潜力、抗压韧性）正确显示
    - _Requirements: 4.2_

## Notes

- 核心原则："只动皮囊，不动筋骨"——script setup 块必须保持 byte-for-byte 一致
- PremiumInterview 建议使用 pink 或 default 主题变体
- CareerPlanning 建议使用 cyan 或 emerald 主题变体
- 所有原始业务 UI 元素必须通过 slot 完整保留
- 返回按钮位于页面级别，不被 CyberGlassCard 包裹
- 边框流光动画使用纯 CSS 实现，确保 60fps 性能
- 需要关注 prefers-reduced-motion 无障碍降级
- Property tests 验证核心正确性属性（业务逻辑保护、slot 完整性、variant 映射一致性）

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.8"] },
    { "id": 2, "tasks": ["1.3", "1.5", "1.6", "1.7"] },
    { "id": 3, "tasks": ["1.4"] },
    { "id": 4, "tasks": ["3.1", "5.1"] },
    { "id": 5, "tasks": ["3.2", "3.3", "5.2", "5.3"] },
    { "id": 6, "tasks": ["3.4", "3.5", "5.4", "5.5"] }
  ]
}
```
