# Technical Design: 提取 CyberRadarChart 公共组件

## 新组件: `src/components/CyberRadarChart.vue`

### Props
- `chartData` (Object, optional): 包含 `indicators` 和 `values` 的对象，格式与 `userStore.radarData` 一致
  - 若未传入，默认读取 `useUserStore().radarData`

### 内部逻辑
- 使用 `vue-echarts` 的 `<v-chart>` 渲染
- ECharts tree-shaking: 引入 `CanvasRenderer`, `RadarChart`, `TitleComponent`, `TooltipComponent`, `LegendComponent`
- 完整保留原有赛博朋克配色：
  - 分割线: `rgba(139, 92, 246, 0.15)`
  - 面积渐变: cyan → purple
  - Tooltip: 暗色背景 + 紫色边框

## Dashboard.vue 清理

### 移除内容
1. ECharts 相关 imports: `use`, `CanvasRenderer`, `RadarChart`, `TitleComponent`, `TooltipComponent`, `LegendComponent`, `VChart`
2. `use([...])` 调用
3. `radarOption` computed 属性
4. `radarData` computed 属性
5. 模板中"六维能力雷达图 Bento Card"整个 `<div>` 块

### 保留内容
- SSE 流式对话代码
- 左侧菜单栏代码
- 右侧 Bento 条形图模块
- 所有其他功能逻辑

## ResumeDiagnosis.vue 集成

### 替换区域
- 移除原有 SVG 雷达图（`<svg viewBox="0 0 200 200">` 区域）
- 引入 `<CyberRadarChart :chartData="resumeRadarData" />`
- 将 `diagnosisScores` 转换为 `chartData` 格式传入

### 样式调整
- 主容器 `min-h-[100dvh] bg-[#08080d]` → `min-h-[100dvh] bg-[#020205] text-gray-300`
