<script setup>
/**
 * ChatDock.vue — Dashboard 底部浮动 AI 对话面板
 *
 * 职责：
 *   - 浮动容器、折叠态/展开态、transition、z-index、pointer-events
 *   - 默认展开
 *   - 右上角 28×28 折叠按钮
 *   - 折叠后显示 pill（AI 职场领航员 + 最近用户消息预览 + streaming pulse）
 *   - 点击 pill 展开，展开后输入框自动 focus
 *   - 归档按钮：手动归档当前完整对话到历史
 */
import { ref, nextTick } from 'vue'
import { MessageSquare, ChevronDown, ChevronUp, Archive, Plus } from 'lucide-vue-next'
import { useChatSessionStore } from '@/stores/chatSessionStore'
import { archiveDashboardChat } from '@/services/historyClient.js'
import ChatMessageList from './ChatMessageList.vue'
import ChatComposer from './ChatComposer.vue'

const props = defineProps({
  placeholder: { type: String, default: '' },
  carouselText: { type: String, default: '' },
  carouselFade: { type: Boolean, default: true }
})

const emit = defineEmits(['send', 'toast', 'new-chat'])

const chatStore = useChatSessionStore()
const composerRef = ref(null)
const messageListRef = ref(null)

async function toggleDock() {
  chatStore.toggleCollapsed()
  if (!chatStore.isCollapsed) {
    await nextTick()
    composerRef.value?.focus()
  }
}

function handleSend(text) {
  emit('send', text)
}

async function handleArchive() {
  if (!chatStore.canArchive) return
  chatStore.isArchiving = true
  try {
    const result = await archiveDashboardChat({
      sessionId: chatStore.currentSessionId,
      messages: chatStore.messages
    })
    chatStore.markArchived(result.record_id)
    emit('toast', '已归档本次对话')
  } catch (err) {
    console.error('归档失败:', err)
    emit('toast', '归档失败，请稍后重试')
  } finally {
    chatStore.isArchiving = false
  }
}

function handleNewChat() {
  // 不再在组件内 clearSession,统一交给 Dashboard 处理:
  //   1. abort 当前正在 streaming 的 SSE 请求
  //   2. clearSession + 生成新的 currentSessionId
  //   3. focus 输入框
  // 这样可以避免新建会话时旧流仍在 onMessage 中 += 内容污染新会话。
  emit('new-chat')
}

/** 外部可调用：聚焦输入框 */
function focus() {
  composerRef.value?.focus()
}

/** 外部可调用：设置输入内容 */
function setInput(text) {
  composerRef.value?.setInput(text)
}

/** 外部可调用：滚动消息到底部 */
function scrollToBottom() {
  messageListRef.value?.scrollToBottom()
}

defineExpose({ focus, setInput, scrollToBottom })
</script>

<template>
  <div class="input-container absolute bottom-5 left-0 w-full flex justify-center z-[60] pointer-events-none animate-[fadeInUp_0.5s_ease-out_0.5s_both] pb-[env(safe-area-inset-bottom)]">
    <transition name="chat-dock" mode="out-in">
      <!-- 折叠态：最小标题栏占位 pill -->
      <button
        v-if="chatStore.isCollapsed"
        key="collapsed"
        type="button"
        @click="toggleDock"
        title="展开 AI 助手"
        aria-label="展开 AI 助手"
        class="chat-dock-collapsed pointer-events-auto flex items-center gap-2 px-4 py-2.5 rounded-full border border-purple-400/40 bg-black/60 backdrop-blur-xl text-xs text-cyan-100 hover:text-white hover:border-cyan-400/60 hover:shadow-[0_0_22px_rgba(34,211,238,0.30)] ring-1 ring-purple-500/20 transition-all duration-300"
      >
        <MessageSquare class="w-3.5 h-3.5 text-cyan-300 flex-shrink-0" />
        <span class="font-medium flex-shrink-0">AI 职场领航员</span>
        <!-- 正在 streaming：pulse 指示 -->
        <span
          v-if="chatStore.isLoading"
          class="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_6px_rgba(34,211,238,0.8)]"
          aria-hidden="true"
          title="AI 正在输出..."
        />
        <!-- 有历史消息时展示最近一条用户消息预览 -->
        <span
          v-else-if="chatStore.lastUserPreview"
          class="flex-shrink-0 max-w-[120px] truncate text-cyan-200/70 hidden sm:block"
        >{{ chatStore.lastUserPreview }}</span>
        <!-- 展开图标 -->
        <ChevronUp class="w-3.5 h-3.5 text-cyan-300/80 flex-shrink-0" />
      </button>

      <!-- 展开态：完整浮动对话面板 -->
      <div
        v-else
        key="expanded"
        class="input-wrapper relative pointer-events-auto w-full max-w-4xl bg-black/50 backdrop-blur-md rounded-xl border border-white/10 p-4 transition-all duration-300 shadow-[0_0_15px_rgba(168,85,247,0.1)] border-purple-500/20 focus-within:border-cyan-500/50 focus-within:shadow-[0_0_30px_rgba(34,211,238,0.2)] focus-within:-translate-y-1"
        :class="{ 'border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.2)]': chatStore.isLoading }"
      >
        <!-- 顶部高亮分隔线 -->
        <div class="chat-dock-accent absolute top-0 left-0 right-0 h-px pointer-events-none" aria-hidden="true"></div>

        <!-- 顶部操作栏：归档 + 新建对话 + 折叠 -->
        <div class="chat-dock-fold-wrap absolute top-2 right-2 flex items-center gap-1.5">
          <!-- 归档按钮 -->
          <button
            type="button"
            @click.stop="handleArchive"
            :disabled="!chatStore.canArchive"
            :title="chatStore.archiveLabel"
            :aria-label="chatStore.archiveLabel"
            class="chat-dock-archive-btn h-7 px-2 rounded-md flex items-center justify-center gap-1 transition-all duration-200 border text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed"
            :class="chatStore.archivedRecordId && !chatStore.isDirty
              ? 'border-emerald-400/35 bg-emerald-500/10 text-emerald-300'
              : 'border-purple-400/35 bg-black/40 text-gray-300 hover:text-cyan-200 hover:border-cyan-400/60 hover:bg-cyan-500/10'"
          >
            <Archive class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{{ chatStore.archiveLabel }}</span>
          </button>
          <!-- 新建对话按钮 -->
          <button
            v-if="chatStore.messages.length > 0"
            type="button"
            @click.stop="handleNewChat"
            title="新建对话"
            aria-label="新建对话"
            class="h-7 px-2 rounded-md flex items-center justify-center gap-1 transition-all duration-200 border border-cyan-400/25 bg-black/40 text-gray-400 hover:text-cyan-200 hover:border-cyan-400/50 hover:bg-cyan-500/10 text-xs font-medium"
          >
            <Plus class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">新建</span>
          </button>
          <!-- 折叠按钮 -->
          <button
            type="button"
            @click="toggleDock"
            title="折叠 AI 助手"
            aria-label="折叠 AI 助手"
            class="chat-dock-fold-btn w-7 h-7 rounded-md flex items-center justify-center transition-all duration-200 border border-purple-400/35 bg-black/40 text-gray-300 hover:text-cyan-200 hover:border-cyan-400/60 hover:bg-cyan-500/10 hover:shadow-[0_0_12px_rgba(34,211,238,0.25)] ring-1 ring-purple-500/20 focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          >
            <ChevronDown class="w-4 h-4" />
          </button>
          <div class="chat-dock-fold-tooltip" aria-hidden="true">折叠 AI 助手</div>
        </div>

        <!-- 消息列表（有消息时展示） -->
        <ChatMessageList
          v-if="chatStore.messages.length > 0"
          ref="messageListRef"
          :messages="chatStore.messages"
          :isLoading="chatStore.isLoading"
          class="max-h-[40vh] mb-3"
        />

        <!-- 输入区 -->
        <ChatComposer
          ref="composerRef"
          :isLoading="chatStore.isLoading"
          :placeholder="placeholder"
          :carouselText="carouselText"
          :carouselFade="carouselFade"
          @send="handleSend"
        />
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ── 浮动对话框：折叠 / 展开过渡 ────────────────────────── */
.chat-dock-enter-active,
.chat-dock-leave-active {
  transition: opacity 0.28s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}
