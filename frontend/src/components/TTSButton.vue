<script setup>
/**
 * TTSButton.vue —— ChatDock AI 回复气泡的「朗读」喇叭按钮(Beta)
 *
 * 状态机:
 *   idle    — 未播放
 *   loading — 正在请求 /api/tts/synthesize
 *   playing — 正在播放(同一时间全局只允许一个 TTSButton 处于 playing)
 *   error   — 出错,2 秒后自动回 idle
 *
 * 关键约束(单例 + 缓存):
 *   1. 模块级单例 audioEl:整个应用同一时间只播放一个朗读音轨,
 *      点击其它 TTSButton 会先停止当前正在播放的那个。
 *   2. 模块级 blobCache:Map<cacheKey, Blob>,同一条消息重复点击零网络。
 *      cacheKey 由调用方传入(推荐 sessionId + 消息 idx)。
 *   3. 模块级 activeButton:跟踪当前哪个按钮在播,unmount/切换时强制 reset。
 *   4. AbortController:loading 中再次点击或组件 unmount 立即取消 fetch。
 *
 * 安全:
 *   - 不读取 / 不打印 API Key。
 *   - 文本长度防御性兜底(后端也会拦)。
 */

import { ref, computed, onUnmounted } from 'vue'
import { Volume2, Loader2, Square, AlertCircle } from 'lucide-vue-next'
import { synthesizeAudio, cleanTtsText, TTS_MAX_TEXT_LEN } from '@/services/ttsClient.js'
import { showToast } from '@/utils/uiFallbacks.js'

const props = defineProps({
  text: { type: String, required: true },
  /** 缓存键,推荐 `${sessionId}:${index}` */
  cacheKey: { type: String, default: '' },
  /** 父组件可禁用(streaming 中) */
  disabled: { type: Boolean, default: false },
  /** 朗读音色,缺省由后端 ENV 决定 */
  voice: { type: String, default: '' },
  /** 风格指令(可选) */
  style: { type: String, default: '' }
})

// ─── 模块级单例资源 ────────────────────────────
// 整个应用共享:同一时间只有一个 TTSButton 处于 playing
let _audioEl = null            // HTMLAudioElement | null
let _activeButton = null       // 当前播放按钮的 stopPlayback 句柄
const _blobCache = new Map()   // cacheKey → Blob,跨组件实例共享

function ensureAudio() {
  if (_audioEl) return _audioEl
  // 仅在浏览器侧创建,Server-side 无 window 时跳过
  if (typeof window === 'undefined' || typeof Audio === 'undefined') return null
  _audioEl = new Audio()
  _audioEl.preload = 'auto'
  return _audioEl
}

function stopGlobalPlayback() {
  // 让当前正在播放的按钮回到 idle
  if (_activeButton && typeof _activeButton.onForcedStop === 'function') {
    try { _activeButton.onForcedStop() } catch (_) { /* noop */ }
  }
  _activeButton = null
  if (_audioEl) {
    try {
      _audioEl.pause()
      _audioEl.removeAttribute('src')
      _audioEl.load()  // 释放 srcObject
    } catch (_) { /* noop */ }
  }
}

// ─── 组件级状态 ────────────────────────────
const state = ref('idle')   // 'idle' | 'loading' | 'playing' | 'error'
const errorMsg = ref('')
let abortCtl = null
let errorTimer = null

const isDisabled = computed(() => {
  return props.disabled || !String(props.text || '').trim()
})

/**
 * 朗读用文本：剥离 markdown 标记后送给 TTS（不影响页面展示）。
 * 调用方传 props.text 仍然可以是 markdown,组件内部统一清洗。
 */
const ttsText = computed(() => cleanTtsText(props.text || ''))

const tooltip = computed(() => {
  if (props.disabled) return 'AI 正在输出,稍后可朗读'
  if (state.value === 'loading') return '合成中...'
  if (state.value === 'playing') return '点击停止朗读'
  if (state.value === 'error')   return errorMsg.value || '朗读失败'
  return '朗读这段回复'
})

function setError(msg) {
  errorMsg.value = msg || '朗读失败'
  state.value = 'error'
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    if (state.value === 'error') {
      state.value = 'idle'
      errorMsg.value = ''
    }
  }, 2000)
}

/** 当外部强制停止本按钮播放时(其它按钮接管 / 组件卸载) */
function onForcedStop() {
  state.value = 'idle'
}

async function fetchOrCacheBlob() {
  const key = props.cacheKey || ''
  if (key && _blobCache.has(key)) {
    return _blobCache.get(key)
  }
  abortCtl = new AbortController()
  const blob = await synthesizeAudio({
    text: ttsText.value,
    voice: props.voice || undefined,
    style: props.style || undefined,
    signal: abortCtl.signal
  })
  if (key) _blobCache.set(key, blob)
  return blob
}

