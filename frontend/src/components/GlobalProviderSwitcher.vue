<script setup>
/**
 * GlobalProviderSwitcher.vue —— 全局 AI Provider 切换徽章 + 下拉
 *
 * 职责：
 *   - 在 Dashboard / 三功能页（ResumeDiagnosis / CareerPlanning / PremiumInterview）顶部
 *     统一展示当前 LLM Provider（Online 徽章），支持点击展开下拉切换。
 *   - 复用 llmProviderStore 中的 providers / currentProviderId / currentDisplayLabel。
 *   - 切换 Provider 不会清空当前对话，仅影响下一次请求。
 *
 * 关键实现要点：
 *   - 下拉菜单使用 <Teleport to="body"> 渲染到 document.body，规避父容器
 *     overflow-hidden / transform / backdrop-filter 形成的 stacking context 截断。
 *   - 位置基于 trigger.getBoundingClientRect() 计算（fixed 定位）。
 *   - 滚动 / resize 自动关闭，避免位置脱钩。
 *   - 下拉本身不设全屏遮罩；它只是一个轻量浮层，不是 Modal。
 *
 * 严格约束：
 *   - 不直接调用 fetch / EventSource / axios，不出现 /api/... 字面量
 *   - 不持有任何业务状态，所有 Provider 数据来源于 llmProviderStore
 *   - Placeholder（占位）Provider 永远不可选中、不会写入 localStorage
 *   - API Key 永不出现在前端（依赖后端 / store 已做白名单脱敏）
 *
 * 视觉：暗黑赛博毛玻璃；emerald 主色（Online）；gray 表示 Standby / Unconfigured。
 */
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useLlmProviderStore } from '@/stores/llmProviderStore'
import { showToast } from '@/utils/uiFallbacks.js'

const props = defineProps({
  /** 紧凑模式：徽章更小 */
  compact: { type: Boolean, default: false },
  /** 是否显示徽章上的文本标签（"MiMo 2.5 Online" / "DeepSeek V4 Online"） */
  showLabel: { type: Boolean, default: true },
  /** 下拉对齐方向：'bottom-right' | 'bottom-left' */
  placement: {
    type: String,
    default: 'bottom-right',
    validator: (v) => ['bottom-right', 'bottom-left'].includes(v)
  },
  /**
   * 状态文本覆盖（用于 PremiumInterview 在 AI 思考时显示 "Thinking..."）。
   * 传入非空字符串时，徽章上的标签会被替换；不影响下拉内的真实选中状态。
   */
  statusOverride: { type: String, default: '' }
})

const llmProviderStore = useLlmProviderStore()

const open = ref(false)
const triggerRef = ref(null)
const dropdownRef = ref(null)

// 下拉位置（fixed 定位坐标，相对视口）
const dropdownPos = ref({ top: 0, left: 0 })
const DROPDOWN_WIDTH = 280  // 与下方模板 width 保持一致（w-[280px]）
const VIEWPORT_PADDING = 8  // 防止贴边

const displayLabel = computed(() => {
  if (props.statusOverride && props.statusOverride.trim()) return props.statusOverride
  return llmProviderStore.currentDisplayLabel
})

/** 判断 Provider 是否可选（必须 online 且非占位） */
const isSelectable = (p) => !!p && !p.is_placeholder && p.status === 'online'

/** Provider 状态徽标文本 */
const statusBadge = (provider) => {
  if (!provider) return ''
  if (llmProviderStore.currentProviderId === provider.id && isSelectable(provider)) return '当前'
  if (provider.is_placeholder || provider.status !== 'online') return '未配置'
  return 'Standby'
}

/** 计算下拉位置：基于 trigger 在视口中的位置 */
const computePosition = () => {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  const top = rect.bottom + 8  // 与 trigger 间距 8px

  let left
  if (props.placement === 'bottom-left') {
    left = rect.left
  } else {
    // bottom-right：菜单右边缘对齐 trigger 右边缘
    left = rect.right - DROPDOWN_WIDTH
  }

  // 防止溢出视口
  const maxLeft = window.innerWidth - DROPDOWN_WIDTH - VIEWPORT_PADDING
  if (left > maxLeft) left = maxLeft
  if (left < VIEWPORT_PADDING) left = VIEWPORT_PADDING

  dropdownPos.value = { top, left }
}

