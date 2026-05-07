<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Compass, Map, Target, Loader2, FileText, Copy, Download } from 'lucide-vue-next'
import { marked } from 'marked'

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const router = useRouter()
const route = useRoute()

const isRestoring = ref(false)

const resumeText = ref('')
const userConfusion = ref('')
const reportResult = ref('')
const displayedResult = ref('')
const isGenerating = ref(false)
const isComplete = ref(false)
const error = ref('')
const copySuccess = ref(false)

const resultContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (resultContainer.value) {
      resultContainer.value.scrollTop = resultContainer.value.scrollHeight
    }
  })
}

const isResumeValid = ref(false)

const recommendedQuestions = ref([])
const isLoadingSuggestions = ref(false)

const parsedReport = computed(() => {
  if (!displayedResult.value) return ''
  return marked.parse(displayedResult.value)
})

const fillConfusion = (text) => {
  userConfusion.value = text
}

const loadSuggestions = async () => {
  if (!resumeText.value || resumeText.value.trim().length < 20) return

  isLoadingSuggestions.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/career/suggestions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText.value })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    if (data.suggestions && data.suggestions.length > 0) {
      recommendedQuestions.value = data.suggestions
    }
  } catch (err) {
    console.error('加载推荐问题失败:', err)
    recommendedQuestions.value = [
      '简历缺乏亮点怎么补救？',
      '非科班如何进大厂？',
      '项目经验太简单怎么办？',
      '技术栈太旧如何转型？'
    ]
  } finally {
    isLoadingSuggestions.value = false
  }
}

const copyReport = async () => {
  try {
    await navigator.clipboard.writeText(reportResult.value)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = reportResult.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  }
}

const exportTxt = () => {
  const blob = new Blob([reportResult.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `职业规划蓝图_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const generatePlan = async () => {
  if (!userConfusion.value.trim()) {
    error.value = '请输入您的职业困惑或未来期望'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }

  isGenerating.value = true
  isComplete.value = false
  reportResult.value = ''
  displayedResult.value = ''
  error.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/career/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: resumeText.value,
        user_confusion: userConfusion.value
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `请求失败 (HTTP ${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim()
        } else if (line.startsWith('data:')) {
          const dataStr = line.substring(5).trim()
          if (!dataStr) continue

          if (currentEvent === 'reply') {
            try {
              const parsed = JSON.parse(dataStr)
              const content = parsed?.payload?.content || ''
              if (content) {
                displayedResult.value += content
                reportResult.value += content
                scrollToBottom()
              }
            } catch {}
          }
        }
      }
    }

    if (displayedResult.value) isComplete.value = true
  } catch (err) {
    console.error('职业规划请求失败:', err)
    error.value = err.message.includes('Failed to fetch')
      ? '😵 导师正在开小差，请检查网络后重试哦~'
      : `⚠️ ${err.message}`
    setTimeout(() => { error.value = '' }, 8000)
  } finally {
    isGenerating.value = false
  }
}

