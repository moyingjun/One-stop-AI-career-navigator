<script setup>
/**
 * CareerPreviewPanel.vue — 职业规划快速预览浮窗（v2，支持上一条/下一条翻阅）
 *
 * 右侧滑入浮窗，展示职业规划记录概要。
 *
 * Props 契约：
 *   - visible:      Boolean
 *   - records:      Array  — 职业规划记录列表
 *   - initialIndex: Number — 初始定位的记录索引
 *
 * 内部状态：
 *   - currentIndex: 当前展示的记录索引
 *   - currentRecord: computed，当前记录引用
 *
 * Emits:
 *   - close
 *   - go-full(recordId | null)
 */
import { ref, computed, watch } from 'vue'
import { X, Compass, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { marked } from 'marked'
import { formatRecordTime } from '@/utils/dateFormat.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  records: { type: Array, default: () => [] },
  initialIndex: { type: Number, default: 0 }
})

const emit = defineEmits(['close', 'go-full'])

const currentIndex = ref(0)

// 浮窗打开时，按 initialIndex 重置当前索引
watch(() => props.visible, (v) => {
  if (v) {
    const safeIdx = Math.max(0, Math.min(props.initialIndex || 0, (props.records?.length || 1) - 1))
    currentIndex.value = safeIdx
  }
})

watch(() => props.initialIndex, (idx) => {
  if (props.visible) {
    const safeIdx = Math.max(0, Math.min(idx || 0, (props.records?.length || 1) - 1))
    currentIndex.value = safeIdx
  }
})

const currentRecord = computed(() => props.records?.[currentIndex.value] || null)

const renderedContent = computed(() => {
  const rec = currentRecord.value
  if (!rec) return ''
  const raw = typeof rec.ai_result === 'string'
    ? rec.ai_result
    : (typeof rec.content === 'string' ? rec.content : '')
  if (!raw) return ''
  return marked.parse(raw.slice(0, 8000))
})

const recordTime = computed(() => formatRecordTime(currentRecord.value))

const totalCount = computed(() => props.records?.length || 0)
const canPrev = computed(() => currentIndex.value > 0)
const canNext = computed(() => currentIndex.value < totalCount.value - 1)

function goPrev() {
  if (canPrev.value) currentIndex.value -= 1
}

function goNext() {
  if (canNext.value) currentIndex.value += 1
}

function handleGoFull() {
  const rec = currentRecord.value
  emit('go-full', rec?.id || null)
}
</script>

<template>
  <Teleport to="body">
    <transition name="panel-slide">
      <div
        v-if="visible"
        class="fixed right-4 top-20 w-[380px] max-h-[72vh] z-[90] flex flex-col rounded-2xl border border-white/10 bg-[#0a0f1a]/92 backdrop-blur-2xl shadow-[0_0_50px_rgba(0,0,0,0.6),0_0_20px_rgba(6,182,212,0.08)]"
      >
        <!-- 标题栏 -->
        <div class="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.06] flex-shrink-0">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center flex-shrink-0">
              <Compass class="w-4 h-4 text-cyan-300" />
            </div>
            <div class="min-w-0">
              <h3 class="text-sm font-semibold text-gray-100">职业规划概要</h3>
              <p v-if="recordTime" class="text-[10px] text-gray-500 mt-0.5 truncate">{{ recordTime }}</p>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="w-7 h-7 rounded-md flex items-center justify-center border border-white/10 bg-white/[0.03] text-gray-400 hover:text-white hover:border-white/20 hover:bg-white/[0.06] transition-all duration-200 flex-shrink-0"
            aria-label="关闭"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- 翻阅控制条 -->
        <div
          v-if="totalCount > 1"
          class="flex items-center justify-between px-5 py-2 border-b border-white/[0.04] bg-white/[0.01]"
        >
          <button
            @click="goPrev"
            :disabled="!canPrev"
            class="flex items-center gap-1 px-2 py-1 rounded-md text-xs border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
            :class="canPrev
              ? 'border-cyan-500/25 text-cyan-300 hover:bg-cyan-500/10 hover:border-cyan-400/50'
              : 'border-white/10 text-gray-500'"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
            上一条
          </button>
          <span class="text-xs text-gray-400 font-mono">
            {{ currentIndex + 1 }} / {{ totalCount }}
          </span>
          <button
            @click="goNext"
            :disabled="!canNext"
            class="flex items-center gap-1 px-2 py-1 rounded-md text-xs border transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
            :class="canNext
              ? 'border-cyan-500/25 text-cyan-300 hover:bg-cyan-500/10 hover:border-cyan-400/50'
              : 'border-white/10 text-gray-500'"
          >
            下一条
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
          <div
            v-if="renderedContent"
            class="dashboard-markdown text-sm leading-relaxed"
            v-html="renderedContent"
          ></div>
          <div v-else class="flex flex-col items-center justify-center py-10 text-center">
            <Compass class="w-10 h-10 text-gray-600 mb-3" />
            <p class="text-xs text-gray-500">暂无规划内容</p>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="flex-shrink-0 px-5 py-3 border-t border-white/[0.06]">
          <button
            @click="handleGoFull"
            class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-cyan-500/30 bg-cyan-500/[0.06] text-cyan-300 text-xs font-medium hover:bg-cyan-500/15 hover:border-cyan-400/50 hover:shadow-[0_0_18px_rgba(6,182,212,0.2)] transition-all duration-300"
          >
            <ExternalLink class="w-3.5 h-3.5" />
            查看完整功能页
          </button>
        </div>
      </div>
    </transition>

    <!-- 背景遮罩 -->
    <transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[89] bg-black/30 backdrop-blur-[2px]"
        @click="emit('close')"
      ></div>
    </transition>
  </Teleport>
</template>

<style scoped>
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.24s ease;
}
.panel-slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.panel-slide-leave-to {
  transform: translateX(60%);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.22s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(6, 182, 212, 0.4); }

.dashboard-markdown :deep(h1) { font-size: 1.2em; font-weight: 700; margin: 0.5em 0 0.3em; color: #67e8f9; }
.dashboard-markdown :deep(h2) { font-size: 1.1em; font-weight: 600; margin: 0.4em 0 0.2em; color: #22d3ee; }
.dashboard-markdown :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 0.3em 0 0.15em; color: #06b6d4; }
.dashboard-markdown :deep(strong), .dashboard-markdown :deep(b) { color: #67e8f9; font-weight: 700; }
.dashboard-markdown :deep(p) { margin: 0.2em 0; color: rgba(229, 231, 235, 0.9); }
.dashboard-markdown :deep(ul), .dashboard-markdown :deep(ol) { padding-left: 1.2em; margin: 0.2em 0; }
.dashboard-markdown :deep(li) { margin: 0.1em 0; color: rgba(229, 231, 235, 0.85); }
.dashboard-markdown :deep(li)::marker { color: #06b6d4; }
.dashboard-markdown :deep(blockquote) { border-left: 3px solid rgba(6, 182, 212, 0.35); padding: 0.2em 0.6em; margin: 0.3em 0; background: rgba(6, 182, 212, 0.04); border-radius: 0 6px 6px 0; color: rgba(229, 231, 235, 0.7); }
.dashboard-markdown :deep(code) { background: rgba(6, 182, 212, 0.1); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.88em; color: #67e8f9; }
.dashboard-markdown :deep(pre) { background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(6, 182, 212, 0.12); border-radius: 8px; padding: 0.6em; overflow-x: auto; margin: 0.3em 0; }
.dashboard-markdown :deep(pre code) { background: none; padding: 0; border-radius: 0; color: rgba(229, 231, 235, 0.85); }
</style>