.chat-dock-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.985);
}
.chat-dock-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.985);
}

/* 顶部高亮分隔线 — 跟随主题色渐变(本轮接入) */
.chat-dock-accent {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(var(--accent-rgb), 0)            8%,
    rgba(var(--accent-rgb), 0.45)         30%,
    rgba(var(--accent-secondary-rgb), 0.55) 50%,
    rgba(var(--accent-rgb), 0.45)         70%,
    rgba(var(--accent-rgb), 0)            92%,
    transparent 100%
  );
  box-shadow: 0 0 8px rgba(var(--accent-rgb), 0.18);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}

/* 折叠态 pill — 跟随主题色渐变(本轮接入) */
.chat-dock-collapsed {
  border-color: var(--accent-border) !important;
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.38),
    0 0 14px rgba(var(--accent-rgb), 0.22);
  animation: chat-dock-pill-breathe 3.2s ease-in-out infinite;
}
.chat-dock-collapsed:hover {
  border-color: rgba(var(--accent-secondary-rgb), 0.6) !important;
  box-shadow:
    0 8px 28px rgba(0, 0, 0, 0.42),
    0 0 22px rgba(var(--accent-secondary-rgb), 0.30) !important;
}

@keyframes chat-dock-pill-breathe {
  0%, 100% {
    box-shadow:
      0 8px 24px rgba(0, 0, 0, 0.38),
      0 0 10px rgba(var(--accent-rgb), 0.18);
  }
  50% {
    box-shadow:
      0 8px 28px rgba(0, 0, 0, 0.42),
      0 0 20px rgba(var(--accent-secondary-rgb), 0.28);
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-dock-collapsed { animation: none; }
}

/* 折叠按钮 */
.chat-dock-fold-wrap {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

.chat-dock-fold-btn:hover {
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.22);
  transform: scale(1.08);
}
.chat-dock-fold-btn:active {
  transform: scale(0.96);
}

/* 内联 tooltip */
.chat-dock-fold-tooltip {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  white-space: nowrap;
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  background: rgba(6, 10, 20, 0.90);
  color: rgba(207, 250, 254, 0.9);
  backdrop-filter: blur(8px);
  opacity: 0;
  transform: translateY(-4px);
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.chat-dock-fold-wrap:hover .chat-dock-fold-tooltip {
  opacity: 1;
  transform: translateY(0);
}

.input-wrapper:focus-within {
  border-color: var(--accent-border) !important;
  box-shadow: 0 0 20px rgba(var(--accent-rgb), 0.22) !important;
}

/* 静态 shell:覆盖 Tailwind 写死的紫色边/光晕,跟随主题色 */
.input-wrapper {
  border-color: var(--accent-border) !important;
  box-shadow: 0 0 15px rgba(var(--accent-rgb), 0.12) !important;
}

@media (prefers-reduced-motion: reduce) {
  .chat-dock-enter-active,
  .chat-dock-leave-active {
    transition: opacity 0.18s ease;
  }
  .chat-dock-enter-from,
  .chat-dock-leave-to {
    transform: none;
  }
}
</style>