onMounted(async () => {
  const recordId = route.query.id
  if (recordId) {
    isRestoring.value = true
    try {
      const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history/${recordId}`)
      if (res.ok) {
        const data = await res.json()
        if (data.success && data.data) {
          const record = data.data
          reportResult.value = record.ai_result || ''
          displayedResult.value = record.ai_result || ''
          if (record.user_input) {
            const match = record.user_input.match(/困惑: (.+)/)
            if (match) userConfusion.value = match[1]
          }
          isComplete.value = true
          return
        }
      }
    } catch (err) {
      console.error('恢复历史记录失败:', err)
    } finally {
      isRestoring.value = false
    }
  }

  const globalResume = localStorage.getItem('resume_text')
  if (globalResume) {
    resumeText.value = globalResume
    isResumeValid.value = globalResume.trim().length >= 20
    if (isResumeValid.value) loadSuggestions()
  }
})

onUnmounted(() => {})
</script>

<template>
  <div class="min-h-[100dvh] relative flex flex-col lg:flex-row overflow-hidden bg-[#050505]">
    <!-- 极光流体背景 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="aurora-blob aurora-blob-1"></div>
      <div class="aurora-blob aurora-blob-2"></div>
      <div class="aurora-blob aurora-blob-3"></div>
    </div>

    <!-- 动态网格 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute inset-0 grid-bg"></div>
      <div class="absolute inset-0" style="background: radial-gradient(ellipse at center, transparent 0%, #050505 75%);"></div>
    </div>

    <!-- CRT 扫描线 -->
    <div class="crt-overlay absolute inset-0 pointer-events-none z-50"></div>

    <!-- 主内容 -->
    <div class="relative z-10 flex w-full flex-col lg:flex-row min-h-[100dvh] overflow-y-auto">
      <!-- 左侧控制台 40% -->
      <div class="left-panel w-full lg:w-[40%] xl:w-[38%] flex flex-col border-r border-cyan-500/10 bg-white/[0.02] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
        <!-- 返回按钮 -->
        <div class="p-4 border-b border-cyan-500/10">
          <button
            @click="router.push('/dashboard')"
            class="w-full flex items-center gap-2 text-cyan-400/70 hover:text-cyan-400 transition-all duration-300 group"
          >
            <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-300" />
            <span class="text-sm">返回工作台</span>
          </button>
        </div>

        <!-- 简历预览面板 -->
        <div class="p-4 border-b border-cyan-500/10">
          <div class="flex items-center gap-2 mb-3">
            <FileText class="w-5 h-5 text-cyan-400" />
            <h2 class="text-sm font-bold text-cyan-400">简历档案</h2>
          </div>
          <div
            class="rounded-xl border p-4 max-h-[200px] overflow-y-auto backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300"
            :class="isResumeValid
              ? 'bg-white/[0.02] border-cyan-500/20'
              : 'bg-amber-500/5 border-amber-500/20'"
          >
            <template v-if="isResumeValid">
              <p class="text-xs leading-relaxed whitespace-pre-wrap text-cyan-100/70">{{ resumeText }}</p>
            </template>
            <template v-else>
              <p class="text-xs text-amber-400/70">简历数据缺失，将基于困惑生成通用规划</p>
            </template>
          </div>
        </div>

        <!-- 职业困惑输入 -->
        <div class="flex-1 p-4 flex flex-col overflow-y-auto">
          <div class="flex items-center gap-2 mb-3">
            <Target class="w-5 h-5 text-cyan-400" />
            <h2 class="text-sm font-bold text-cyan-400">您的职业困惑</h2>
          </div>
          <textarea
            v-model="userConfusion"
            rows="5"
            placeholder="描述您当前的职业困惑或未来期望..."
            class="w-full rounded-xl px-4 py-3 text-base resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 border border-cyan-500/20 text-cyan-100 placeholder-cyan-400/30 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20"
          ></textarea>

          <!-- 快捷困惑 Chips -->
          <div class="flex flex-wrap gap-2 mt-3 mb-3">
            <template v-if="isLoadingSuggestions">
              <div v-for="i in 4" :key="'skel-'+i" class="px-3 py-1.5 rounded-full text-[11px] font-medium border border-cyan-500/10 bg-cyan-500/5 animate-pulse">
                <span class="inline-block w-24 h-3 bg-cyan-500/10 rounded"></span>
              </div>
              <p class="w-full text-[10px] text-cyan-400/40 mt-1">AI 正在深度剖析您的简历，生成专属问题...</p>
            </template>
            <template v-else>
              <button
                v-for="(chip, i) in recommendedQuestions"
                :key="i"
                @click="fillConfusion(chip)"
                class="chip-btn px-3 py-1.5 rounded-full text-[11px] font-medium transition-all duration-300 border border-cyan-500/20 text-cyan-400/70 hover:text-cyan-300 hover:border-cyan-500/50 hover:shadow-[0_0_12px_rgba(6,182,212,0.2)] hover:bg-cyan-500/5"
              >
                {{ chip }}
              </button>
            </template>
          </div>

          <!-- 生成按钮 -->
          <button
            @click="generatePlan"
            :disabled="isGenerating || !userConfusion.trim()"
            class="generate-btn mt-auto w-full py-4 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50"
          >
            <span class="generate-btn-shimmer"></span>
            <Loader2 v-if="isGenerating" class="w-4 h-4 animate-spin relative z-10" />
            <Compass v-else class="w-4 h-4 relative z-10" />
            <span class="relative z-10">{{ isGenerating ? 'AI 领航中...' : '生成专属职业蓝图' }}</span>
          </button>

          <!-- 错误提示 -->
          <div v-if="error" class="mt-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-400 text-center">
            {{ error }}
          </div>
        </div>
      </div>

      <!-- 右侧主报告区 60% -->
      <div class="flex-1 w-full lg:w-[60%] flex flex-col relative z-[60] pointer-events-auto pb-[env(safe-area-inset-bottom)]">
        <!-- Header -->
        <div class="flex items-center justify-between px-3 py-3 md:px-6 md:py-4 border-b border-cyan-500/20 bg-white/[0.03] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
          <div class="flex items-center gap-2 md:gap-3 flex-shrink-0 cursor-pointer hover:opacity-80 transition-opacity duration-200 active:scale-95" @click="router.push('/')">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Compass class="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 class="text-lg md:text-2xl font-bold text-cyan-400 whitespace-nowrap">🧭 AI 职业领航导师</h1>
              <p class="text-xs text-cyan-400/50">{{ isGenerating ? '导师正在查阅你的职业档案...' : '深度规划 · 精准导航' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <transition name="fade">
              <div v-if="isComplete" class="flex items-center gap-2">
                <button
                  @click="copyReport"
                  class="action-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-1.5 border border-cyan-500/30 text-cyan-400/80 hover:text-cyan-300 hover:border-cyan-500/60 hover:shadow-[0_0_15px_rgba(6,182,212,0.25)] bg-blue-950/40"
                >
                  <Copy class="w-3.5 h-3.5" />
                  {{ copySuccess ? '已复制' : '一键复制蓝图' }}
                </button>
                <button
                  @click="exportTxt"
                  class="action-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-1.5 border border-cyan-500/30 text-cyan-400/80 hover:text-cyan-300 hover:border-cyan-500/60 hover:shadow-[0_0_15px_rgba(6,182,212,0.25)] bg-blue-950/40"
                >
                  <Download class="w-3.5 h-3.5" />
                  导出为 TXT
                </button>
              </div>
            </transition>
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></div>
            <span class="text-xs text-green-400 font-mono">System Online</span>
          </div>
        </div>

        <!-- 报告展示区 -->
        <div ref="resultContainer" class="flex-1 overflow-y-auto p-4 md:p-8">
          <div v-if="displayedResult" class="markdown-body max-w-full">
            <div v-html="parsedReport"></div>
            <span v-if="!isComplete" class="inline-block w-2 h-[1.2em] bg-cyan-500 animate-pulse rounded-sm ml-0.5 align-middle"></span>
          </div>

          <div v-else-if="isGenerating" class="flex flex-col items-center justify-center h-full text-center">
            <div class="relative mb-6">
              <div class="w-20 h-20 rounded-2xl bg-cyan-500/[0.04] border border-cyan-500/[0.08] flex items-center justify-center">
                <Loader2 class="w-8 h-8 text-cyan-400 animate-spin" />
              </div>
              <div class="absolute -inset-2 rounded-2xl bg-cyan-500/[0.02] blur-xl animate-pulse"></div>
            </div>
            <p class="text-cyan-300/80 text-sm font-medium">导师正在查阅你的职业档案...</p>
            <p class="text-gray-600 text-xs mt-2 max-w-[240px]">正在深度分析简历与职业困惑，为你绘制专属职业蓝图</p>
          </div>

          <div v-else class="flex flex-col items-center justify-center h-full text-center">
            <div class="w-20 h-20 rounded-2xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-center mb-6">
              <Map class="w-10 h-10 text-gray-600" />
            </div>
            <p class="text-gray-500 text-sm">输入您的职业困惑，点击生成专属蓝图</p>
            <p class="text-gray-600 text-xs mt-2">AI 将结合您的简历，提供精准的职业导航</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.aurora-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  mix-blend-mode: screen;
}

.aurora-blob-1 {
  width: 700px;
  height: 700px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.2) 0%, transparent 70%);
  top: -15%;
  left: 5%;
  animation: auroraSpin1 30s ease-in-out infinite;
}

.aurora-blob-2 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.18) 0%, transparent 70%);
  top: 30%;
  right: -10%;
  animation: auroraSpin2 35s ease-in-out infinite;
}

.aurora-blob-3 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%);
  bottom: -10%;
  left: 25%;
  animation: auroraSpin3 40s ease-in-out infinite;
}

@keyframes auroraSpin1 {
  0% { transform: translate(0, 0) rotate(0deg) scale(1); }
  25% { transform: translate(150px, -100px) rotate(90deg) scale(1.2); }
  50% { transform: translate(-50px, 150px) rotate(180deg) scale(0.85); }
  75% { transform: translate(-150px, -50px) rotate(270deg) scale(1.1); }
  100% { transform: translate(0, 0) rotate(360deg) scale(1); }
}

@keyframes auroraSpin2 {
  0% { transform: translate(0, 0) rotate(0deg) scale(1); }
  25% { transform: translate(-200px, 80px) rotate(-90deg) scale(1.15); }
  50% { transform: translate(100px, -120px) rotate(-180deg) scale(0.9); }
  75% { transform: translate(80px, 60px) rotate(-270deg) scale(1.1); }
  100% { transform: translate(0, 0) rotate(-360deg) scale(1); }
}

@keyframes auroraSpin3 {
  0% { transform: translate(0, 0) rotate(0deg) scale(1); }
  33% { transform: translate(100px, -150px) rotate(120deg) scale(1.25); }
  66% { transform: translate(-150px, 80px) rotate(240deg) scale(0.8); }
  100% { transform: translate(0, 0) rotate(360deg) scale(1); }
}

.grid-bg {
  background-image:
    linear-gradient(rgba(6, 182, 212, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(6, 182, 212, 0.06) 1px, transparent 1px);
  background-size: 40px 40px;
}

.crt-overlay {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.03) 2px,
    rgba(255, 255, 255, 0.03) 4px
  );
  animation: crtFlicker 0.15s infinite;
}

@keyframes crtFlicker {
  0% { opacity: 0.97; }
  50% { opacity: 1; }
  100% { opacity: 0.98; }
}

.generate-btn {
  position: relative;
  overflow: hidden;
}

.generate-btn-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.15) 40%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0.15) 60%,
    transparent 100%
  );
  animation: shimmer 3s infinite;
  width: 200%;
  top: 0;
  left: -100%;
  pointer-events: none;
}

@keyframes shimmer {
  0% { transform: translateX(0); }
  100% { transform: translateX(100%); }
}

.fade-enter-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.overflow-y-auto::-webkit-scrollbar,
textarea::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track,
textarea::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb,
textarea::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover,
textarea::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}

.markdown-body {
  color: rgba(207, 250, 254, 0.9);
  font-size: 14px;
  line-height: 1.8;
  word-wrap: break-word;
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
  font-weight: 800;
  margin: 0 0 0.5em;
  padding-bottom: 0.25em;
  background: linear-gradient(135deg, #22d3ee, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid rgba(6, 182, 212, 0.12);
}

.markdown-body :deep(h2) {
  font-size: 1.25em;
  font-weight: 700;
  margin: 1em 0 0.4em;
  background: linear-gradient(135deg, #06b6d4, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(h3) {
  font-size: 1.08em;
  font-weight: 600;
  margin: 0.7em 0 0.3em;
  background: linear-gradient(135deg, #22d3ee, #60a5fa);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(strong), .markdown-body :deep(b) {
  color: #22d3ee;
  font-weight: 700;
}

.markdown-body :deep(p) {
  margin: 0.5em 0;
  color: rgba(207, 250, 254, 0.85);
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.markdown-body :deep(li) {
  margin: 0.25em 0;
  color: rgba(207, 250, 254, 0.8);
}

.markdown-body :deep(li)::marker {
  color: #22d3ee;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0.8em 0;
  border: 1px solid rgba(6, 182, 212, 0.15);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.markdown-body :deep(thead) { background: rgba(6, 182, 212, 0.08); }

.markdown-body :deep(th) {
  padding: 8px 12px;
  font-weight: 600;
  color: #22d3ee;
  font-size: 12px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.2);
}

.markdown-body :deep(td) {
  padding: 7px 12px;
  font-size: 12px;
  color: rgba(207, 250, 254, 0.8);
  border-bottom: 1px solid rgba(6, 182, 212, 0.06);
}

.markdown-body :deep(tr:hover td) { background: rgba(6, 182, 212, 0.04); }

.markdown-body :deep(blockquote) {
  border-left: 2px solid rgba(6, 182, 212, 0.3);
  padding: 0.3em 0.8em;
  margin: 0.6em 0;
  background: rgba(6, 182, 212, 0.04);
  border-radius: 0 6px 6px 0;
  color: rgba(207, 250, 254, 0.7);
}

.markdown-body :deep(code) {
  background: rgba(6, 182, 212, 0.08);
  padding: 0.1em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
  color: #67e8f9;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(6, 182, 212, 0.1);
  border-radius: 8px;
  padding: 0.8em;
  overflow-x: auto;
  margin: 0.6em 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: rgba(207, 250, 254, 0.85);
}

.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.2), transparent);
  margin: 1.2em 0;
}
</style>
