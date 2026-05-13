# Implementation Plan: Dashboard Bento Pinia Refactor — Phase 1

## Overview

Phase 1 聚焦于最小可行的基础设施搭建：安装 Pinia + ECharts 依赖，创建基础 userStore（含雷达图 mock 数据），在 main.js 初始化 Pinia，并在现有 Dashboard.vue 中通过 vue-echarts 渲染六维能力雷达图。不拆分组件，不迁移 localStorage，不触碰 SSE 聊天逻辑。

## Tasks

- [x] 1. Install dependencies and initialize Pinia
  - [x] 1.1 Install pinia, echarts, and vue-echarts packages
    - Run `npm install pinia echarts vue-echarts` in the `frontend/` directory
    - Verify packages appear in `package.json` dependencies
    - _Requirements: Phase 1 Goal 1_

  - [x] 1.2 Initialize Pinia in main.js
    - Import `createPinia` from `pinia`
    - Create pinia instance with `createPinia()`
    - Add `app.use(pinia)` before `app.mount('#app')`
    - Do NOT modify any other existing code in main.js (keep the toHex polyfill and router intact)
    - _Requirements: Phase 1 Goal 3_

- [x] 2. Create userStore with radar chart mock data
  - [x] 2.1 Create `src/stores/userStore.js`
    - Create `frontend/src/stores/` directory
    - Define a Pinia store using `defineStore('user', { ... })`
    - Include `state` with:
      - `candidateName`: default empty string
      - `radarData`: object containing radar chart mock data for 六维能力雷达图 with indicators: 技术能力, 沟通表达, 项目经验, 学习能力, 团队协作, 职业规划
      - `panelLayout`: basic panel layout configuration object (e.g., columns count, card sizes)
    - Include a `getters` section with a `greeting` getter that returns time-based greeting (早上好/中午好/下午好/晚上好/夜深了)
    - _Requirements: Phase 1 Goal 2_

- [x] 3. Checkpoint - Verify Pinia setup
  - Ensure pinia is correctly initialized: import userStore in a test component or console log to confirm store is accessible. Ask the user if questions arise.

- [x] 4. Add ECharts radar chart to Dashboard.vue
  - [x] 4.1 Import and register vue-echarts in Dashboard.vue
    - Add imports for `VChart` from `vue-echarts` and required echarts modules (use tree-shaking: `use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, LegendComponent])`)
    - Import `useUserStore` from `@/stores/userStore`
    - Access `radarData` from the store
    - IRON RULE: Do NOT modify any existing SSE streaming chat logic or Session TOC logic
    - _Requirements: Phase 1 Goal 4, Phase 1 Goal 5_

  - [x] 4.2 Add radar chart template and option config in Dashboard.vue
    - Create a computed `radarOption` that builds the ECharts option object using store's `radarData` (indicator names, max values, series data)
    - Style the radar chart with custom colors matching the existing dark theme (purple/cyan/indigo palette)
    - Add the `<v-chart>` component in the template within a new Bento-style card section (placed after the feature carousel area, before the chat panel)
    - Use appropriate sizing (e.g., `style="height: 300px"`) and add a card title like "六维能力雷达图"
    - IRON RULE: Do NOT touch or modify the existing SSE streaming chat logic or Session TOC logic
    - _Requirements: Phase 1 Goal 4, Phase 1 Goal 5_

- [x] 5. Final checkpoint - Verify radar chart renders
  - Ensure the app builds without errors (`npm run build` in frontend/). Ask the user if questions arise.

## Notes

- This task list covers **Phase 1 only**. Component splitting, full localStorage migration, and deep Pinia refactoring are deferred to Phase 2.
- IRON RULE: The existing SSE streaming chat logic and Session TOC logic in Dashboard.vue must NOT be modified.
- The radar chart uses mock data from userStore; real user assessment data integration is a Phase 2 concern.
- No test tasks are included because the design's Correctness Properties relate to full Pinia migration (Phase 2 scope), not Phase 1's minimal setup.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["4.1"] },
    { "id": 3, "tasks": ["4.2"] }
  ]
}
```
