<script setup>
import { computed } from 'vue'

// ECharts tree-shaking imports
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, LegendComponent])

// Pinia store
import { useUserStore } from '@/stores/userStore'

const props = defineProps({
  chartData: {
    type: Object,
    default: null
  }
})

const userStore = useUserStore()

// 若未传入 chartData，则默认读取 userStore.radarData
const radarData = computed(() => props.chartData || userStore.radarData)

// 六维能力雷达图 ECharts 配置（保留原有赛博朋克渐变配色方案）
const radarOption = computed(() => ({
  title: {
    show: false
  },
  tooltip: {
    trigger: 'item',
    appendToBody: true,
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    borderColor: 'rgba(139, 92, 246, 0.3)',
    textStyle: { color: '#e2e8f0', fontSize: 12 }
  },
  legend: {
    show: false
  },
  radar: {
    indicator: radarData.value.indicators.map(item => ({
      name: item.name,
      max: item.max
    })),
    shape: 'polygon',
    splitNumber: 4,
    axisName: {
      color: '#a5b4fc',
      fontSize: 11
    },
    splitLine: {
      lineStyle: { color: 'rgba(139, 92, 246, 0.15)' }
    },
    splitArea: {
      areaStyle: { color: ['rgba(139, 92, 246, 0.02)', 'rgba(139, 92, 246, 0.05)'] }
    },
    axisLine: {
      lineStyle: { color: 'rgba(139, 92, 246, 0.2)' }
    }
  },
  series: [{
    type: 'radar',
    symbol: 'circle',
    symbolSize: 5,
    data: [{
      value: radarData.value.values,
      name: '能力评估',
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(6, 182, 212, 0.35)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.10)' }
          ]
        }
      },
      lineStyle: {
        color: 'rgba(6, 182, 212, 0.8)',
        width: 2
      },
      itemStyle: {
        color: '#06b6d4',
        borderColor: '#a78bfa',
        borderWidth: 1
      }
    }]
  }]
}))
</script>

<template>
  <v-chart :option="radarOption" style="height: 300px; width: 100%;" :autoresize="true" />
</template>
