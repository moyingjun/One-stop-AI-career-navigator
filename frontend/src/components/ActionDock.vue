<script setup>
/**
 * ActionDock.vue
 *
 * 职责：聚合主操作 / 次操作按钮的「操作坞」。
 * - 内部复用 CyberGlassCard.vue（read-only 复用，不重新实现毛玻璃容器）。
 * - 通过具名插槽 `primary` / `secondary` 暴露主操作与次操作的注入点。
 * - 主 / 次操作渲染到两个清晰隔离的 DOM 容器中（Property 3：Slot 路由隔离）。
 * - `sticky=true` 时使用 position: sticky; bottom: 0 吸附到页面底部。
 *
 * 视觉风格：暗黑赛博毛玻璃（沿用 Dashboard.vue 同源视觉语言）。
 */
import { computed } from 'vue'
import CyberGlassCard from './CyberGlassCard.vue'

const props = defineProps({
  align: {
    type: String,
    default: 'right',
    validator: (v) => ['left', 'center', 'right'].includes(v)
  },
  sticky: {
    type: Boolean,
    default: false
  }
})

// flex 主轴对齐
const justifyClass = computed(() => {
  switch (props.align) {
    case 'left':
      return 'justify-start'
    case 'center':
      return 'justify-center'
    case 'right':
    default:
      return 'justify-end'
  }
})

// sticky 吸附时附加的根类
const rootClass = computed(() => [
  'action-dock',
  props.sticky ? 'action-dock--sticky' : ''
])
</script>

<template>
  <div :class="rootClass" data-test="action-dock">
    <CyberGlassCard headerless variant="default">
      <div class="action-dock__layout" :class="justifyClass">
        <!-- 次操作容器（可多个） -->
        <div
          class="action-dock__secondary"
          data-test="action-dock-secondary"
          role="group"
          aria-label="次操作"
        >
          <slot name="secondary" />
        </div>

        <!-- 主操作容器（通常 1 个） -->
        <div
          class="action-dock__primary"
          data-test="action-dock-primary"
          role="group"
          aria-label="主操作"
        >
          <slot name="primary" />
        </div>
      </div>
    </CyberGlassCard>
  </div>
</template>

<style scoped>
.action-dock {
  width: 100%;
  position: relative;
}

/* 吸附底部：position: sticky + bottom: 0 */
.action-dock--sticky {
  position: sticky;
  bottom: 0;
  z-index: 30;
  /* 让吸附时与下方内容有视觉间距 */
  padding-top: 4px;
  padding-bottom: 4px;
  /* 轻量背景渐隐，避免下方内容透出导致按钮可读性下降 */
  background: linear-gradient(
    to top,
    rgba(2, 2, 5, 0.92) 0%,
    rgba(2, 2, 5, 0.65) 55%,
    rgba(2, 2, 5, 0) 100%
  );
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  /* 二阶段：sticky 时顶部加一道紫青渐变高亮线，强化"操作坞"视觉层级 */
  border-top: 1px solid transparent;
  background-clip: padding-box;
}
.action-dock--sticky::before {
  content: '';
  position: absolute;
  top: 0;
  left: 8%;
  right: 8%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(168, 85, 247, 0.45) 30%,
    rgba(34, 211, 238, 0.55) 50%,
    rgba(168, 85, 247, 0.45) 70%,
    transparent 100%
  );
  box-shadow: 0 0 6px rgba(34, 211, 238, 0.15);
  pointer-events: none;
}

/* 主轴布局：次操作在左，主操作在右；通过 justify-content 控制整体对齐 */
.action-dock__layout {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
}

/* 次操作容器：横向排列，可包多个按钮 */
.action-dock__secondary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

/* 主操作容器：通常一个按钮 */
.action-dock__primary {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 当未提供 secondary slot 时，仍保留容器以满足 Property 3（路由隔离），
   但通过 :empty 移除其 gap 影响 */
.action-dock__secondary:empty,
.action-dock__primary:empty {
  display: none;
}

/* 响应式：窄屏改为纵向堆叠，主操作在下方更易点击 */
@media (max-width: 640px) {
  .action-dock__layout {
    flex-direction: column-reverse;
    align-items: stretch;
    justify-content: flex-start !important;
    gap: 10px;
  }
  .action-dock__secondary,
  .action-dock__primary {
    width: 100%;
    justify-content: center;
  }
  /* 移动端 sticky 时给主操作多一点呼吸空间 */
  .action-dock--sticky .action-dock__layout {
    gap: 8px;
  }
}
</style>
