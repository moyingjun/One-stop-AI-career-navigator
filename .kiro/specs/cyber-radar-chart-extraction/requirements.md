# Requirements: 提取 CyberRadarChart 公共组件并优化子页面视觉

## R1: 组件提取
- 将 Dashboard.vue 中冗余的 ECharts 雷达图提取为独立组件 `@/components/CyberRadarChart.vue`
- 继承原有的赛博朋克配色方案（紫色分割线、青色发光面积、暗色 Tooltip）
- 不修改 ECharts 现有的高颜值渐变配色方案

## R2: 组件化复用
- 雷达图需支持通过 props 接收数据（`chartData`），默认读取 `userStore.radarData`
- 支持不同页面传入不同的六维数据

## R3: Dashboard 清理
- 移除 Dashboard.vue 中"六维能力雷达图"Bento 卡片区域
- 保留右侧原有的"简历诊断 / 面试评估 / 综合规划" Bento 条形图模块
- 清除不再使用的 echarts 相关 import
- 绝对不碰 SSE 流式对话代码和左侧菜单栏代码

## R4: ResumeDiagnosis 集成
- 在 ResumeDiagnosis.vue 中引入并使用 `<CyberRadarChart />` 替换原有简陋的 SVG 雷达图占位符
- 给 ResumeDiagnosis.vue 的主容器添加赛博朋克底色 `bg-[#020205] text-gray-300`
