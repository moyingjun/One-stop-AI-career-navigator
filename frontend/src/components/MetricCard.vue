<script setup>
/**
 * MetricCard.vue
 *
 * 量化指标卡片：以暗黑赛博毛玻璃风格展示评分 / 计数 / 状态标签。
 *
 * 设计契约（参见 design.md §"2. MetricCard.vue（新增）"）：
 * - 内部复用 CyberGlassCard，不重新实现毛玻璃容器（Requirement 4.8）
 * - 根元素根据 trend 取值带上 trend-up / trend-down / trend-flat class
 *   方向标记色调分别为绿（up）/ 红（down）/ 灰（flat）
 * - 默认 slot 用于自定义图标 / 副文案
 * - 受保护文件清单：本组件不修改 CyberGlassCard.vue（read-only 复用）
 *
 * 二阶段增强：
 * - 卡片更"仪表盘"：左侧 tone 强调色短条 + 右上 trend 图标更明显
 * - hover 时轻微抬起 + 轻光晕，但不破坏暗黑赛博风格
 * - 数值与单位字号 / 颜色层级进一步拉开
 * - 无业务 API、无 fetch / axios / EventSource 依赖
 */
import { computed } from 'vue'
import { TrendingUp, TrendingDown, Minus } from 'lucide-vue-next'
import CyberGlassCard from './CyberGlassCard.vue'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  unit: {
    type: String,
    default: ''
  },
  trend: {
    type: String,
    default: '',
    validator: (v) => v === '' || ['up', 'down', 'flat'].includes(v)
  },
  tone: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'cyan', 'purple', 'pink', 'emerald'].includes(v)
  }
})

// 根元素的 trend class — Property 5 要求 trend 取定值时存在对应方向标记 class
const trendClass = computed(() => {
  if (props.trend === 'up') return 'trend-up'
  if (props.trend === 'down') return 'trend-down'
  if (props.trend === 'flat') return 'trend-flat'
  return ''
})

// 方向标记色调：绿 / 红 / 灰
const trendIconColorClass = computed(() => {
  if (props.trend === 'up') return 'text-emerald-400'
  if (props.trend === 'down') return 'text-red-400'
  if (props.trend === 'flat') return 'text-gray-400'
  return ''
})

const trendIcon = computed(() => {
  if (props.trend === 'up') return TrendingUp
  if (props.trend === 'down') return TrendingDown
  if (props.trend === 'flat') return Minus
  return null
})

const trendAriaLabel = computed(() => {
  if (props.trend === 'up') return '上升趋势'
  if (props.trend === 'down') return '下降趋势'
  if (props.trend === 'flat') return '持平趋势'
  return ''
})

// value 强调色随 tone 变化，与 Dashboard / CyberGlassCard 同源
const valueToneClass = computed(() => {
  const map = {
    default: 'text-purple-200',
    cyan: 'text-cyan-200',
    purple: 'text-purple-200',
    pink: 'text-pink-200',
    emerald: 'text-emerald-200'
  }
  return map[props.tone] || map.default
})

// 左侧短色条颜色（仪表盘左侧 accent）
const accentBarClass = computed(() => {
  const map = {
    default: 'metric-accent--purple',
    cyan: 'metric-accent--cyan',
    purple: 'metric-accent--purple',
    pink: 'metric-accent--pink',
    emerald: 'metric-accent--emerald'
  }
  return map[props.tone] || map.default
})
</script>

