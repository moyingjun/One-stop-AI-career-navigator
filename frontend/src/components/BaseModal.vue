<script setup>
/**
 * BaseModal — 全项目通用弹窗基类
 * 所有弹窗必须基于此组件扩展，通过 slot 注入内容。
 * 视觉规范：暗黑赛博毛玻璃（Dark Cyberpunk + Glassmorphism）
 * 紫青渐变边框 + backdrop-filter 毛玻璃 + 极暗深色背景
 */
defineProps({
  /** 控制弹窗显隐 */
  modelValue: {
    type: Boolean,
    default: false
  },
  /** 弹窗最大宽度，Tailwind max-w-* 类名，默认 max-w-2xl */
  maxWidth: {
    type: String,
    default: 'max-w-2xl'
  },
  /** 点击遮罩层是否关闭弹窗 */
  closeOnOverlay: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const handleOverlayClick = (props) => {
  if (props.closeOnOverlay) {
    emit('update:modelValue', false)
    emit('close')
  }
}

const handleClose = () => {
  emit('update:modelValue', false)
  emit('close')
}
</script>

<script>
// 允许 defineProps 在 setup 中访问
export default { inheritAttrs: false }
</script>

<template>
  <Teleport to="body">
    <Transition name="base-modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
      >
        <!-- 遮罩层 -->
        <div
          class="absolute inset-0 bg-black/70 backdrop-blur-sm"
          @click="handleOverlayClick({ closeOnOverlay })"
        />

        <!-- 弹窗主体 -->
        <div
          class="relative w-full rounded-2xl overflow-hidden"
          :class="maxWidth"
        >
          <!-- 渐变边框容器（伪元素替代方案，用 padding + 内层背景实现） -->
          <div class="base-modal-border-wrap rounded-2xl p-px">
            <div class="relative rounded-2xl bg-[#07090f]/92 backdrop-blur-2xl shadow-[0_0_60px_rgba(0,0,0,0.8),inset_0_0_30px_rgba(255,255,255,0.02)]">

              <!-- 顶部扫描线装饰 -->
              <div class="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent pointer-events-none" />

              <!-- 关闭按钮 -->
              <button
                class="absolute top-4 right-4 z-10 w-8 h-8 rounded-lg border border-white/10 bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:border-cyan-400/40 hover:bg-cyan-500/10 hover:shadow-[0_0_12px_rgba(34,211,238,0.2)] transition-all duration-200"
                aria-label="关闭"
                @click="handleClose"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>

              <!-- 内容插槽 -->
              <slot />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 紫青渐变边框 */
.base-modal-border-wrap {
  background: linear-gradient(
    135deg,
    rgba(168, 85, 247, 0.5) 0%,
    rgba(99, 102, 241, 0.3) 30%,
    rgba(6, 182, 212, 0.4) 70%,
    rgba(168, 85, 247, 0.3) 100%
  );
  box-shadow:
    0 0 40px rgba(168, 85, 247, 0.15),
    0 0 80px rgba(6, 182, 212, 0.08);
}

/* 进入/离开动画 */
.base-modal-enter-active,
.base-modal-leave-active {
  transition: opacity 0.25s ease;
}
.base-modal-enter-active .base-modal-border-wrap,
.base-modal-leave-active .base-modal-border-wrap {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.base-modal-enter-from,
.base-modal-leave-to {
  opacity: 0;
}
.base-modal-enter-from .base-modal-border-wrap {
  transform: scale(0.94) translateY(8px);
}
.base-modal-leave-to .base-modal-border-wrap {
  transform: scale(0.96) translateY(4px);
}
</style>
