<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  variant: { type: String, default: 'default' },
  noPadding: { type: Boolean, default: false },
  headerless: { type: Boolean, default: false }
})

const VARIANT_MAP = {
  default: {
    borderColor: 'rgba(139, 92, 246, 0.2)',
    glowColor: 'rgba(139, 92, 246, 0.08)',
    gradientFrom: 'rgba(139, 92, 246, 0.6)',
    gradientTo: 'rgba(6, 182, 212, 0.6)',
    iconColor: 'text-purple-400',
    titleColor: 'text-purple-200',
    cornerColor: 'rgba(139, 92, 246, 0.5)'
  },
  cyan: {
    borderColor: 'rgba(6, 182, 212, 0.2)',
    glowColor: 'rgba(6, 182, 212, 0.08)',
    gradientFrom: 'rgba(6, 182, 212, 0.6)',
    gradientTo: 'rgba(59, 130, 246, 0.6)',
    iconColor: 'text-cyan-400',
    titleColor: 'text-cyan-200',
    cornerColor: 'rgba(6, 182, 212, 0.5)'
  },
  purple: {
    borderColor: 'rgba(139, 92, 246, 0.2)',
    glowColor: 'rgba(139, 92, 246, 0.08)',
    gradientFrom: 'rgba(168, 85, 247, 0.6)',
    gradientTo: 'rgba(139, 92, 246, 0.6)',
    iconColor: 'text-purple-400',
    titleColor: 'text-purple-200',
    cornerColor: 'rgba(168, 85, 247, 0.5)'
  },
  pink: {
    borderColor: 'rgba(236, 72, 153, 0.2)',
    glowColor: 'rgba(236, 72, 153, 0.08)',
    gradientFrom: 'rgba(236, 72, 153, 0.6)',
    gradientTo: 'rgba(232, 121, 249, 0.6)',
    iconColor: 'text-pink-400',
    titleColor: 'text-pink-200',
    cornerColor: 'rgba(236, 72, 153, 0.5)'
  },
  emerald: {
    borderColor: 'rgba(16, 185, 129, 0.2)',
    glowColor: 'rgba(16, 185, 129, 0.08)',
    gradientFrom: 'rgba(16, 185, 129, 0.6)',
    gradientTo: 'rgba(6, 182, 212, 0.6)',
    iconColor: 'text-emerald-400',
    titleColor: 'text-emerald-200',
    cornerColor: 'rgba(16, 185, 129, 0.5)'
  }
}

const variantConfig = computed(() => {
  return VARIANT_MAP[props.variant] || VARIANT_MAP.default
})

const variantClasses = computed(() => {
  const map = {
    default: 'cyber-card--default',
    cyan: 'cyber-card--cyan',
    purple: 'cyber-card--purple',
    pink: 'cyber-card--pink',
    emerald: 'cyber-card--emerald'
  }
  return map[props.variant] || map.default
})

const containerStyle = computed(() => ({
  '--cgc-border-color': variantConfig.value.borderColor,
  '--cgc-glow-color': variantConfig.value.glowColor,
  '--cgc-gradient-from': variantConfig.value.gradientFrom,
  '--cgc-gradient-to': variantConfig.value.gradientTo,
  '--cgc-corner-color': variantConfig.value.cornerColor
}))
</script>

<template>
  <div class="cyber-glass-card" :style="containerStyle">
    <!-- 边框流光伪元素由 CSS ::before 实现 -->
    <div class="cyber-glass-card__inner">
      <!-- Header -->
      <div v-if="!headerless" class="cyber-glass-card__header">
        <slot name="header">
          <div class="flex items-center gap-2">
            <component v-if="icon" :is="icon" class="w-5 h-5" :class="variantConfig.iconColor" />
            <h3 v-if="title" class="text-sm font-bold" :class="variantConfig.titleColor">{{ title }}</h3>
          </div>
        </slot>
      </div>

      <!-- Corner slot -->
      <div v-if="$slots.corner" class="cyber-glass-card__corner">
        <slot name="corner" />
      </div>

      <!-- Content -->
      <div class="cyber-glass-card__content" :class="{ 'p-0': noPadding, 'p-4': !noPadding }">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.cyber-glass-card {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  isolation: isolate;
  box-shadow: 0 0 20px var(--cgc-glow-color), 0 4px 30px rgba(0, 0, 0, 0.3);
  transition: box-shadow 300ms ease-out;
}

.cyber-glass-card:hover {
  box-shadow: 0 0 40px var(--cgc-glow-color), 0 0 60px var(--cgc-glow-color), 0 4px 30px rgba(0, 0, 0, 0.4);
}

/* 边框流光动画 - conic-gradient 旋转 */
.cyber-glass-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 17px;
  padding: 1px;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    transparent 60deg,
    var(--cgc-gradient-from) 120deg,
    var(--cgc-gradient-to) 180deg,
    transparent 240deg,
    transparent 360deg
  );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: borderGlow 4s linear infinite;
  will-change: transform;
  transform: translateZ(0);
  opacity: 0.6;
  transition: animation-duration 300ms ease-out, opacity 300ms ease-out;
}

.cyber-glass-card:hover::before {
  animation-duration: 2s;
  opacity: 0.9;
}

@keyframes borderGlow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 内层毛玻璃容器 */
.cyber-glass-card__inner {
  position: relative;
  z-index: 1;
  border-radius: 16px;
  background: rgba(10, 10, 20, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--cgc-border-color);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.cyber-glass-card__header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--cgc-border-color);
  flex-shrink: 0;
}

/* Corner 角标 */
.cyber-glass-card__corner {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--cgc-corner-color);
  background: rgba(0, 0, 0, 0.4);
}

/* Content */
.cyber-glass-card__content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* 自定义滚动条 */
.cyber-glass-card__content::-webkit-scrollbar {
  width: 5px;
}
.cyber-glass-card__content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}
.cyber-glass-card__content::-webkit-scrollbar-thumb {
  background: var(--cgc-gradient-from);
  opacity: 0.4;
  border-radius: 3px;
}

/* 响应式 */
@media (max-width: 767px) {
  .cyber-glass-card {
    border-radius: 12px;
    width: 100%;
  }
  .cyber-glass-card::before {
    border-radius: 13px;
  }
  .cyber-glass-card__inner {
    border-radius: 12px;
  }
}

/* prefers-reduced-motion 无障碍降级 */
@media (prefers-reduced-motion: reduce) {
  .cyber-glass-card::before {
    animation: none;
    opacity: 0.3;
  }
  .cyber-glass-card:hover::before {
    animation: none;
    opacity: 0.3;
  }
  .cyber-glass-card {
    transition: none;
  }
  .cyber-glass-card:hover {
    box-shadow: 0 0 20px var(--cgc-glow-color), 0 4px 30px rgba(0, 0, 0, 0.3);
  }
}
</style>