async function playFromBlob(blob) {
  const audio = ensureAudio()
  if (!audio) {
    throw new Error('当前环境不支持音频播放')
  }
  const url = URL.createObjectURL(blob)

  return await new Promise((resolve, reject) => {
    const cleanup = () => {
      audio.onended = null
      audio.onerror = null
      try { URL.revokeObjectURL(url) } catch (_) { /* noop */ }
    }
    audio.onended = () => { cleanup(); resolve('ended') }
    audio.onerror = () => { cleanup(); reject(new Error('音频播放失败')) }
    audio.src = url
    audio.play().catch((err) => {
      cleanup()
      reject(err)
    })
  })
}

async function handleClick() {
  if (isDisabled.value) return

  // 当前按钮正在播放 → 停止
  if (state.value === 'playing' && _activeButton?.id === buttonId) {
    stopGlobalPlayback()
    state.value = 'idle'
    return
  }

  // 文本超长前置防御(基于清洗后的朗读文本判断,避免 markdown 噪声虚增字数)
  const txt = ttsText.value
  if (!txt) return
  if (txt.length > TTS_MAX_TEXT_LEN) {
    setError(`文本过长(>${TTS_MAX_TEXT_LEN} 字),请缩短后再试`)
    showToast(`文本过长,请缩短后再试`, { type: 'error' })
    return
  }

  // loading 中再点 → 取消当前请求,回到 idle
  if (state.value === 'loading') {
    try { abortCtl?.abort() } catch (_) { /* noop */ }
    state.value = 'idle'
    return
  }

  // 切换到 loading,先把全局正在播的另一条停掉
  stopGlobalPlayback()
  state.value = 'loading'
  errorMsg.value = ''

  try {
    const blob = await fetchOrCacheBlob()
    state.value = 'playing'
    _activeButton = { id: buttonId, onForcedStop }
    await playFromBlob(blob)
    // 自然结束
    if (state.value === 'playing') state.value = 'idle'
    if (_activeButton?.id === buttonId) _activeButton = null
  } catch (err) {
    if (err?.name === 'AbortError') {
      state.value = 'idle'
      return
    }
    console.error('[TTSButton] 合成或播放失败:', err)
    setError(err?.message || '朗读失败')
  }
}

// 唯一标识本按钮实例(便于全局 _activeButton 比对)
const buttonId = Symbol('ttsButton')

onUnmounted(() => {
  // 卸载时如果是当前正在播放的按钮,停掉播放并解占
  if (_activeButton?.id === buttonId) {
    stopGlobalPlayback()
  }
  if (errorTimer) clearTimeout(errorTimer)
  try { abortCtl?.abort() } catch (_) { /* noop */ }
})
</script>

<template>
  <button
    type="button"
    class="tts-btn"
    :class="{
      'tts-btn--idle':    state === 'idle',
      'tts-btn--loading': state === 'loading',
      'tts-btn--playing': state === 'playing',
      'tts-btn--error':   state === 'error',
      'tts-btn--disabled': isDisabled
    }"
    :disabled="isDisabled"
    :title="tooltip"
    :aria-label="tooltip"
    data-test="tts-button"
    @click="handleClick"
  >
    <Loader2  v-if="state === 'loading'" class="w-3 h-3 animate-spin" />
    <Square   v-else-if="state === 'playing'" class="w-3 h-3" />
    <AlertCircle v-else-if="state === 'error'" class="w-3 h-3" />
    <Volume2  v-else class="w-3 h-3" />
  </button>
</template>

<style scoped>
.tts-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(229, 231, 235, 0.7);
  cursor: pointer;
  transition: all 0.18s ease;
}
.tts-btn:hover:not(:disabled) {
  border-color: var(--accent-border, rgba(34, 211, 238, 0.4));
  background: var(--accent-soft, rgba(34, 211, 238, 0.1));
  color: rgb(var(--accent-rgb, 34, 211, 238));
  box-shadow: 0 0 8px rgba(var(--accent-rgb, 34, 211, 238), 0.20);
}
.tts-btn--playing {
  border-color: var(--accent-border, rgba(34, 211, 238, 0.4)) !important;
  background: var(--accent-soft, rgba(34, 211, 238, 0.12)) !important;
  color: rgb(var(--accent-rgb, 34, 211, 238)) !important;
  box-shadow: 0 0 10px rgba(var(--accent-rgb, 34, 211, 238), 0.25) !important;
  animation: tts-pulse 1.4s ease-in-out infinite;
}
@keyframes tts-pulse {
  0%, 100% { box-shadow: 0 0 8px  rgba(var(--accent-rgb, 34, 211, 238), 0.20); }
  50%      { box-shadow: 0 0 14px rgba(var(--accent-rgb, 34, 211, 238), 0.40); }
}
.tts-btn--loading {
  color: rgb(var(--accent-rgb, 34, 211, 238));
}
.tts-btn--error {
  border-color: rgba(239, 68, 68, 0.45);
  color: rgb(252, 165, 165);
  background: rgba(239, 68, 68, 0.08);
}
.tts-btn--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
@media (prefers-reduced-motion: reduce) {
  .tts-btn--playing { animation: none; }
}
</style>
