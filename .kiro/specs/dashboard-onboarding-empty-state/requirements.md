# Requirements Document

## Introduction

本功能为 Dashboard 底部的"继续上次"区块重构零数据态（Empty State）体验。当用户尚无任何历史记录时，渲染"新手启航舱"引导面板，展示 4 个功能引导卡片，帮助新用户快速了解并进入各核心功能模块。一旦用户完成任意一次对话或诊断并产生历史记录，引导舱自动隐藏，平滑切换回现有的历史记录列表。

整个改动仅涉及 `frontend/src/Dashboard.vue` 单文件，不引入任何新依赖，与现有 Dark Cyberpunk + Glassmorphism 视觉风格完全一致。

---

## Glossary

- **Dashboard**：系统主界面，包含聊天区、功能卡片轮播、历史记录区等模块
- **OnboardingPanel**：新手启航舱，零数据态下渲染的引导面板
- **HistoryPanel**：继续上次区块，有历史记录时渲染的历史列表
- **historyRecords**：Vue 响应式 `ref([])` 数组，存储从 `/api/history?limit=2` 加载的历史记录
- **OnboardingCard**：新手启航舱内的单张功能引导卡片
- **LockedCard**：处于锁定状态的引导卡片（opacity 降低，按钮不可点击）
- **ActiveCard**：处于激活状态的引导卡片（可点击跳转）
- **Router**：Vue Router 5 实例，通过 `router.push(path)` 执行页面跳转
- **loadHistory**：从后端 `/api/history?limit=2` 加载历史记录的异步函数

---

## Requirements

### Requirement 1: 零数据态检测与面板切换

**User Story:** 作为一名新用户，我希望在没有任何历史记录时看到引导面板，以便快速了解系统的核心功能并开始使用。

#### Acceptance Criteria

1. WHEN Dashboard 挂载完成且 `loadHistory()` 返回空数组时，THE Dashboard SHALL 将 OnboardingPanel 渲染至 DOM 中，并将 HistoryPanel 从 DOM 中移除
2. WHEN Dashboard 挂载完成且 `loadHistory()` 返回至少一条记录时，THE Dashboard SHALL 将 HistoryPanel 渲染至 DOM 中，并将 OnboardingPanel 从 DOM 中移除
3. THE Dashboard SHALL 保证 OnboardingPanel 与 HistoryPanel 在任意时刻有且仅有一个存在于 DOM 中（严格 XOR 关系）
4. IF `loadHistory()` 因网络错误或非 2xx 响应而失败，THEN THE Dashboard SHALL 保持 `historyRecords` 为空数组，并将 OnboardingPanel 渲染至 DOM 中
5. WHILE `loadHistory()` 请求正在进行中，THE Dashboard SHALL 不将 OnboardingPanel 或 HistoryPanel 渲染至 DOM 中，并显示加载占位状态

---

### Requirement 2: 新手启航舱容器样式

**User Story:** 作为一名新用户，我希望引导面板与整体界面风格一致，以便获得沉浸式的视觉体验。

#### Acceptance Criteria

1. WHEN OnboardingPanel 被渲染时，THE OnboardingPanel SHALL 使用与 HistoryPanel 完全相同的外层容器样式类：`rounded-[28px] border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5`
2. WHEN OnboardingPanel 首次进入 DOM 时，THE OnboardingPanel SHALL 触发一次 `animate-fade-in-up` 入场动画，且该动画仅执行一次
3. THE OnboardingPanel 顶部 SHALL 显示全局引导语："系统初始化完成。欢迎登舰，新同学。四大核心引擎已就绪，请选择你的首个突破口进行全息扫描。"
4. THE 全局引导语 SHALL 使用 `text-xs text-gray-400` 样式，并带有左侧竖线装饰（`border-l-2 border-purple-500/50 pl-3`）

---

### Requirement 3: 引导卡片响应式网格布局

**User Story:** 作为一名用户，我希望引导卡片在不同屏幕尺寸下都能合理排列，以便在任何设备上获得良好的浏览体验。

#### Acceptance Criteria

1. WHILE 视口宽度 ≥ 1024px（`lg` 断点及以上）时，THE OnboardingPanel SHALL 以固定 4 列网格排列引导卡片，无论屏幕宽度多大均保持 4 列不变
2. WHILE 视口宽度在 768px–1023px（`md` 断点）时，THE OnboardingPanel SHALL 以 2×2 网格排列引导卡片
3. WHILE 视口宽度 < 768px（`sm` 断点以下）时，THE OnboardingPanel SHALL 以单列堆叠排列引导卡片
4. THE OnboardingPanel SHALL 在相邻卡片之间保持 12px（`gap-3`）的间距

---

### Requirement 4: 激活状态引导卡片

**User Story:** 作为一名新用户，我希望点击功能引导卡片后能直接跳转到对应功能页，以便快速开始使用。

#### Acceptance Criteria

