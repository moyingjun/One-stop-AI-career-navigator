# Requirements Document

## Introduction

本文档定义了"全站 UI 视觉大一统与 CyberGlassCard 创意封装"功能的需求规格。该功能旨在提取一个全局通用的赛博朋克毛玻璃卡片容器组件，统一子页面（PremiumInterview、CareerPlanning）的视觉风格，使其与 Dashboard 已建立的"暗黑赛博朋克 + Glassmorphism + 高信息密度"设计基调保持一致。核心原则为"只动皮囊，不动筋骨"——仅替换 UI 容器与样式，绝不修改任何业务逻辑。

## Glossary

- **CyberGlassCard**: 全局通用的赛博朋克毛玻璃卡片容器 Vue 组件，提供统一的视觉包装层
- **Variant**: CyberGlassCard 的主题色变体，包含 default、cyan、purple、pink、emerald 五种
- **Border_Glow_Animation**: 使用 CSS conic-gradient 旋转实现的边框流光扫描动画效果
- **Glassmorphism**: 毛玻璃设计风格，通过 backdrop-blur 和半透明背景实现
- **Sub_Page**: 需要进行视觉统一的子页面，包括 PremiumInterview.vue、CareerPlanning.vue 和 ResumeDiagnosis.vue
- **Business_Logic**: 页面中的核心功能代码，包括 ref 状态、computed 属性、API 请求、事件处理函数等
- **Back_Button**: 各子页面中的"返回工作台"导航按钮
- **Slot_Content**: 通过 Vue slot 机制传入 CyberGlassCard 的业务 UI 内容

## Requirements

### Requirement 1: CyberGlassCard 组件创建

**User Story:** As a developer, I want a reusable CyberGlassCard component, so that I can wrap page sections with a unified cyberpunk glassmorphism visual style.

#### Acceptance Criteria

1. THE CyberGlassCard SHALL render a container with backdrop-blur (minimum 12px blur radius) and a background opacity between 0.4 and 0.7 to achieve the glassmorphism effect
2. THE CyberGlassCard SHALL accept a variant prop with values limited to default, cyan, purple, pink, and emerald
3. WHEN a variant prop is provided, THE CyberGlassCard SHALL apply the corresponding theme color to border glow, icon color, title color, and corner decoration
4. IF no variant prop is provided, THEN THE CyberGlassCard SHALL use the default variant configuration
5. THE CyberGlassCard SHALL accept an optional title prop and render it in the header area
6. THE CyberGlassCard SHALL accept an optional icon prop (Lucide Vue component) and render it alongside the title
7. WHEN the headerless prop is set to true, THE CyberGlassCard SHALL hide the entire header area including title, icon, and any header slot content
8. WHEN the noPadding prop is set to true, THE CyberGlassCard SHALL remove internal padding from the content area
9. THE CyberGlassCard SHALL provide a default slot for main content, a header slot for custom header override, and a corner slot for decorative elements
10. IF an invalid variant value is provided (not one of default, cyan, purple, pink, emerald), THEN THE CyberGlassCard SHALL fall back to the default variant configuration without rendering errors
11. WHEN the user hovers over the CyberGlassCard, THE CyberGlassCard SHALL visually enhance the border glow intensity and box-shadow within 300ms transition duration

### Requirement 2: 边框流光动画

**User Story:** As a user, I want to see an animated glowing border on card containers, so that the interface feels dynamic and futuristic.

#### Acceptance Criteria

1. THE Border_Glow_Animation SHALL render a CSS conic-gradient that completes one full 360-degree rotation every 4 seconds in its default state
2. THE Border_Glow_Animation SHALL use the variant-specific gradient colors (gradientFrom and gradientTo from VARIANT_MAP) for the glow effect
3. WHEN the user hovers over a CyberGlassCard, THE Border_Glow_Animation SHALL reduce its rotation cycle to 2 seconds and increase the gradient color opacity from 0.6 to 0.9
4. WHEN the user moves the cursor away from a CyberGlassCard, THE Border_Glow_Animation SHALL transition back to its default rotation speed and opacity over a duration of 300 milliseconds using an ease-out timing function
5. THE Border_Glow_Animation SHALL use CSS animations on composite-friendly properties (transform, opacity) for the glow overlay, and use GPU-accelerated rendering (will-change or translateZ) on the conic-gradient pseudo-element to maintain 60fps rendering performance

### Requirement 3: 子页面视觉统一

**User Story:** As a user, I want all sub-pages to share the same dark cyberpunk visual style as the Dashboard, so that the application feels cohesive and polished.

#### Acceptance Criteria

1. THE Sub_Page outermost container element SHALL set its background-color to #020205 on PremiumInterview, CareerPlanning, and ResumeDiagnosis pages, and any radial-gradient vignette overlays SHALL fade to #020205 instead of the previous #050505
2. WHEN a Sub_Page is rendered, THE Sub_Page SHALL wrap each distinct functional area (left-panel sidebar, main content/chat area, and any modal overlays) in a CyberGlassCard component, replacing inline backdrop-blur containers and ad-hoc border/bg utility class groupings
3. THE Sub_Page color palette for borders, text highlights, icon colors, and glow effects SHALL use only colors from the purple family (rgba 139, 92, 246 at any opacity between 0.05 and 1) and the cyan family (rgba 6, 182, 212 at any opacity between 0.05 and 1), with neutral grays (white at reduced opacity) permitted for body text and dividers
4. WHEN a Sub_Page is refactored, THE Sub_Page SHALL remove page-specific aurora-blob and decorative background animation elements, relying instead on the shared ambient background treatment established in the Dashboard (purple and cyan blur layers with grid overlay)

