# Requirements Document

## Introduction

本特性将三个独立的前端业务页面（`ResumeDiagnosis.vue`、`CareerPlanning.vue`、`PremiumInterview.vue`）重构为统一的「AI 任务控制台骨架」（Feature Mission Page Shell），实现「视觉同源、叙事不同型」：三页共享同一套 Hero / Control Grid / Result Zone 三段式结构与暗黑赛博毛玻璃视觉语言，但各自保留差异化的业务叙事（扫描/诊断/报告、路线图/阶段目标/能力缺口、训练舱/实时评分/复盘）。

重构以「不破坏既有业务闭环」为最高优先级：所有后端接口、SSE 流式协议、数据流向、评分链路、Router/Service/Agent 均保持原状；本次仅调整前端视觉骨架与组件复用层。

## Glossary

- **Feature_Mission_Page_Shell**：三页共用的 AI 任务控制台骨架，由 Hero、Control Grid、Result Zone 三段构成，封装为 `FeaturePageShell.vue` 可复用组件
- **Hero**：页面顶部叙事区，承载页面标题、任务描述、状态徽章与主操作 CTA，提供差异化的业务入口叙事
- **Control_Grid**：中部控制网格区，承载页面专属的输入控件、配置选项、操作按钮
- **Result_Zone**：底部结果展示区，承载流式输出、报告卡片、可视化（如雷达图）等业务产出
- **MetricCard**：可复用的指标卡片组件，用于展示评分、计数、状态标签等量化信息，遵循暗黑赛博毛玻璃风格
- **ActionDock**：可复用的操作坞组件，将一组主/次操作按钮以悬浮坞形态聚合呈现
- **SSE_Stream**：基于 Server-Sent Events 的后端流式响应通道，事件类型包括 `meta` / `reply` / `warning` / `error` / `done`
- **Business_Loop**：单页内的业务闭环，包括：简历诊断（上传→分析→报告）、职业规划（输入→阶段路线→能力缺口）、模拟面试（问答→评分→复盘）
- **Visual_Source_Of_Truth**：视觉风格基准，参考 `Dashboard.vue` 的暗黑赛博毛玻璃 + Bento 卡片语言，但本特性禁止修改 `Dashboard.vue`
- **Sidebar_Education_Placeholder**：侧边栏的「升学」模块占位项，呈现为禁用态（disabled），文案固定为「工程师正在玩命开发中，敬请期待！🚀」
- **Loader_Fallback**：当项目中不存在 `StreamingLoader.vue` 时使用的降级加载态实现
- **Toast_Fallback**：当项目中不存在 `Toast.vue` 时使用的降级轻提示实现
- **Resume_Page**：简历诊断页（`frontend/src/ResumeDiagnosis.vue`）
- **Career_Page**：职业规划页（`frontend/src/CareerPlanning.vue`）
- **Interview_Page**：模拟面试页（`frontend/src/PremiumInterview.vue`）
- **Frontend_Console**：本特性涉及的前端任务控制台子系统（包含 `Resume_Page` / `Career_Page` / `Interview_Page` 及其复用组件）

## Requirements

### Requirement 1: 统一 Feature Mission Page Shell 骨架

**User Story:** 作为求职者用户，我希望简历诊断、职业规划、模拟面试三个页面在结构上保持一致的「Hero / Control Grid / Result Zone」三段式布局，从而获得稳定可预期的导航与操作体验。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在 `Resume_Page`、`Career_Page`、`Interview_Page` 三页中均渲染由 Hero、Control_Grid、Result_Zone 三个区域按从上到下顺序组成的页面结构
2. THE Frontend_Console SHALL 通过 `FeaturePageShell.vue` 组件封装 Hero、Control_Grid、Result_Zone 三个区域的容器与栅格规则
3. WHEN 视口宽度大于或等于 1024 像素，THE Feature_Mission_Page_Shell SHALL 以单列纵向堆叠的方式渲染 Hero、Control_Grid、Result_Zone 三个区域
4. WHEN 视口宽度小于 1024 像素，THE Feature_Mission_Page_Shell SHALL 以单列纵向堆叠的方式渲染 Hero、Control_Grid、Result_Zone 三个区域，且每个区域占满可用宽度
5. THE Feature_Mission_Page_Shell SHALL 通过具名插槽（slots）`hero`、`control`、`result` 暴露三个区域的内容注入点
6. IF 任一页面未向 `result` 插槽注入内容，THEN THE Feature_Mission_Page_Shell SHALL 渲染一个空状态占位区，并保持骨架不塌陷

### Requirement 2: 三页业务闭环 100% 兼容

