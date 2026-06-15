<script setup>
import { ref, computed, nextTick, onBeforeUnmount, watch } from 'vue'
import { Bot, Loader2 } from 'lucide-vue-next'
import { renderSafeMarkdown } from '@/utils/safeMarkdown.js'
import { useChatSessionStore } from '@/stores/chatSessionStore'
import TTSButton from '@/components/TTSButton.vue'

/**
 * ChatMessageList.vue —— 主聊天消息列表(P0 安全渲染版)
 *
 * 安全说明:
 *   - LLM / RAG 输出可能包含 raw HTML(<img onerror>、<script>、伪装链接等),
 *     直接 v-html 等同于把第三方/用户输入直接插入 DOM,存在 XSS 风险。
 *   - 现统一通过 renderSafeMarkdown 清洗:禁止 raw HTML、链接协议白名单、二次正则兜底。
 *   - 不影响普通 Markdown(粗体、列表、代码块、引用、表格等)的展示。
 *
 * TTS 朗读(Beta):
 *   - 每条 AI 消息时间戳右侧渲染 TTSButton。
 *   - cacheKey 由 sessionId + index 组合,保证同一条消息重复点击零网络。
 *   - streaming 中(chatStore.isLoading 且为最后一条 AI)按钮 disabled,
 *     避免对未完整文本朗读 + 与流式 token 冲突。
 */

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false }
})

const chatStore = useChatSessionStore()

const containerRef = ref(null)
const renderTick = ref(0)
const markdownCache = new Map()
const MARKDOWN_BATCH_MS = 80
const SCROLL_BATCH_MS = 80
const MARKDOWN_CACHE_LIMIT = 80
let scrollTimer = null
let scrollFrame = null
let markdownBatchTimer = null

function pruneMarkdownCache() {
  while (markdownCache.size > MARKDOWN_CACHE_LIMIT) {
    const firstKey = markdownCache.keys().next().value
    markdownCache.delete(firstKey)
  }
}

function cacheMarkdown(key, entry) {
  markdownCache.set(key, entry)
  pruneMarkdownCache()
}

function getCacheKey(index, message) {
  return `${chatStore.currentSessionId}:${index}:${message?.role || 'unknown'}`
}

function getRenderedMarkdown(message, index, isStreaming, tick) {
  if (message?.role !== 'ai') return ''
  const content = message.content || ''
  const key = getCacheKey(index, message)
  const cached = markdownCache.get(key)

  if (isStreaming) {
    if (cached && cached.tick === tick) return cached.html
    const html = renderSafeMarkdown(content)
    cacheMarkdown(key, { content, html, tick, streaming: true })
    return html
  }

  if (cached && !cached.streaming && cached.content === content) return cached.html
  const html = renderSafeMarkdown(content)
  cacheMarkdown(key, { content, html, tick: -1, streaming: false })
  return html
}

function flushScrollToBottom() {
  scrollFrame = null
  nextTick(() => {
    if (containerRef.value) {
      containerRef.value.scrollTop = containerRef.value.scrollHeight
    }
  })
}

function scrollToBottom() {
  if (scrollTimer || scrollFrame) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    scrollFrame = requestAnimationFrame(flushScrollToBottom)
  }, SCROLL_BATCH_MS)
}

function scheduleMarkdownRefresh() {
  if (markdownBatchTimer) return
  markdownBatchTimer = setTimeout(() => {
    markdownBatchTimer = null
    renderTick.value += 1
  }, MARKDOWN_BATCH_MS)
}

// 自动滚动：消息变化时滚到底部
watch(() => props.messages.length, () => {
  scrollToBottom()
  if (props.messages.length === 0) markdownCache.clear()
})

// streaming 内容变化时也滚动
watch(
  () => {
    const last = props.messages[props.messages.length - 1]
    return last?.content?.length || 0
  },
  () => {
    if (props.isLoading) scheduleMarkdownRefresh()
    scrollToBottom()
  }
)

watch(
  () => props.isLoading,
  (loading) => {
    if (!loading) {
      if (markdownBatchTimer) {
        clearTimeout(markdownBatchTimer)
        markdownBatchTimer = null
      }
      renderTick.value += 1
      scrollToBottom()
    }
  }
)

/**
 * 是否为「正在 streaming 的最后一条 AI 消息」。
 * 只有它需要 disabled,其它已结束的 AI 消息可以自由朗读。
 */
const isLastStreamingAI = (index, message) => {
  if (!props.isLoading) return false
  if (message?.role !== 'ai') return false
  const last = props.messages[props.messages.length - 1]
  return last && last === message && index === props.messages.length - 1
}