### Requirement 4: 业务逻辑保护

**User Story:** As a developer, I want the UI refactoring to preserve all existing business logic, so that no functional regressions are introduced.

#### Acceptance Criteria

1. WHEN any Sub_Page is refactored to use CyberGlassCard, THE Business_Logic in the script setup block SHALL remain identical to the original with zero modifications to imports, ref declarations, computed properties, API calls, event handler functions, and lifecycle hooks (onMounted, onUnmounted)
2. WHEN any Sub_Page is refactored, THE Slot_Content SHALL render all original business UI elements (forms, lists, chat messages, markdown output) preserving their v-model bindings, event bindings (@click, @keydown, v-for, v-if conditions), and parent-child DOM nesting order without omission
3. WHEN any Sub_Page is refactored, THE Sub_Page SHALL preserve all existing Vue Router navigation calls including router.push paths (e.g., '/dashboard', '/career-planning', '/') and route.query parameter handling (e.g., route.query.id for history restoration)
4. WHEN any Sub_Page refactoring is completed, THE Sub_Page script setup block SHALL produce an identical diff (zero changed lines) when compared to the pre-refactoring version using a line-by-line text comparison

### Requirement 5: 返回按钮统一

**User Story:** As a user, I want a consistent "返回工作台" button across all sub-pages, so that navigation feels predictable and visually unified.

#### Acceptance Criteria

1. WHEN the user clicks the Back_Button on any Sub_Page, THE Back_Button SHALL invoke router.push('/dashboard')
2. THE Back_Button SHALL display the ArrowLeft icon (size 16x16 px) from lucide-vue-next followed by the text "返回工作台" (font-size 14px)
3. WHEN the user hovers over the Back_Button, THE Back_Button SHALL apply a leftward translate-x of 4px (translate-x-1) to the arrow icon with a 300ms ease transition
4. THE Back_Button SHALL render text in cyan-400 at 70% opacity by default, and WHEN the user hovers over the Back_Button, THE Back_Button SHALL transition to 100% opacity within 300ms
5. THE Back_Button SHALL be positioned outside of and above any CyberGlassCard containers, within the top-level page padding area
6. WHEN the Back_Button receives keyboard focus, THE Back_Button SHALL display a visible focus indicator (outline or ring) meeting a minimum 3:1 contrast ratio against the background

### Requirement 6: 响应式布局兼容

**User Story:** As a user, I want the refactored pages to work correctly on both mobile and desktop screens, so that the experience is consistent across devices.

#### Acceptance Criteria

1. THE CyberGlassCard SHALL render for viewport widths from 320px to 2560px without causing a horizontal scrollbar to appear, without any content being clipped by overflow:hidden, and without any child element extending beyond the viewport boundary
2. IF the viewport width is below 768px, THEN THE Sub_Page layout SHALL switch from side-by-side arrangement to a single stacked column arrangement where panels display in top-to-bottom order
3. WHEN content exceeds the CyberGlassCard container height, THE CyberGlassCard SHALL enable vertical scrolling with a semi-transparent scrollbar no wider than 6px, colored to match the card's active variant theme color at 40% opacity
4. WHILE the viewport width is below 768px, THE CyberGlassCard SHALL occupy 100% of the available container width and allow vertical touch-gesture scrolling within its content area

### Requirement 7: 无效 Variant 容错

**User Story:** As a developer, I want the component to handle invalid variant values gracefully, so that the UI does not break due to configuration errors.

#### Acceptance Criteria

1. IF the variant prop value is not one of the valid variants ('default', 'cyan', 'purple', 'pink', 'emerald') or is undefined/null, THEN THE CyberGlassCard SHALL apply the 'default' variant configuration (border color, glow color, gradient, icon color, title color, and corner color matching the default entry in VARIANT_MAP)
2. WHEN the icon prop is not provided or is undefined, THE CyberGlassCard SHALL render the header area with only the title text and SHALL NOT render any icon element or placeholder in the icon position
3. IF an invalid variant value or missing icon prop is provided, THEN THE CyberGlassCard SHALL render without producing JavaScript runtime errors and without layout breakage (no content overflow, no missing container borders, no absent background effects)

### Requirement 8: 动画性能与无障碍

**User Story:** As a user with motion sensitivity preferences, I want animations to respect my system settings, so that the interface does not cause discomfort.

#### Acceptance Criteria

1. WHEN the user has prefers-reduced-motion enabled, THE CyberGlassCard SHALL stop all border glow rotation animation and display a static border using the variant's gradientFrom color at 30% opacity instead
2. WHEN the user has prefers-reduced-motion enabled, THE CyberGlassCard SHALL disable hover-triggered visual transitions (glow intensification, border animation speed change) and apply hover state changes instantaneously with no transition duration
3. THE CyberGlassCard SHALL not introduce more than 3 additional DOM layers compared to the original page structure
4. WHILE animations are active and prefers-reduced-motion is not enabled, THE CyberGlassCard border glow animation SHALL run at a consistent 60 frames per second without causing frame drops below 30fps on the host page