**User Story:** 作为产品负责人，我希望本次重构在视觉调整后保留所有既有业务闭环，从而确保用户的简历诊断、职业规划、模拟面试核心使用路径不被破坏。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在重构后保留 `Resume_Page` 的完整业务闭环：上传简历、触发分析、接收 SSE_Stream、渲染报告
2. THE Frontend_Console SHALL 在重构后保留 `Career_Page` 的完整业务闭环：输入用户背景、生成阶段路线、展示能力缺口
3. THE Frontend_Console SHALL 在重构后保留 `Interview_Page` 的完整业务闭环：进入训练舱、实时问答、实时评分、生成复盘
4. THE Frontend_Console SHALL 在重构前后向后端发起相同的 HTTP 端点路径、HTTP 方法、请求体字段集合
5. THE Frontend_Console SHALL 在重构前后消费相同序列的 SSE_Stream 事件类型（`meta` / `reply` / `warning` / `error` / `done`），且 `done` 事件携带的 `record_id` 字段处理逻辑保持不变
6. WHEN 后端通过 SSE_Stream 推送 `reply` 事件，THE Frontend_Console SHALL 将文本片段以与重构前等价的方式追加到 Result_Zone 的对应渲染节点
7. IF 后端通过 SSE_Stream 推送 `error` 事件，THEN THE Frontend_Console SHALL 在 Result_Zone 展示与重构前等价的错误提示，且不静默吞掉该错误
8. THE Frontend_Console SHALL 不修改 `frontend/src/services/llm_service.js` 中已有的 SSE 解析与请求构建逻辑

### Requirement 3: 三页叙事差异化

**User Story:** 作为求职者用户，我希望即便三页结构一致，仍能在每个页面的 Hero 与 Control_Grid 区识别出该页面专属的业务叙事与操作语言，从而清晰区分当前所在的任务场景。

#### Acceptance Criteria

1. THE Resume_Page SHALL 在 Hero 区呈现与「扫描 / 诊断 / 报告」三阶段叙事一致的标题与状态徽章
2. THE Career_Page SHALL 在 Hero 区呈现与「路线图 / 阶段目标 / 能力缺口」三阶段叙事一致的标题与状态徽章
3. THE Interview_Page SHALL 在 Hero 区呈现与「训练舱 / 实时评分 / 复盘」三阶段叙事一致的标题与状态徽章
4. THE Resume_Page SHALL 在 Control_Grid 区暴露简历上传、目标岗位输入、触发诊断的操作控件
5. THE Career_Page SHALL 在 Control_Grid 区暴露背景输入、目标方向选择、触发规划生成的操作控件
6. THE Interview_Page SHALL 在 Control_Grid 区暴露面试难度选择、开始/结束训练、提交答案的操作控件
7. THE Resume_Page SHALL 在 Result_Zone 区呈现简历诊断报告内容
8. THE Career_Page SHALL 在 Result_Zone 区呈现阶段路线与能力缺口可视化
9. THE Interview_Page SHALL 在 Result_Zone 区呈现实时问答记录、评分指标与复盘卡片

### Requirement 4: 新增可复用组件 FeaturePageShell / MetricCard / ActionDock

**User Story:** 作为前端开发者，我希望将三页共享的视觉骨架与高频 UI 模式抽离为可复用组件，从而避免视觉规范在三页中各自漂移。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在 `frontend/src/components/` 目录下新增 `FeaturePageShell.vue` 组件
2. THE Frontend_Console SHALL 在 `frontend/src/components/` 目录下新增 `MetricCard.vue` 组件
3. THE Frontend_Console SHALL 在 `frontend/src/components/` 目录下新增 `ActionDock.vue` 组件
4. THE FeaturePageShell SHALL 通过 props 接收 `title`、`subtitle`、`stageBadges` 字段，并将其渲染至 Hero 区
5. THE MetricCard SHALL 通过 props 接收 `label`、`value`、`unit`、`trend` 字段，并按暗黑赛博毛玻璃风格渲染量化信息卡片
6. THE ActionDock SHALL 通过具名插槽 `primary`、`secondary` 暴露主操作与次操作的内容注入点
7. THE Resume_Page、Career_Page、Interview_Page SHALL 各自至少使用一次 `FeaturePageShell.vue` 组件来构建页面骨架
8. THE Frontend_Console SHALL 在 `MetricCard.vue` 与 `ActionDock.vue` 内部复用 `CyberGlassCard.vue` 的视觉容器，而不重新实现毛玻璃容器
9. THE Frontend_Console SHALL 不修改 `CyberGlassCard.vue`、`BaseModal.vue`、`CyberRadarChart.vue` 三个既有组件的源文件

### Requirement 5: 视觉风格统一为暗黑赛博毛玻璃

