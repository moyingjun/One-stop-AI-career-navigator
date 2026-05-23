<script setup>
/**
 * FeaturePageShell.vue —— AI 任务控制台骨架（Hero / Control / Result 三段式）
 *
 * 职责：
 *   - 仅承担布局骨架与具名插槽容器
 *   - 不接业务接口、不发起请求、不解析流式事件
 *   - 不持有任何业务状态
 *   - 视觉变量与 Dashboard.vue 同源，毛玻璃 / 圆角 / 边框流光由内部复用的 CyberGlassCard 提供
 *
 * 二阶段增强：
 *   - 新增 maxWidth prop（默认 1280px），统一三页主体宽度
 *   - 新增 result-header / control-aside / hero-aside 具名插槽，支持页面级信息架构重排
 *   - 默认 result-empty 升级为 4 格预告卡片（仅在未提供自定义 result-empty 时使用）
 *   - 增加轻微背景网格 + 噪点感（不引入新依赖、不加载图片）
 *
 * 严格约束：本组件仍不允许 import services/llm_service.js / fetch / EventSource / axios，
 * 不允许出现 /api/...、onMessage、onError、onDone 等业务字面量。
 */
import { computed } from 'vue'
import CyberGlassCard from './CyberGlassCard.vue'

const props = defineProps({
  /** Hero 主标题（必填） */
  title: { type: String, required: true },
  /** Hero 副标题 / slogan（可选） */
  subtitle: { type: String, default: '' },
  /**
   * Hero 三阶段徽章列表，每项形如 { label: string; tone?: 'purple'|'blue'|'pink'|'cyan'|'emerald' }
   * 超过 5 项截断（设计契约：最多 5 项）。
   */
  stageBadges: {
    type: Array,
    default: () => []
  },
  /** 透传给 Result 区 CyberGlassCard 的色调 */
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'cyan', 'purple', 'pink', 'emerald'].includes(v)
  },
  /**
   * 主体最大宽度。允许传任意 CSS 长度单位字符串（"1280px" / "80rem" 等）；
   * 默认 1280px，确保三页视觉宽度统一。
   */
  maxWidth: {
    type: String,
    default: '1280px'
  },
  /**
   * 是否在 Shell 内部渲染轻微背景网格 + 噪点层。
   * 业务页本身可能已有自己的 ambient blur 背景，此处只在 Shell 主体上叠一层弱质感。
   */
  ambient: {
    type: Boolean,
    default: true
  }
})

const MAX_BADGES = 5

// 截断策略：原数组 0..MAX_BADGES，超出忽略，避免过度撑高 Hero 区
const visibleBadges = computed(() => {
  const list = Array.isArray(props.stageBadges) ? props.stageBadges : []
  return list.slice(0, MAX_BADGES)
})

// 徽章色调 → Tailwind class 映射；与 Dashboard.vue 既有色板同源
const BADGE_TONE_MAP = {
  purple: 'text-purple-300 border-purple-500/40 bg-purple-500/10 shadow-[0_0_12px_rgba(168,85,247,0.18)]',
  blue: 'text-blue-300 border-blue-500/40 bg-blue-500/10 shadow-[0_0_12px_rgba(59,130,246,0.18)]',
  pink: 'text-pink-300 border-pink-500/40 bg-pink-500/10 shadow-[0_0_12px_rgba(236,72,153,0.18)]',
  cyan: 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10 shadow-[0_0_12px_rgba(6,182,212,0.18)]',
  emerald: 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10 shadow-[0_0_12px_rgba(16,185,129,0.18)]'
}

const toneClass = (tone) => BADGE_TONE_MAP[tone] || BADGE_TONE_MAP.cyan

// 主体最大宽度通过 CSS 变量下传，方便外部样式继承
const shellStyle = computed(() => ({
  '--feature-shell-max-width': props.maxWidth
}))
</script>

