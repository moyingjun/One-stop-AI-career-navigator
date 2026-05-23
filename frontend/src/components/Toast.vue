<script setup>
/**
 * Toast.vue —— 全项目统一轻提示组件。
 *
 * 这是 Vite dep scan 过去找不到的"占位组件"恢复版本。
 * 与 `@/utils/uiFallbacks.js` 的 InlineToastFallback 视觉同源、Props 一致，
 * 让 resolveToast() 优先解析到本组件而不是降级版。
 *
 * Props 契约（必须与 InlineToastFallback 保持一致）：
 *   - message: string  必填
 *   - type:    'success' | 'error'  默认 'success'
 *   - duration: number  默认 3000ms
 *
 * 行为：在 duration 毫秒后自身淡出（emit('dismiss') 通知外层卸载）。
 * 真正的 DOM 卸载由 showToast() 的命令式挂载逻辑负责，组件本身只切换 visible。
 */
import { ref, onMounted } from 'vue'

const props = defineProps({
  message: { type: String, required: true },
  type: { type: String, default: 'success' },
  duration: { type: Number, default: 3000 }
})
const emit = defineEmits(['dismiss'])

const visible = ref(true)

onMounted(() => {
  setTimeout(() => {
    visible.value = false
    emit('dismiss')
  }, props.duration)
})
</script>

<template>
  <div
    v-if="visible"
    role="status"
    aria-live="polite"
    class="cyber-toast fixed top-5 left-1/2 -translate-x-1/2 z-[120] px-4 py-2.5 rounded-full border backdrop-blur-2xl text-sm flex items-center gap-2"
    :class="type === 'error'
      ? 'cyber-toast--error border-red-400/30 bg-[#1a0808]/85 text-red-100 shadow-[0_0_28px_rgba(239,68,68,0.20)]'
      : 'cyber-toast--success border-cyan-400/30 bg-[#0b1020]/85 text-cyan-100 shadow-[0_0_28px_rgba(6,182,212,0.18)]'"
  >
    <span
      class="cyber-toast__dot w-1.5 h-1.5 rounded-full"
      :class="type === 'error' ? 'bg-red-400' : 'bg-cyan-400'"
      aria-hidden="true"
    ></span>
    <span class="cyber-toast__msg">{{ message }}</span>
  </div>
</template>

<style scoped>
.cyber-toast {
  animation: cyber-toast-in 220ms ease-out;
}
@keyframes cyber-toast-in {
  from { opacity: 0; transform: translate(-50%, -8px); }
  to   { opacity: 1; transform: translate(-50%, 0); }
}
.cyber-toast__dot {
  box-shadow: 0 0 8px currentColor;
}
@media (prefers-reduced-motion: reduce) {
  .cyber-toast { animation: none; }
}
</style>