1. THE OnboardingPanel SHALL 渲染以下三张激活状态引导卡片（可点击、按钮可交互、无禁用遮罩）：简历诊断（Resume Scanner）、模拟面试（Combat Simulator）、职业规划（Career Compass）
2. WHEN 用户点击"立即诊断"按钮时，THE Router SHALL 跳转至 `/resume-diagnosis`
3. WHEN 用户点击"开启实战"按钮时，THE Router SHALL 跳转至 `/interview`
4. WHEN 用户点击"生成路线"按钮时，THE Router SHALL 跳转至 `/career-planning`
5. THE 每张激活卡片 SHALL 包含以下全部元素：Emoji 图标区域、功能标题（中文）、英文副标题、功能描述文本、主色高亮操作按钮；缺少任意一项均视为不合格
6. THE 激活卡片按钮 SHALL 应用对应功能的主题色样式（简历诊断：`text-purple-300 bg-purple-500/20 hover:bg-purple-500/30`；模拟面试：`text-pink-300 bg-pink-500/20 hover:bg-pink-500/30`；职业规划：`text-blue-300 bg-blue-500/20 hover:bg-blue-500/30`）
7. WHEN 用户悬停在激活卡片上时，THE 卡片 SHALL 应用 `hover:-translate-y-1` 上移效果，并分别应用对应主题色阴影（简历诊断：`hover:shadow-[0_8px_24px_rgba(168,85,247,0.2)]`；模拟面试：`hover:shadow-[0_8px_24px_rgba(236,72,153,0.2)]`；职业规划：`hover:shadow-[0_8px_24px_rgba(59,130,246,0.2)]`），过渡时间 `transition-all duration-300`

---

### Requirement 5: 锁定状态引导卡片

**User Story:** 作为一名用户，我希望看到尚未开放的功能模块的预告，以便了解系统的未来规划，同时不会误触未完成的功能。

#### Acceptance Criteria

1. WHEN OnboardingPanel 被渲染时，THE OnboardingPanel SHALL 渲染一张锁定状态的引导卡片：升学与避坑（Academic Radar）
2. THE LockedCard SHALL 应用 `opacity-60` 样式，使整体视觉呈半透明状态（仅为视觉效果，不影响点击事件的传递）
3. THE LockedCard 的操作按钮 SHALL 显示文案"模块构筑中... Coming Soon"，并应用 `animate-pulse` 闪烁动画
4. THE LockedCard 的操作按钮 SHALL 应用 `cursor-not-allowed` 样式
5. IF 用户点击 LockedCard 的操作按钮，THEN THE Dashboard SHALL 阻止任何路由跳转行为，并通过 Toast 提示"该模块正在开发中，敬请期待！"向用户反馈，Toast 显示时长为 3 秒
6. THE LockedCard 的外层容器边框 SHALL 使用 `border-emerald-500/40`，操作按钮 SHALL 使用 `border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50`

---

### Requirement 6: 空态与有数据态的过渡动画

**User Story:** 作为一名用户，我希望从引导面板切换到历史记录列表时有平滑的过渡动画，以便获得流畅的视觉体验。

#### Acceptance Criteria

1. THE Dashboard SHALL 使用 Vue `<transition>` 组件包裹 OnboardingPanel 与 HistoryPanel 的切换区块
2. THE 过渡动画 SHALL 使用 `mode="out-in"`，确保旧面板的离场动画完全结束后，新面板的入场动画才开始
3. THE 过渡动画 SHALL 同时作用于 `opacity`（从 0 到 1）和 `transform: translateY`（从 8px 偏移到 0），持续时间 0.4s，缓动函数 `ease`
4. WHEN `historyRecords` 从空数组变为非空数组时，THE Dashboard SHALL 触发 OnboardingPanel 的离场动画（opacity 降至 0，translateY 增至 8px）和 HistoryPanel 的入场动画（opacity 从 0 升至 1，translateY 从 8px 归零）

---

### Requirement 7: 引导卡片文案内容

**User Story:** 作为一名新用户，我希望每张引导卡片都有清晰的功能描述，以便在选择前了解各功能的用途。

#### Acceptance Criteria

1. WHEN 简历诊断卡片被渲染时，THE 卡片 SHALL 显示描述文本："深度解析过往经历，精准对齐目标岗位。找出致命失分项并提供重构建议，让你的简历一击必中。"
2. WHEN 模拟面试卡片被渲染时，THE 卡片 SHALL 显示描述文本："沉浸式 AI 语音实战对练。模拟真实业务场景与高频拷问，生成多维度能力雷达，彻底消除实战恐慌。"
3. WHEN 职业规划卡片被渲染时，THE 卡片 SHALL 显示描述文本："基于个人特质与行业真实大数据，打破信息壁垒，为你定制科学、清晰的长线职场发展路径。"
4. WHEN 升学与避坑卡片被渲染时，THE 卡片 SHALL 显示描述文本："专插本、考研真实数据导航。帮你平衡繁重的课业规划与升学抉择，绕开前人踩过的坑。"
5. WHEN 任意卡片的描述文本超过 3 行时，THE 卡片 SHALL 截断超出内容并显示省略号，文本使用小字号（`text-xs`）和次要色（`text-gray-400`），行高宽松（`leading-relaxed`）

---

### Requirement 8: 零副作用渲染

**User Story:** 作为系统维护者，我希望新手启航舱的渲染不产生额外的副作用，以便保证系统性能和状态一致性。

#### Acceptance Criteria

1. THE OnboardingPanel 的渲染 SHALL 不触发任何在组件初始挂载序列之外的 fetch 或 XHR 请求
2. THE OnboardingPanel 的渲染 SHALL 不修改任何现有的 Vue 响应式 `ref` 状态（`historyRecords` 本身除外）
3. THE OnboardingPanel 的卡片数据 SHALL 在每次重新渲染时保持完全一致，且不依赖任何响应式数据源
4. WHEN 最后一个待处理的 `loadHistory()` Promise 完成后，THE Dashboard SHALL 仅根据该 Promise 的最终返回值决定渲染哪个面板
5. WHEN `historyRecords` 从空数组变为非空数组时，THE Dashboard SHALL 不重置或清空当前聊天消息（`chatMessages`）等其他响应式状态