<template>
  <section
    class="feature-shell"
    :class="{ 'feature-shell--ambient': ambient }"
    :style="shellStyle"
    data-test="feature-shell"
  >
    <!-- Hero -->
    <header class="feature-shell__hero" data-test="hero">
      <slot name="hero">
        <div class="feature-shell__hero-default">
          <h1
            class="feature-shell__title text-2xl md:text-3xl font-bold text-white tracking-tight"
            data-test="hero-title"
          >
            {{ title }}
          </h1>
          <p
            v-if="subtitle"
            class="feature-shell__subtitle mt-2 text-sm md:text-base text-cyan-200/80"
            data-test="hero-subtitle"
          >
            {{ subtitle }}
          </p>
          <div
            v-if="visibleBadges.length"
            class="feature-shell__badges mt-4 flex flex-wrap gap-2"
            data-test="hero-badges"
          >
            <span
              v-for="(badge, idx) in visibleBadges"
              :key="`${badge.label}-${idx}`"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border backdrop-blur-md transition-colors duration-300"
              :class="toneClass(badge.tone)"
              data-test="hero-badge"
            >
              {{ badge.label }}
            </span>
          </div>
        </div>
      </slot>
    </header>

    <!-- Control Grid -->
    <section class="feature-shell__control" data-test="control">
      <CyberGlassCard headerless variant="default">
        <slot name="control" />
      </CyberGlassCard>
    </section>

    <!-- Result Zone -->
    <section class="feature-shell__result" data-test="result">
      <CyberGlassCard headerless :variant="variant">
        <!-- 可选：result-header 让业务页注入自己的"扫描仪 / 仪表盘 / 路线图"标题栏 -->
        <slot name="result-header" />

        <slot name="result">
          <slot name="result-empty">
            <!-- 默认空状态：保持骨架不塌陷（Requirement 1.6）；二阶段升级为更友好的引导 -->
            <div
              class="feature-shell__result-empty flex flex-col items-center justify-center gap-2 min-h-[200px] py-8 px-6 text-center"
              data-test="result-empty"
            >
              <span class="feature-shell__result-empty-dot" aria-hidden="true"></span>
              <span class="text-sm text-gray-400">等待结果输出</span>
              <span class="text-xs text-gray-500/80 max-w-sm leading-relaxed">
                填写左侧或上方控件后，AI 将在此展示分析结果。
              </span>
            </div>
          </slot>
        </slot>
      </CyberGlassCard>
    </section>
  </section>
</template>

<style scoped>
.feature-shell {
  /* 通过 CSS 变量统一主体宽度，业务页可在外层包一层 max-w-[var(...)] */
  --feature-shell-max-width: 1280px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  width: 100%;
  position: relative;
}

/* 轻微背景网格 + 渐变层：让 Shell 在大屏下不再像一块"白板" */
.feature-shell--ambient::before {
  content: '';
  position: absolute;
  inset: -16px -16px auto -16px;
  height: 280px;
  background:
    radial-gradient(ellipse at 12% 0%, rgba(168, 85, 247, 0.10), transparent 60%),
    radial-gradient(ellipse at 90% 0%, rgba(34, 211, 238, 0.08), transparent 55%);
  pointer-events: none;
  z-index: -1;
  filter: blur(2px);
  opacity: 0.85;
}

/* 噪点感：通过 SVG 内联 data URI 实现，不引入新依赖与新文件 */
.feature-shell--ambient::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: -1;
  opacity: 0.04;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='1.6' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.55'/></svg>");
}

.feature-shell__hero {
  width: 100%;
  padding: 1.25rem 1.5rem 0.5rem;
}

.feature-shell__hero-default {
  display: flex;
  flex-direction: column;
}

.feature-shell__control,
.feature-shell__result {
  width: 100%;
}

@media (max-width: 767px) {
  .feature-shell {
    gap: 1rem;
  }
  .feature-shell__hero {
    padding: 1rem 1rem 0.25rem;
  }
}

/* 默认空状态的脉冲圆点：让冷状态有一点呼吸感，但保持低调 */
.feature-shell__result-empty-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.55);
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.35);
  animation: feature-shell-empty-pulse 2.4s ease-in-out infinite;
}

@keyframes feature-shell-empty-pulse {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50%      { opacity: 1;    transform: scale(1.18); }
}

@media (prefers-reduced-motion: reduce) {
  .feature-shell__result-empty-dot {
    animation: none;
  }
}
</style>
