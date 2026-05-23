<script setup>
/**
 * StreamingLoader.vue —— 全项目统一 SSE 流式等待 / AI 思考中加载态。
 *
 * 这是 Vite dep scan 过去找不到的"占位组件"恢复版本。
 * 与 `@/utils/uiFallbacks.js` 的 InlineLoaderFallback 视觉同源、Props 一致，
 * 让 resolveLoader() 优先解析到本组件而不是降级版。
 *
 * Props 契约（必须与 InlineLoaderFallback 保持一致，调用方仅传 label）：
 *   - label: string，默认 'AI 思考中…'
 *
 * 视觉：暗黑赛博毛玻璃卡片 + cyan→purple 渐变流光圆点 + 文案。
 * 不引入新依赖，仅使用 Tailwind 4 + 既有色调。
 */
defineProps({
  label: { type: String, default: 'AI 思考中…' }
})
</script>

<template>
  <div
    role="status"
    aria-live="polite"
    class="streaming-loader relative inline-flex items-center gap-3 px-5 py-3 rounded-2xl border border-cyan-400/20 bg-[#0a0a14]/60 backdrop-blur-xl shadow-[0_0_24px_rgba(6,182,212,0.18)]"
  >
    <span
      class="streaming-loader__dot inline-block w-3 h-3 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500"
      aria-hidden="true"
    ></span>
    <span class="streaming-loader__label text-sm font-medium text-cyan-100">
      {{ label }}
    </span>
  </div>
</template>

<style scoped>
.streaming-loader__dot {
  animation: streaming-loader-pulse 1.4s ease-in-out infinite;
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.55);
}
@keyframes streaming-loader-pulse {
  0%, 100% { transform: scale(1); opacity: 0.85; }
  50%      { transform: scale(1.25); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .streaming-loader__dot { animation: none; }
}
</style>
