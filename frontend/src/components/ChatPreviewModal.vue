<script setup>
/**
 * ChatPreviewModal.vue — Agent 对话历史预览弹窗
 *
 * 功能：
 *   - 接收 visible 和 recordId props
 *   - visible 变为 true 且 recordId 为正整数时自动 fetch /api/history/{recordId}
 *   - 渲染气泡对话列表（用户消息右对齐紫色，AI 消息左对齐深色）
 *   - "✨ 载入上下文并继续对话"按钮：emit load-context 并 emit close
 *   - fetch 失败时显示错误消息 + 重试按钮 + 关闭按钮，不向父组件传播错误
 *   - chat_history 为空时显示空状态提示
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.7, 13.8
 */

import { ref, watch } from 'vue'
import { getAuthHeaders } from '@/services/authService.js'
import { Loader2, X, MessageSquare, RefreshCw, Sparkles } from 'lucide-vue-next'

// ─────────────────────────────────────────────
// Props & Emits
// ─────────────────────────────────────────────

const props = defineProps({
  /** 控制弹窗显示/隐藏 */
  visible: {
    type: Boolean,
    required: true
  },
  /** 要预览的历史记录 ID（正整数） */
  recordId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['close', 'load-context'])

// ─────────────────────────────────────────────
// 内部状态
// ─────────────────────────────────────────────

/** 从 API 加载的对话历史消息列表 */
const chatHistory = ref([])

/** 加载状态指示器 */
const isLoading = ref(false)

/** 错误提示文字（空字符串表示无错误） */
const errorMessage = ref('')

// ─────────────────────────────────────────────
// API 基础路径
// ─────────────────────────────────────────────

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

// ─────────────────────────────────────────────
// 核心方法
// ─────────────────────────────────────────────

/**
 * 从后端拉取指定 recordId 的历史记录，解析 chat_history 字段。
 * 失败时设置 errorMessage，不向父组件抛出异常（Requirements 13.7）。
 *
 * @param {number} id - 历史记录 ID（正整数）
 */
async function fetchChatHistory(id) {
  isLoading.value = true
  errorMessage.value = ''
  chatHistory.value = []

  try {
    const response = await fetch(`${API_BASE_URL}/history/${id}`, {
      headers: { ...getAuthHeaders() }
    })

    if (!response.ok) {
      // HTTP 错误：显示错误消息，不抛出（Requirements 13.7）
      let detail = `请求失败（HTTP ${response.status}）`
      try {
        const body = await response.json()
        if (body && body.detail) detail = body.detail
      } catch {
        // 响应体非 JSON，保留默认 detail
      }
      errorMessage.value = detail
      return
    }

    const record = await response.json()

    // 解析 chat_history（后端可能返回 JSON 字符串或数组）
    let history = record.chat_history
    if (typeof history === 'string') {
      try {
        history = JSON.parse(history)
      } catch {
        history = []
      }
    }

    chatHistory.value = Array.isArray(history) ? history : []
  } catch (networkError) {
    // 网络层错误（断网、CORS 等）：显示错误消息，不向父组件传播（Requirements 13.7）
    errorMessage.value = '网络连接失败，请检查网络后重试'
    console.error('ChatPreviewModal: fetch 失败', networkError)
  } finally {
    isLoading.value = false
  }
}

/**
 * 重试：重新触发 fetch（Requirements 13.7）
 */
function handleRetry() {
  if (props.recordId && props.recordId > 0) {
    fetchChatHistory(props.recordId)
  }
}

/**
 * 点击"✨ 载入上下文并继续对话"按钮：
 * emit load-context 携带消息列表和 recordId，然后 emit close（Requirements 13.4）
 */
function handleLoadContext() {
  emit('load-context', {
    messages: chatHistory.value,
    recordId: props.recordId
  })
  emit('close')
}

/**
 * 关闭弹窗：emit close（Requirements 13.6）
 */
function handleClose() {
  emit('close')
}

// ─────────────────────────────────────────────
// 响应式监听：visible + recordId 变化时自动 fetch
// ─────────────────────────────────────────────

/**
 * 当 visible 变为 true 且 recordId 为正整数时，自动触发 fetch（Requirements 13.2）
 */
watch(
  () => [props.visible, props.recordId],
  ([newVisible, newRecordId]) => {
    if (newVisible && typeof newRecordId === 'number' && newRecordId > 0) {
      fetchChatHistory(newRecordId)
    } else if (!newVisible) {
      // 弹窗关闭时重置内部状态，避免下次打开时闪现旧数据
      chatHistory.value = []
      errorMessage.value = ''
      isLoading.value = false
    }
  },
  { immediate: true }
)
</script>

<template>
  <!-- 使用 Teleport 将弹窗挂载到 body，避免 z-index 层叠问题 -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[150] flex items-center justify-center px-4 bg-black/70 backdrop-blur-sm"
        @click.self="handleClose"
      >
        <!-- 弹窗主体：深色赛博朋克 + 玻璃拟态风格 -->
        <div
          class="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-white/10 bg-[#0a0f1a]/95 backdrop-blur-2xl shadow-[0_0_60px_rgba(168,85,247,0.15),0_0_120px_rgba(6,182,212,0.08)] overflow-hidden"
        >
          <!-- 顶部装饰光晕 -->
          <div class="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent pointer-events-none"></div>

          <!-- ── 弹窗头部 ── -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <MessageSquare class="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h3 class="text-base font-bold text-white">对话历史预览</h3>
                <p class="text-xs text-gray-500 mt-0.5">Agent 对话记录 #{{ recordId }}</p>
              </div>
            </div>
            <button
              @click="handleClose"
              class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all duration-200"
              aria-label="关闭"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- ── 弹窗内容区 ── -->
          <div class="flex-1 overflow-y-auto custom-scrollbar px-6 py-4 min-h-0">

            <!-- 加载状态（Requirements 13.2） -->
            <div
              v-if="isLoading"
              class="flex flex-col items-center justify-center py-16 gap-4"
            >
              <Loader2 class="w-8 h-8 text-cyan-400 animate-spin" />
              <p class="text-sm text-gray-400">正在加载对话历史...</p>
            </div>

            <!-- 错误状态（Requirements 13.7） -->
            <div
              v-else-if="errorMessage"
              class="flex flex-col items-center justify-center py-16 gap-4"
            >
              <div class="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <X class="w-6 h-6 text-red-400" />
              </div>
              <div class="text-center">
                <p class="text-sm font-medium text-red-300">加载失败</p>
                <p class="text-xs text-gray-500 mt-1 max-w-xs">{{ errorMessage }}</p>
              </div>
              <div class="flex gap-3">
                <!-- 重试按钮：重新触发 fetch（Requirements 13.7） -->
                <button
                  @click="handleRetry"
                  class="flex items-center gap-2 px-4 py-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-sm hover:bg-cyan-500/20 hover:border-cyan-500/50 transition-all duration-200"
                >
                  <RefreshCw class="w-3.5 h-3.5" />
                  重试
                </button>
                <!-- 关闭按钮：emit close（Requirements 13.7） -->
                <button
                  @click="handleClose"
                  class="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/5 text-gray-400 text-sm hover:bg-white/10 hover:text-white transition-all duration-200"
                >
                  关闭
                </button>
              </div>
            </div>

            <!-- 空状态（Requirements 13.8） -->
            <div
              v-else-if="!isLoading && chatHistory.length === 0"
              class="flex flex-col items-center justify-center py-16 gap-4"
            >
              <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                <MessageSquare class="w-6 h-6 text-gray-500" />
              </div>
              <div class="text-center">
                <p class="text-sm font-medium text-gray-400">暂无对话记录</p>
                <p class="text-xs text-gray-600 mt-1">该记录没有可预览的对话历史</p>
              </div>
            </div>

            <!-- 气泡对话列表（Requirements 13.3） -->
            <div
              v-else
              class="space-y-4"
            >
              <div
                v-for="(message, index) in chatHistory"
                :key="index"
                class="flex"
                :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
              >
                <!-- 用户消息：右对齐，紫色气泡（Requirements 13.3） -->
                <div
                  v-if="message.role === 'user'"
                  class="max-w-[75%] px-4 py-3 text-sm text-gray-100 leading-relaxed bg-purple-500/20 border border-purple-500/30 rounded-2xl rounded-tr-sm"
                >
                  {{ message.content }}
                </div>

                <!-- AI 消息：左对齐，深色气泡（Requirements 13.3） -->
                <div
                  v-else
                  class="max-w-[75%] px-4 py-3 text-sm text-gray-200 leading-relaxed bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm"
                >
                  {{ message.content }}
                </div>
              </div>
            </div>

          </div>

          <!-- ── 弹窗底部操作区（仅在有对话内容时显示） ── -->
          <div
            v-if="!isLoading && !errorMessage && chatHistory.length > 0"
            class="flex-shrink-0 px-6 py-4 border-t border-white/5"
          >
            <!-- "✨ 载入上下文并继续对话"按钮（Requirements 13.4） -->
            <button
              @click="handleLoadContext"
              class="w-full py-3 px-6 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.45)] transition-all duration-300 flex items-center justify-center gap-2"
            >
              <Sparkles class="w-4 h-4" />
              ✨ 载入上下文并继续对话
            </button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 弹窗淡入淡出过渡动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

/* 自定义滚动条（与 Dashboard 保持一致） */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