<template>
  <!--
    复用 CyberGlassCard 作为视觉容器（Requirement 4.8）。
    trendClass 通过 Vue 的属性穿透机制落到 CyberGlassCard 的根元素 .cyber-glass-card 上，
    满足 Property 5 对 trend-up / trend-down / trend-flat class 的可见性断言。
  -->
  <CyberGlassCard
    :variant="tone"
    headerless
    no-padding
    class="metric-card"
    :class="[trendClass, accentBarClass]"
  >
    <div class="metric-card__body">
      <!-- 第一行：label + 方向标记 -->
      <div class="metric-card__head">
        <span class="metric-card__label">{{ label }}</span>
        <span
          v-if="trend"
          class="metric-card__trend-icon"
          :class="trendIconColorClass"
          :aria-label="trendAriaLabel"
        >
          <component :is="trendIcon" class="w-4 h-4" aria-hidden="true" />
        </span>
      </div>

      <!-- 第二行：主数值 + 单位 -->
      <div class="metric-card__value-row">
        <span class="metric-card__value" :class="valueToneClass">{{ value }}</span>
        <span v-if="unit" class="metric-card__unit">{{ unit }}</span>
      </div>

      <!-- 默认 slot：自定义图标 / 副文案 -->
      <div v-if="$slots.default" class="metric-card__slot">
        <slot />
      </div>
    </div>
  </CyberGlassCard>
</template>

<style scoped>
.metric-card {
  /* 容器尺寸由父布局决定；此处给最小高度保持三卡同高，避免单/双行内容差异导致塌陷 */
  min-height: 108px;
  height: 100%;
  position: relative;
  transition: transform 0.18s ease-out, box-shadow 0.2s ease-out;
}

/* hover 微抬起 + 轻光晕：让指标卡更像可交互的仪表盘单元 */
.metric-card:hover {
  transform: translateY(-1px);
}

/* 左侧仪表盘 accent 短条：通过 ::before 注入到 CyberGlassCard 根元素上 */
.metric-card::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 2px;
  opacity: 0.85;
  pointer-events: none;
}

.metric-card.metric-accent--purple::before  { background: linear-gradient(to bottom, #a855f7, transparent); box-shadow: 0 0 10px rgba(168,85,247,0.5); }
.metric-card.metric-accent--cyan::before    { background: linear-gradient(to bottom, #22d3ee, transparent); box-shadow: 0 0 10px rgba(34,211,238,0.5); }
.metric-card.metric-accent--pink::before    { background: linear-gradient(to bottom, #ec4899, transparent); box-shadow: 0 0 10px rgba(236,72,153,0.5); }
.metric-card.metric-accent--emerald::before { background: linear-gradient(to bottom, #10b981, transparent); box-shadow: 0 0 10px rgba(16,185,129,0.5); }

.metric-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px 14px 22px;
  height: 100%;
}

.metric-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-card__label {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: rgba(203, 213, 225, 0.85);
  text-transform: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-card__trend-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.20);
  flex-shrink: 0;
}

.metric-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 2px;
}

.metric-card__value {
  font-size: 30px;
  line-height: 1.05;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  text-shadow: 0 0 12px rgba(139, 92, 246, 0.25);
}

.metric-card__unit {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.7);
  font-weight: 500;
  letter-spacing: 0.02em;
  /* 与主数值视觉层级拉开：单位更轻，避免和数值争夺注意力 */
  align-self: baseline;
  padding-bottom: 1px;
}

.metric-card__slot {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(148, 163, 184, 0.85);
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 方向标记色调强化（绿 / 红 / 灰）—— 当根元素带 trend-* class 时
   给数值与边框附加微弱方向色辉光，强化"上升 / 下降 / 持平"的视觉语义 */
.metric-card.trend-up .metric-card__value {
  text-shadow: 0 0 14px rgba(16, 185, 129, 0.35);
}
.metric-card.trend-down .metric-card__value {
  text-shadow: 0 0 14px rgba(239, 68, 68, 0.35);
}
.metric-card.trend-flat .metric-card__value {
  text-shadow: 0 0 10px rgba(148, 163, 184, 0.25);
}

/* prefers-reduced-motion 无障碍降级：保持视觉语义但去掉强辉光动效 */
@media (prefers-reduced-motion: reduce) {
  .metric-card { transition: none; }
  .metric-card:hover { transform: none; }
  .metric-card .metric-card__value,
  .metric-card.trend-up .metric-card__value,
  .metric-card.trend-down .metric-card__value,
  .metric-card.trend-flat .metric-card__value {
    text-shadow: none;
  }
}
</style>
