<script setup>
/**
 * CustomDropdown.vue
 * 深色赛博朋克风格自定义下拉菜单组件
 *
 * 职责：替换原生 <select>，提供与整体 Dark Cyberpunk + Glassmorphism 设计语言一致的下拉交互。
 * 支持外部点击关闭（onClickOutside）和 ESC 键关闭。
 *
 * 对应需求：Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { ChevronDown } from 'lucide-vue-next'

// ─── Props & Emits ────────────────────────────────────────────────────────────

const props = defineProps({
  /** v-model 绑定值，与 options 中某个 value 对应 */
  modelValue: {
    type: String,
    default: ''
  },
  /**
   * 选项列表，每项格式为 { value: string, label: string }
   * Requirements: 11.1, 11.8（空数组时显示空面板，不报错）
   */
  options: {
    type: Array,
    default: () => []
  },
  /** 未选中任何选项时显示的占位文字 */
  placeholder: {
    type: String,
    default: '请选择'
  }
})

const emit = defineEmits(['update:modelValue'])

// ─── 内部状态 ─────────────────────────────────────────────────────────────────

/** 控制下拉面板的显示/隐藏 */
const isOpen = ref(false)

/** 根元素 ref，用于 onClickOutside 检测外部点击 */
const dropdownRef = ref(null)

// ─── Computed ─────────────────────────────────────────────────────────────────

/**
 * 当前选中项的 label。
 * 若 modelValue 与某个 option.value 匹配则显示其 label，否则显示 placeholder。
 * Requirements: 11.6
 */
const displayLabel = computed(() => {
  if (!props.modelValue) return null
  const matched = props.options.find(opt => opt.value === props.modelValue)
  return matched ? matched.label : null
})

// ─── Actions ──────────────────────────────────────────────────────────────────

/**
 * 点击触发按钮时切换面板开关状态。
 * Requirements: 11.2
 */
function togglePanel() {
  isOpen.value = !isOpen.value
}

/**
 * 点击某个选项时：emit 新值并关闭面板。
 * Requirements: 11.5
 * @param {string} value - 选中选项的 value
 */
function selectOption(value) {
  emit('update:modelValue', value)
  isOpen.value = false
}

// ─── 外部点击关闭 ─────────────────────────────────────────────────────────────

/**
 * 使用 @vueuse/core 的 onClickOutside 检测点击组件外部区域，自动关闭面板。
 * Requirements: 11.3
 */
onClickOutside(dropdownRef, () => {
  isOpen.value = false
})

// ─── ESC 键关闭 ───────────────────────────────────────────────────────────────

/**
 * 处理键盘事件：按下 ESC 键时关闭下拉面板。
 * Requirements: 11.4
 * @param {KeyboardEvent} event
 */
function handleKeydown(event) {
  if (event.key === 'Escape') {
    isOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <!-- 外层容器，相对定位以便面板绝对定位 -->
  <div ref="dropdownRef" class="relative">

    <!-- 触发按钮 Requirements: 11.7 -->
    <button
      type="button"
      class="w-full flex items-center justify-between gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10 hover:border-white/20 focus:outline-none focus:border-white/30"
      :class="displayLabel ? 'text-gray-200' : 'text-gray-500'"
      @click="togglePanel"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
    >
      <!-- 当前选中标签或占位文字 -->
      <span class="truncate">{{ displayLabel ?? placeholder }}</span>

      <!-- 展开/收起箭头图标 -->
      <ChevronDown
        class="w-4 h-4 shrink-0 text-gray-400 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <!-- 下拉面板 Requirements: 11.7 -->
    <Transition name="dropdown">
      <div
        v-if="isOpen"
        class="absolute z-50 w-full mt-1 bg-gray-900 border border-white/10 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden"
        role="listbox"
      >
        <!-- 选项列表 -->
        <ul class="py-1 max-h-60 overflow-y-auto">

          <!-- 空状态：options 为空时显示空面板，不报错 Requirements: 11.8 -->
          <li
            v-if="options.length === 0"
            class="px-3 py-2 text-sm text-gray-500 text-center select-none"
          >
            暂无选项
          </li>

          <!-- 选项列表项 -->
          <li
            v-for="option in options"
            :key="option.value"
            class="flex items-center px-3 py-2 text-sm cursor-pointer transition-colors duration-150 hover:bg-white/5 hover:text-white"
            :class="modelValue === option.value
              ? 'text-purple-300 bg-purple-500/10'
              : 'text-gray-300'"
            role="option"
            :aria-selected="modelValue === option.value"
            @click="selectOption(option.value)"
          >
            {{ option.label }}
          </li>

        </ul>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* 下拉面板展开/收起过渡动画 Requirements: 11.7 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
  transform-origin: top;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.95) translateY(-4px);
}

/* 选项列表滚动条美化 */
ul::-webkit-scrollbar {
  width: 4px;
}
ul::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 2px;
}
ul::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
}
ul::-webkit-scrollbar-thumb:hover {
  background: rgba(168, 85, 247, 0.3);
}
</style>
