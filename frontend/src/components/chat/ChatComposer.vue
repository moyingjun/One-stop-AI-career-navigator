<script setup>
import { ref, computed } from 'vue'
import { Send, Paperclip, Sparkles, X, FileText, Loader2 } from 'lucide-vue-next'

/**
 * ChatComposer.vue —— 主聊天输入区(P0 收口版)
 *
 * 本轮收口决策:
 *   - 旧 /api/knowledge/upload 已被后端下线(返回 410)。
 *   - 新 /api/kb/upload 是持久知识库,语义不同,不可临时接管"本轮对话附件"。
 *   - 因此暂时禁用纸夹附件入口,避免触发已下线的旧端点,同时不误导用户。
 *   - 为了把改动收敛在前端,保留 file-upload / clear-knowledge 事件签名不变,
 *     上游(ChatDock / Dashboard)无需改动;按钮变为 disabled,不再触发任何上传。
 */

const props = defineProps({
  isLoading: { type: Boolean, default: false },
  placeholder: { type: String, default: '向 AI 职场领航员提问...' },
  knowledgeId: { type: String, default: '' },
  knowledgeFileName: { type: String, default: '' },
  carouselText: { type: String, default: '' },
  carouselFade: { type: Boolean, default: true }
})

// 注意:file-upload / clear-knowledge 事件保留是为了不破坏父组件 props/emit 契约。
// 本轮 file-upload 实际不再被任何控件触发;clear-knowledge 仍然在历史挂载文件场景下可用。
const emit = defineEmits(['send', 'file-upload', 'clear-knowledge'])

const inputRef = ref(null)
const inputText = ref('')

const canSend = computed(() => inputText.value.trim().length > 0 && !props.isLoading)

function handleEnter(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleSend() {
  if (!canSend.value) return
  emit('send', inputText.value.trim())
  inputText.value = ''
}

/** 外部可调用:聚焦输入框 */
function focus() {
  inputRef.value?.focus()
}

/** 外部可调用:设置输入内容 */
function setInput(text) {
  inputText.value = text
}

defineExpose({ focus, setInput, inputText })
</script>

<template>
  <!-- 个人文件挂载状态(历史挂载场景仍可清空,本轮不允许新增挂载) -->
  <div v-if="knowledgeId" class="mb-3 flex items-center gap-2">
    <div class="personal-file-tag rounded-full px-3 py-1 flex items-center gap-2">
      <FileText class="w-3.5 h-3.5 text-gray-300" />
      <span class="text-xs text-gray-200 truncate max-w-[260px]">[个人文件已挂载] {{ knowledgeFileName }}</span>
      <button
        @click="emit('clear-knowledge')"
        class="text-gray-400 hover:text-white transition-colors ml-1"
        title="清空文件挂载"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
  <!-- 系统预设知识库状态 -->
  <div v-else class="mb-3 flex items-center gap-2">
    <div class="system-knowledge-tag rounded-full px-3 py-1 flex items-center gap-2">
      <Sparkles class="w-3.5 h-3.5 text-emerald-300" />
      <span class="text-xs text-emerald-100 truncate max-w-[260px] system-carousel-text" :class="{ 'carousel-fade-out': !carouselFade, 'carousel-fade-in': carouselFade }">{{ carouselText }}</span>
    </div>
  </div>

  <div class="flex items-end gap-3">
    <!-- 附件入口已禁用:旧 /api/knowledge/upload 已下线,新 /api/kb/upload 语义不一致,
         本轮直接禁用按钮,避免误导用户和触发 410。视觉风格保持不变。 -->
    <button
      type="button"
      disabled
      class="composer-attach-btn w-9 h-9 rounded-lg flex items-center justify-center mb-0.5"
      title="文档引用功能稍后开放"
      aria-label="文档引用功能稍后开放"
      data-test="chat-composer-attach-disabled"
    >
      <Paperclip class="w-4 h-4 text-gray-500" />
    </button>

    <textarea
      ref="inputRef"
      v-model="inputText"
      @keydown="handleEnter"
      :placeholder="placeholder"
      rows="1"
      class="flex-1 bg-transparent border-none outline-none text-gray-300 placeholder-gray-500 resize-none text-sm leading-relaxed focus:ring-0"
    ></textarea>

    <button
      @click="handleSend"
      :disabled="!canSend"
      class="flex-shrink-0 px-4 py-2.5 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 overflow-hidden relative bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50 mb-0.5"
    >
      <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
      <Send v-else class="w-4 h-4" />
    </button>
  </div>

  <div class="flex items-center gap-2 mt-2">
    <Sparkles class="w-3 h-3 text-cyan-500/50" />
    <!-- 旧文案"附件仅作本轮对话上下文"会让用户以为可以临时上传;附件入口已禁用,因此改为中性提示。 -->
    <span class="text-xs text-gray-500">AI 职场领航员 · 文档引用功能稍后开放</span>
  </div>
</template>

<style scoped>
.personal-file-tag {
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.04);
  transition: all 0.3s ease;
}
.personal-file-tag:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.08);
}

.system-knowledge-tag {
  border: 1px solid rgba(16, 185, 129, 0.35);
  background: rgba(16, 185, 129, 0.08);
  animation: breatheGlow 3s ease-in-out infinite;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.1), inset 0 0 8px rgba(16, 185, 129, 0.05);
}

@keyframes breatheGlow {
  0%, 100% {
    border-color: rgba(16, 185, 129, 0.3);
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.08), inset 0 0 4px rgba(16, 185, 129, 0.03);
  }
  50% {
    border-color: rgba(6, 182, 212, 0.5);
    box-shadow: 0 0 18px rgba(6, 182, 212, 0.2), inset 0 0 10px rgba(6, 182, 212, 0.06);
  }
}

.carousel-fade-in {
  opacity: 1;
  transition: opacity 0.3s ease-in;
}
.carousel-fade-out {
  opacity: 0;
  transition: opacity 0.3s ease-out;
}

/* 附件入口禁用态:与原 enabled 视觉风格保持一致,仅降低饱和度并屏蔽交互。 */
.composer-attach-btn {
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  cursor: not-allowed;
  opacity: 0.55;
  transition: opacity 0.18s ease, border-color 0.18s ease;
}
.composer-attach-btn:hover {
  /* 悬停态保持禁用视觉,只有边框微亮以提示存在 */
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}
</style>