const openDropdown = async () => {
  open.value = true
  await nextTick()
  computePosition()
}

const closeDropdown = () => {
  open.value = false
}

const toggleDropdown = () => {
  if (open.value) closeDropdown()
  else openDropdown()
}

const handleSelect = (provider) => {
  if (!provider) return
  // Placeholder / 未配置 → toast 提示，不切换
  if (provider.is_placeholder || provider.status !== 'online') {
    showToast('该 AI 引擎尚未配置 API Key', { type: 'error', duration: 2500 })
    closeDropdown()
    return
  }
  // 已经是当前 Provider → 关闭下拉，不重复 toast
  if (llmProviderStore.currentProviderId === provider.id) {
    closeDropdown()
    return
  }
  const ok = llmProviderStore.setCurrentProvider(provider.id)
  if (ok) {
    showToast(`已切换 AI 引擎：${provider.display_name}`, { duration: 2000 })
  }
  closeDropdown()
}

// 点击下拉外部 / Esc 关闭
const handleOutside = (e) => {
  if (!open.value) return
  const inTrigger = triggerRef.value && triggerRef.value.contains(e.target)
  const inDropdown = dropdownRef.value && dropdownRef.value.contains(e.target)
  if (!inTrigger && !inDropdown) closeDropdown()
}

const handleKeydown = (e) => {
  if (e.key === 'Escape' && open.value) closeDropdown()
}

// 滚动 / resize：直接关闭，避免位置错位
const handleScrollOrResize = () => {
  if (open.value) closeDropdown()
}