**User Story:** 作为产品负责人，我希望三页的视觉语言与 `Dashboard.vue` 同源，从而保持品牌识别一致。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在 `Resume_Page`、`Career_Page`、`Interview_Page` 三页中均使用暗黑底色作为页面背景基色
2. THE Frontend_Console SHALL 在三页所有卡片容器上启用毛玻璃（backdrop-blur）视觉效果
3. THE Frontend_Console SHALL 在三页中使用 Tailwind CSS 4 与项目既有的设计 token 实现样式，且不引入新的第三方 UI 组件库
4. THE Frontend_Console SHALL 在三页中复用 `CyberGlassCard.vue`、`CyberRadarChart.vue` 既有组件作为卡片与可视化的基本单元
5. THE Frontend_Console SHALL 不修改 `Dashboard.vue` 的源文件
6. THE Frontend_Console SHALL 在三页中保持与 `Dashboard.vue` 一致的字体层级、圆角、阴影、边框透明度等视觉变量

### Requirement 6: 侧边栏升学模块 disabled 占位

**User Story:** 作为求职者用户，我希望在侧边栏看到「升学」模块的可见占位，从而了解该能力即将上线，但当前不可点击。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在三页所共享的侧边栏中渲染一个名为「升学」的导航项
2. THE 「升学」导航项 SHALL 处于禁用（disabled）状态，且不响应点击与键盘激活
3. THE 「升学」导航项 SHALL 显示固定占位文案「工程师正在玩命开发中，敬请期待！🚀」
4. WHEN 用户将鼠标悬停在「升学」导航项上，THE Frontend_Console SHALL 通过 tooltip 或同区域文案展示上述占位文案
5. THE 「升学」导航项 SHALL 不向 Vue Router 注册任何新路由，且不触发页面跳转

### Requirement 7: 硬约束清单（NFR / Constraints）

**User Story:** 作为架构守护者，我希望本特性严格遵守一组不可逾越的硬约束，从而保护既有架构边界与构建安全红线。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 不修改 `Router/` 目录下的任何后端路由文件
2. THE Frontend_Console SHALL 不修改 `Service/` 目录下的任何 Service 或 Agent 文件
3. THE Frontend_Console SHALL 不修改 `Service/Games/Avalon/` 目录下的任何文件
4. THE Frontend_Console SHALL 不修改 `frontend/src/stores/gameStore.js`
5. THE Frontend_Console SHALL 不修改 `frontend/src/AvalonGame.vue`
6. THE Frontend_Console SHALL 不修改 `frontend/src/Dashboard.vue`
7. THE Frontend_Console SHALL 不修改 `frontend/src/router/index.js` 中已注册的路由路径与组件映射
8. THE Frontend_Console SHALL 不修改 `frontend/src/components/CyberGlassCard.vue`、`frontend/src/components/BaseModal.vue`、`frontend/src/components/CyberRadarChart.vue` 三个文件
9. THE Frontend_Console SHALL 不引入新的第三方 UI 组件库依赖到 `frontend/package.json`
10. THE Frontend_Console SHALL 不删除 `Resume_Page`、`Career_Page`、`Interview_Page` 任一页面已有的功能入口
11. THE Frontend_Console SHALL 不移动 `Resume_Page`、`Career_Page`、`Interview_Page` 三个文件的物理路径
12. WHILE 本特性处于实现阶段，THE Frontend_Console SHALL 不执行 `npm run build`、`vite build`、`tsc`、`vue-tsc` 命令
13. THE Frontend_Console SHALL 不修改后端任意 HTTP 接口的请求路径、请求方法或响应数据结构

### Requirement 8: Toast 与 StreamingLoader 缺失时的降级方案

**User Story:** 作为前端开发者，我希望在项目尚未提供 `Toast.vue` 与 `StreamingLoader.vue` 组件的情况下，三页仍能通过明确的降级实现完成提示与加载态展示，从而避免阻塞重构落地。

#### Acceptance Criteria

1. THE Frontend_Console SHALL 在引用提示与加载态组件前先按文件路径检测 `frontend/src/components/Toast.vue` 与 `frontend/src/components/StreamingLoader.vue` 是否存在
2. IF `frontend/src/components/StreamingLoader.vue` 不存在，THEN THE Frontend_Console SHALL 使用一个内联实现的 Loader_Fallback 在 Result_Zone 渲染加载态
3. THE Loader_Fallback SHALL 使用 Tailwind CSS 4 与现有设计 token 实现，并保持暗黑赛博毛玻璃风格
4. IF `frontend/src/components/Toast.vue` 不存在，THEN THE Frontend_Console SHALL 使用一个内联实现的 Toast_Fallback 渲染轻提示
5. THE Toast_Fallback SHALL 在 3000 毫秒后自动消失，且支持成功与错误两种语义样式
6. WHERE `frontend/src/components/StreamingLoader.vue` 存在，THE Frontend_Console SHALL 优先复用该组件而非 Loader_Fallback
7. WHERE `frontend/src/components/Toast.vue` 存在，THE Frontend_Console SHALL 优先复用该组件而非 Toast_Fallback
8. THE Frontend_Console SHALL 将 Loader_Fallback 与 Toast_Fallback 的实现集中在一处复用模块中，且不在三个页面文件内各自重复实现

