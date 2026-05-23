<script setup>
import { ref, computed } from 'vue'
import { Send, Paperclip, Sparkles, X, FileText, Loader2 } from 'lucide-vue-next'
import { ACCEPTED_EXTENSIONS } from '@/utils/fileConstants.js'

const props = defineProps({
  isLoading: { type: Boolean, default: false },
  placeholder: { type: String, default: '向 AI 职场领航员提问...' },
  knowledgeId: { type: String, default: '' },
  knowledgeFileName: { type: String, default: '' },
  carouselText: { type: String, default: '' },
  carouselFade: { type: Boolean, default: true }
})

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

function handleFileChange(event) {
  const files = event.target.files
  if (files.length > 0) {
    emit('file-upload', files[0])
    event.target.value = ''
  }
}

/** 外部可调用：聚焦输入框 */
function focus() {
  inputRef.value?.focus()
}

/** 外部可调用：设置输入内容 */
function setInput(text) {
  inputText.value = text
}

defineExpose({ focus, setInput, inputText })
</script>

<template>
  <!-- 个人文件挂载状态 -->
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
    <label class="relative flex-shrink-0 mb-0.5">
      <input
        type="file"
        class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        @change="handleFileChange"
        :accept="ACCEPTED_EXTENSIONS"
      />
      <div class="w-9 h-9 rounded-lg border border-white/10 bg-white/5 flex items-center justify-center hover:bg-white/10 hover:border-purple-500/30 transition-all duration-300 cursor-pointer">
        <Paperclip class="w-4 h-4 text-gray-400" />
      </div>
    </label>

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
    <span class="text-xs text-gray-500">AI 职场领航员 · 附件仅作本轮对话上下文</span>
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
</style>