const renderedMessages = computed(() => {
  const tick = renderTick.value
  return props.messages.map((message, index) => {
    const streaming = isLastStreamingAI(index, message)
    return {
      message,
      index,
      html: getRenderedMarkdown(message, index, streaming, tick)
    }
  })
})

defineExpose({ scrollToBottom })

onBeforeUnmount(() => {
  if (scrollTimer) clearTimeout(scrollTimer)
  if (scrollFrame) cancelAnimationFrame(scrollFrame)
  if (markdownBatchTimer) clearTimeout(markdownBatchTimer)
  markdownCache.clear()
})
</script>

<template>
  <div
    ref="containerRef"
    class="chat-message-list flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1"
  >
    <div v-for="item in renderedMessages" :key="item.index" class="chat-message">
      <!-- 用户消息 -->
      <div v-if="item.message.role === 'user'" class="flex justify-end">
        <div class="max-w-[80%] bg-gradient-to-r from-fuchsia-500/20 to-purple-500/20 border border-fuchsia-500/30 rounded-xl p-3 text-right">
          <p class="text-sm text-gray-200">{{ item.message.content }}</p>
          <p class="text-xs text-gray-500 mt-1">{{ item.message.timestamp }}</p>
        </div>
      </div>
      <!-- AI 消息 -->
      <div v-else class="flex gap-3">
        <div class="w-8 h-8 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
          <Bot class="w-4 h-4 text-cyan-400" />
        </div>
        <div class="max-w-[80%] bg-gradient-to-r from-gray-800/50 to-gray-900/50 border border-white/10 rounded-xl p-3">
          <div class="text-sm text-gray-200 chat-markdown" v-html="item.html"></div>
          <div class="mt-1 flex items-center gap-2">
            <p class="text-xs text-gray-500 flex-1">{{ item.message.timestamp }}</p>
            <!-- TTS 朗读按钮(Beta):cacheKey = 会话 id + 索引,保证重复点击零网络 -->
            <TTSButton
              v-if="(item.message.content || '').trim()"
              :text="item.message.content || ''"
              :cache-key="`${chatStore.currentSessionId}:${item.index}`"
              :disabled="isLastStreamingAI(item.index, item.message)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Loading 指示器 -->
    <div v-if="isLoading" class="flex gap-3">
      <div class="w-8 h-8 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
        <Loader2 class="w-4 h-4 animate-spin text-cyan-400" />
      </div>
      <div class="bg-gradient-to-r from-gray-800/50 to-gray-900/50 border border-white/10 rounded-xl px-4 py-3">
        <div class="flex items-center gap-1.5">
          <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0s;"></div>
          <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0.2s;"></div>
          <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0.4s;"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(168, 85, 247, 0.5);
}

.chat-markdown :deep(h1) { font-size: 1.2em; font-weight: 700; margin: 0.5em 0 0.3em; color: #67e8f9; }
.chat-markdown :deep(h2) { font-size: 1.1em; font-weight: 600; margin: 0.4em 0 0.2em; color: #22d3ee; }
.chat-markdown :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 0.3em 0 0.15em; color: #06b6d4; }
.chat-markdown :deep(strong), .chat-markdown :deep(b) { color: #67e8f9; font-weight: 700; }
.chat-markdown :deep(p) { margin: 0.2em 0; color: rgba(229, 231, 235, 0.9); }
.chat-markdown :deep(ul), .chat-markdown :deep(ol) { padding-left: 1.2em; margin: 0.2em 0; }
.chat-markdown :deep(li) { margin: 0.1em 0; color: rgba(229, 231, 235, 0.85); }
.chat-markdown :deep(li)::marker { color: #06b6d4; }
.chat-markdown :deep(blockquote) { border-left: 3px solid rgba(6, 182, 212, 0.35); padding: 0.2em 0.6em; margin: 0.3em 0; background: rgba(6, 182, 212, 0.04); border-radius: 0 6px 6px 0; color: rgba(229, 231, 235, 0.7); }
.chat-markdown :deep(code) { background: rgba(6, 182, 212, 0.1); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.88em; color: #67e8f9; font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.chat-markdown :deep(pre) { background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(6, 182, 212, 0.12); border-radius: 8px; padding: 0.6em; overflow-x: auto; margin: 0.3em 0; }
.chat-markdown :deep(pre code) { background: none; padding: 0; border-radius: 0; color: rgba(229, 231, 235, 0.85); }
</style>
