<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Loader2, Mic, MicOff } from 'lucide-vue-next'

const props = defineProps({
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['result', 'error', 'listening-change'])

const isSupported = ref(true)
const isListening = ref(false)
const lastError = ref('')
const recognitionRef = ref(null)

const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

const setListening = (value) => {
  if (isListening.value === value) return
  isListening.value = value
  emit('listening-change', value)
}

const resolveErrorMessage = (event) => {
  const code = event?.error || ''
  if (code === 'not-allowed' || code === 'service-not-allowed') return '麦克风权限被拒绝，请在浏览器中允许后重试'
  if (code === 'audio-capture') return '未检测到可用麦克风'
  if (code === 'no-speech') return '没有识别到语音，请再试一次'
  if (code === 'network') return '语音识别网络异常，请稍后重试'
  if (code === 'aborted') return '语音输入已停止'
  return '语音识别失败，请稍后重试'
}

const stopRecognition = () => {
  const recognition = recognitionRef.value
  if (!recognition) {
    setListening(false)
    return
  }
  try {
    recognition.stop()
  } catch {
    setListening(false)
  }
}

const startRecognition = () => {
  if (props.disabled) return

  const SpeechRecognition = getSpeechRecognition()
  if (!SpeechRecognition) {
    isSupported.value = false
    const message = '当前浏览器不支持语音输入'
    lastError.value = message
    emit('error', message)
    return
  }

  lastError.value = ''
  const recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    recognitionRef.value = recognition
    setListening(true)
  }

  recognition.onresult = (event) => {
    let finalText = ''
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i]?.[0]?.transcript || ''
      if (event.results[i].isFinal) {
        finalText += transcript
      }
    }

    const normalized = finalText.trim()
    if (normalized) {
      emit('result', normalized)
    }
  }

  recognition.onerror = (event) => {
    const message = resolveErrorMessage(event)
    lastError.value = message
    emit('error', message)
  }

  recognition.onend = () => {
    if (recognitionRef.value === recognition) {
      recognitionRef.value = null
    }
    setListening(false)
  }

  try {
    recognition.start()
  } catch {
    const message = '语音输入启动失败，请稍后重试'
    lastError.value = message
    emit('error', message)
    setListening(false)
  }
}

const toggleListening = () => {
  if (!isSupported.value || props.disabled) return
  if (isListening.value) {
    stopRecognition()
    return
  }
  startRecognition()
}

watch(() => props.disabled, (disabled) => {
  if (disabled && isListening.value) {
    stopRecognition()
  }
})

const state = computed(() => {
  if (!isSupported.value) return 'unsupported'
  if (isListening.value) return 'listening'
  if (lastError.value) return 'error'
  return 'idle'
})

const buttonDisabled = computed(() => props.disabled || !isSupported.value)
const titleText = computed(() => {
  if (!isSupported.value) return '当前浏览器不支持语音输入'
  if (props.disabled) return '当前状态不可使用语音输入'
  return isListening.value ? '停止语音输入' : '语音输入'
})

onMounted(() => {
  isSupported.value = Boolean(getSpeechRecognition())
})

onBeforeUnmount(() => {
  const recognition = recognitionRef.value
  if (!recognition) return
  try {
    recognition.abort()
  } catch {}
  recognitionRef.value = null
  setListening(false)
})
</script>

<template>
  <button
    type="button"
    class="voice-mode-btn inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50"
    :class="{
      'voice-mode-btn--idle': state === 'idle',
      'voice-mode-btn--listening': state === 'listening',
      'voice-mode-btn--unsupported': state === 'unsupported',
      'voice-mode-btn--error': state === 'error'
    }"
    :disabled="buttonDisabled"
    :title="titleText"
    :aria-pressed="isListening"
    :aria-label="titleText"
    data-test="voice-mode-button"
    @click="toggleListening"
  >
    <span v-if="state === 'listening'" class="voice-mode-btn__pulse" aria-hidden="true"></span>
    <Loader2 v-if="state === 'listening'" class="h-3.5 w-3.5 animate-spin" />
    <MicOff v-else-if="state === 'unsupported'" class="h-3.5 w-3.5" />
    <Mic v-else class="h-3.5 w-3.5" />
    <span>{{ state === 'unsupported' ? '当前浏览器不支持语音输入' : state === 'listening' ? '录音中' : '语音输入' }}</span>
  </button>
</template>

<style scoped>
.voice-mode-btn {
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  background: rgba(0, 0, 0, 0.45);
  color: rgba(209, 213, 219, 0.92);
  border-color: rgba(255, 255, 255, 0.1);
}

.voice-mode-btn--idle:hover:not(:disabled) {
  color: rgb(165, 243, 252);
  border-color: rgba(34, 211, 238, 0.45);
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.14);
}

.voice-mode-btn--listening {
  color: rgb(252, 231, 243);
  border-color: rgba(236, 72, 153, 0.55);
  background: rgba(236, 72, 153, 0.14);
  box-shadow: 0 0 22px rgba(236, 72, 153, 0.24);
}

.voice-mode-btn--unsupported {
  color: rgba(156, 163, 175, 0.92);
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(75, 85, 99, 0.18);
}

.voice-mode-btn--error {
  color: rgb(254, 202, 202);
  border-color: rgba(248, 113, 113, 0.42);
  background: rgba(127, 29, 29, 0.16);
}

.voice-mode-btn__pulse {
  position: absolute;
  inset: 3px;
  border-radius: 0.45rem;
  border: 1px solid rgba(244, 114, 182, 0.45);
  animation: voice-mode-pulse 1.15s ease-out infinite;
  pointer-events: none;
}

@keyframes voice-mode-pulse {
  0% {
    opacity: 0.9;
    transform: scale(0.96);
  }
  100% {
    opacity: 0;
    transform: scale(1.12);
  }
}

@media (prefers-reduced-motion: reduce) {
  .voice-mode-btn__pulse {
    animation: none;
  }
}
</style>
