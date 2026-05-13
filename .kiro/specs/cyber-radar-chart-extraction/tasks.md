# Tasks: 提取 CyberRadarChart 公共组件

## Task 1: 创建 CyberRadarChart.vue 独立组件
- [ ] 在 `frontend/src/components/` 下新建 `CyberRadarChart.vue`
- [ ] 将 Dashboard.vue 中关于 `vue-echarts` 的引入、ECharts 的 tree-shaking 注册（`use([CanvasRenderer, RadarChart, ...])`）以及 `radarOption` 配置完整提取到新组件
- [ ] 实现 `chartData` prop（Object 类型，包含 indicators 和 values），若未传入则默认读取 `useUserStore().radarData`
- [ ] 保留原有赛博朋克渐变配色方案不做任何修改

## Task 2: 清理 Dashboard.vue [depends:1]
- [ ] 删除 `<v-chart>` 雷达图所在的外层 Bento 卡片（标题为"六维能力雷达图"的整个 `<div>` 区域）
- [ ] 移除 ECharts 相关 imports（`use`, `CanvasRenderer`, `RadarChart`, `TitleComponent`, `TooltipComponent`, `LegendComponent`, `VChart`）
- [ ] 移除 `use([...])` 调用和 `radarOption` computed 属性
- [ ] 移除 `radarData` computed 属性
- [ ] 确保 SSE 流式对话代码和左侧菜单栏代码完全不受影响
- [ ] 保留右侧"简历诊断 / 面试评估 / 综合规划" Bento 条形图模块

## Task 3: 将 CyberRadarChart 注入 ResumeDiagnosis.vue [depends:1]
- [ ] 在 ResumeDiagnosis.vue 中引入 `CyberRadarChart` 组件
- [ ] 找到右侧现有的简陋 SVG 雷达图占位符区域（`<svg viewBox="0 0 200 200">` 块）
- [ ] 用 `<CyberRadarChart :chartData="resumeRadarData" />` 替换原有 SVG 雷达图
- [ ] 将 `diagnosisScores` 数据转换为 `chartData` 格式（indicators + values）传入组件
- [ ] 给 ResumeDiagnosis.vue 主容器添加赛博朋克底色：将 `bg-[#08080d]` 改为 `bg-[#020205] text-gray-300`