onMounted(() => {
  document.addEventListener('mousedown', handleOutside)
  document.addEventListener('keydown', handleKeydown)
  // 用 capture 模式监听 scroll，可以接住任意嵌套滚动容器
  window.addEventListener('scroll', handleScrollOrResize, true)
  window.addEventListener('resize', handleScrollOrResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('scroll', handleScrollOrResize, true)
  window.removeEventListener('resize', handleScrollOrResize)
})
</script>

<template>
  <div class="global-provider-switcher relative inline-block">
    <!-- 顶部徽章：emerald 主色 + 脉冲圆点 + 下拉箭头 -->
    <button
      ref="triggerRef"
      type="button"
      @click="toggleDropdown"
      class="bg-emerald-500/10 backdrop-blur-md border border-emerald-500/30 rounded-full flex items-center gap-2 shadow-[0_0_10px_rgba(16,185,129,0.15)] hover:bg-emerald-500/15 hover:border-emerald-400/50 transition-all duration-200"
      :class="compact ? 'px-2.5 py-1' : 'px-3 py-1.5'"
      :title="displayLabel"
      data-test="global-provider-switcher-trigger"
    >
      <span
        class="rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"
        :class="compact ? 'w-1.5 h-1.5' : 'w-2 h-2'"
        aria-hidden="true"
      ></span>
      <span
        v-if="showLabel"
        class="text-emerald-400 font-mono font-semibold tracking-wider drop-shadow-[0_0_5px_rgba(52,211,153,0.4)] whitespace-nowrap"
        :class="compact ? 'text-[10px]' : 'text-xs'"
      >{{ displayLabel }}</span>
      <ChevronDown
        class="text-emerald-400/70 transition-transform duration-200"
        :class="[compact ? 'w-2.5 h-2.5' : 'w-3 h-3', open ? 'rotate-180' : '']"
      />
    </button>

    <!-- 下拉：Teleport 到 body 规避父容器 stacking context 截断 -->
    <Teleport to="body">
      <transition name="provider-fade">
        <div
          v-if="open"
          ref="dropdownRef"
          class="provider-switcher-dropdown fixed w-[280px] rounded-xl border border-emerald-500/25 bg-[#0a0f1a]/95 backdrop-blur-2xl shadow-[0_0_30px_rgba(0,0,0,0.6),0_0_15px_rgba(16,185,129,0.12)] overflow-hidden"
          :style="{ top: dropdownPos.top + 'px', left: dropdownPos.left + 'px' }"
          data-test="global-provider-switcher-dropdown"
          role="menu"
        >
          <div class="px-3 py-2 border-b border-white/[0.06]">
            <p class="text-[10px] text-gray-500 font-mono uppercase tracking-wider">AI 引擎切换</p>
          </div>

          <div class="py-1 max-h-[280px] overflow-y-auto provider-switcher-scroll">
            <button
              v-for="provider in llmProviderStore.providers"
              :key="provider.id"
              type="button"
              :disabled="!isSelectable(provider) && llmProviderStore.currentProviderId !== provider.id"
              @click="handleSelect(provider)"
              class="w-full px-3 py-2 flex items-start justify-between gap-2 transition-all duration-150 text-left disabled:opacity-40 disabled:cursor-not-allowed"
              :class="llmProviderStore.currentProviderId === provider.id
                ? 'bg-emerald-500/10 text-emerald-200'
                : 'text-gray-300 hover:bg-white/[0.04] hover:text-white'"
              :data-test="`provider-item-${provider.id}`"
              role="menuitem"
            >
              <div class="flex items-start gap-2 min-w-0 flex-1">
                <span
                  class="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5"
                  :class="isSelectable(provider)
                    ? (llmProviderStore.currentProviderId === provider.id
                        ? 'bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                        : 'bg-emerald-400/60')
                    : 'bg-gray-600'"
                  aria-hidden="true"
                ></span>
                <div class="min-w-0 flex-1">
                  <div class="text-xs font-medium truncate">{{ provider.display_name }}</div>
                  <div
                    v-if="provider.description"
                    class="text-[10px] text-gray-500 mt-0.5 leading-snug truncate"
                  >{{ provider.description }}</div>
                  <div class="text-[9px] text-gray-600 font-mono mt-0.5 truncate">{{ provider.model_name }}</div>
                </div>
              </div>
              <span
                class="text-[9px] px-1.5 py-0.5 rounded border flex-shrink-0 mt-0.5"
                :class="llmProviderStore.currentProviderId === provider.id && isSelectable(provider)
                  ? 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10'
                  : (provider.is_placeholder || provider.status !== 'online'
                      ? 'text-gray-500 border-gray-600/40 bg-gray-700/30'
                      : 'text-gray-400 border-gray-500/30 bg-gray-700/20')"
              >{{ statusBadge(provider) }}</span>
            </button>

            <div
              v-if="llmProviderStore.providers.length === 0"
              class="px-3 py-3 text-center text-xs text-gray-500"
            >
              暂无可用引擎
            </div>
          </div>

          <!-- 底部固定提示 -->
          <div class="px-3 py-2 border-t border-white/[0.06] bg-[#080d18]/60">
            <p class="text-[10px] text-gray-500 leading-relaxed">
              切换 AI 引擎不会清空当前对话，仅影响下一次回复。
            </p>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* Teleport 出去的元素不受 scoped 限制；
   这里只为 trigger 区域提供过渡，下拉本身的过渡靠全局非 scoped 选择器 */
</style>

<style>
/* 全局样式：Teleport 到 body 后，scoped 失效，统一用全局选择器 */
.provider-switcher-dropdown {
  /* 必须高于 Modal / Toast / FeaturePageShell ambient 等所有层级 */
  z-index: 9999;
}

.provider-fade-enter-active,
.provider-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.provider-fade-enter-from,
.provider-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 下拉内部滚动条美化（暗黑赛博风格） */
.provider-switcher-scroll::-webkit-scrollbar {
  width: 6px;
}
.provider-switcher-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.provider-switcher-scroll::-webkit-scrollbar-thumb {
  background: rgba(16, 185, 129, 0.25);
  border-radius: 3px;
}
.provider-switcher-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(16, 185, 129, 0.45);
}
</style>