## Acceptance Criteria（端到端验收要点）

以下是用于人工与自动化验收的端到端要点，约束本特性整体交付质量：

1. WHEN 用户依次访问 `Resume_Page`、`Career_Page`、`Interview_Page`，THE Frontend_Console SHALL 在三页中呈现可识别的同源 Hero / Control_Grid / Result_Zone 骨架
2. WHEN 用户在 `Resume_Page` 上传简历并触发诊断，THE Frontend_Console SHALL 完整跑通上传→分析→报告业务闭环，且 SSE_Stream 事件序列与重构前一致
3. WHEN 用户在 `Career_Page` 提交背景信息并触发规划，THE Frontend_Console SHALL 完整跑通输入→阶段路线→能力缺口业务闭环，且 SSE_Stream 事件序列与重构前一致
4. WHEN 用户在 `Interview_Page` 进入训练舱并完成一轮问答，THE Frontend_Console SHALL 完整跑通问答→评分→复盘业务闭环，且 SSE_Stream 事件序列与重构前一致
5. THE Frontend_Console SHALL 在三页中复用 `FeaturePageShell.vue`、`MetricCard.vue`、`ActionDock.vue` 三个新组件，且不重复实现等价骨架
6. THE Frontend_Console SHALL 在三页所共享的侧边栏中始终展示「升学」disabled 占位项与对应文案
7. THE Frontend_Console SHALL 不触发 `npm run build`、`vite build`、`tsc`、`vue-tsc` 命令
8. THE Frontend_Console SHALL 在视觉抽样对比中与 `Dashboard.vue` 保持暗黑赛博毛玻璃同源风格

## Correctness Properties（PBT 思路）

以下属性以「重构前后等价性」为核心，可以指导后续设计阶段的属性化测试或回归测试用例生成：

1. **请求等价性（Request Equivalence）**：FOR ALL 用户输入 `x` 属于 `Resume_Page`、`Career_Page`、`Interview_Page` 任一页面的合法输入空间，THE Frontend_Console 在重构后向后端发起的 HTTP 请求集合 SHALL 在端点路径、HTTP 方法、请求体字段集合三个维度上与重构前等价
2. **SSE 事件序列等价性（Event Sequence Equivalence）**：FOR ALL 后端在重构前对输入 `x` 返回的 SSE 事件序列 `S`，THE Frontend_Console 在重构后对同一输入 `x` 接收到的 SSE 事件序列 SHALL 在事件类型 `meta` / `reply` / `warning` / `error` / `done` 的相对顺序与计数上与 `S` 等价
3. **渲染节点等价性（Render Node Equivalence）**：FOR ALL 后端响应 `r`，THE Frontend_Console 在重构后渲染的语义节点集合（报告标题、报告条目、评分指标、阶段卡片、能力缺口条目等业务节点）SHALL 不少于重构前对同一响应 `r` 渲染的语义节点集合，即不丢失节点
4. **错误透传不变性（Error Transparency Invariance）**：FOR ALL 后端通过 SSE_Stream 推送的 `error` 事件 `e`，THE Frontend_Console 在重构后 SHALL 与重构前一样在 UI 上向用户呈现该错误，且不静默吞掉
5. **骨架结构幂等性（Shell Idempotence）**：FOR ALL 在 `Resume_Page`、`Career_Page`、`Interview_Page` 之间的导航切换序列，THE Feature_Mission_Page_Shell SHALL 始终渲染恰好一组 Hero、Control_Grid、Result_Zone 区域，且不出现重复或缺失
6. **侧边栏占位不变性（Sidebar Placeholder Invariance）**：FOR ALL 三页页面进入路径，THE 「升学」导航项 SHALL 始终以 disabled 状态出现，且文案恒为「工程师正在玩命开发中，敬请期待！🚀」


补充两点：

SSE error 的规则再写死一点
现在已经说了“不静默吞掉错误”，建议明确成：只展示后端原始错误内容，不额外编造新的错误话术。这样 Kiro 不会自己再包一层提示，导致语义漂移。

FeaturePageShell 的职责边界再收紧
明确它只管布局骨架和插槽，不接业务 API，不处理请求，不碰 SSE 解析。这样不会把三页的业务逻辑偷偷抽散。