<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Compass, Map, Target, Loader2, FileText, Copy, Download } from 'lucide-vue-next'
import { marked } from 'marked'

const router = useRouter()

const resumeText = ref('')
const userConfusion = ref('')
const reportResult = ref('')
const displayedResult = ref('')
const isGenerating = ref(false)
const isComplete = ref(false)
const error = ref('')
const copySuccess = ref(false)

let typewriterTimer = null
let typewriterIndex = 0

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
    const response = await fetch('http://127.0.0.1:8000/api/career/suggestions', {
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

const startTypewriter = () => {
  const fullText = reportResult.value
  typewriterIndex = 0
  displayedResult.value = ''

  const typeNext = () => {
    if (typewriterIndex < fullText.length) {
      displayedResult.value += fullText[typewriterIndex]
      typewriterIndex++
      typewriterTimer = setTimeout(typeNext, 15 + Math.random() * 20)
    } else {
      isComplete.value = true
    }
  }
  typeNext()
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
    const response = await fetch('http://127.0.0.1:8000/api/career/plan', {
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

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const data = line.substring(5).trim()
          if (data) {
            try {
              const parsed = JSON.parse(data)
              if (parsed.type === 'error') {
                error.value = '腾讯云 API 报错：请求参数错误'
                console.error('腾讯云 API 错误:', parsed)
                isGenerating.value = false
                return
              }
              if (parsed.type === 'reply' && parsed.payload) {
                const content = parsed.payload.content || ''
                if (content) reportResult.value += content
              } else {
                const content = parsed.content || parsed.answer || parsed.text || parsed.message || parsed.delta || ''
                if (content) reportResult.value += content
              }
            } catch {
              if (data) reportResult.value += data
            }
          }
        } else if (line.trim() && !line.startsWith('event:') && !line.startsWith('id:')) {
          reportResult.value += line
        }
      }
    }

    if (reportResult.value) startTypewriter()
  } catch (err) {
    console.error('职业规划请求失败:', err)
    if (err.message.includes('Failed to fetch')) {
      error.value = '无法连接到后端 (http://127.0.0.1:8000)，请确认 FastAPI 服务已启动'
    } else {
      error.value = `生成失败: ${err.message}`
    }
    setTimeout(() => { error.value = '' }, 8000)
  } finally {
    isGenerating.value = false
  }
}

onMounted(() => {
  const globalResume = localStorage.getItem('resume_text')
  if (globalResume) {
    resumeText.value = globalResume
    isResumeValid.value = globalResume.trim().length >= 20
    if (isResumeValid.value) loadSuggestions()
  }
})

onUnmounted(() => {
  if (typewriterTimer) clearTimeout(typewriterTimer)
})
</script>

<template>
  <div class="min-h-screen relative flex overflow-hidden bg-[#050505]">
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
    <div class="relative z-10 flex w-full h-screen">
      <!-- 左侧控制台 -->
      <div class="left-panel w-[30%] flex flex-col border-r border-cyan-500/10 bg-white/[0.02] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
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
            class="w-full rounded-xl px-4 py-3 text-sm resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 border border-cyan-500/20 text-cyan-100 placeholder-cyan-400/30 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20"
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

      <!-- 右侧主报告区 -->
      <div class="flex-1 flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-white/[0.03] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Compass class="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 class="text-lg font-bold text-cyan-400">🧭 AI 职业领航导师</h1>
              <p class="text-xs text-cyan-400/50">深度规划 · 精准导航</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <!-- 复制/导出按钮 -->
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
        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="displayedResult" class="report-card rounded-2xl border border-cyan-500/20 bg-blue-950/30 backdrop-blur-xl p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
            <div v-html="parsedReport" class="markdown-body"></div>
            <span v-if="!isComplete" class="inline-block w-2 h-4 bg-cyan-500 animate-pulse ml-1"></span>
          </div>

          <div v-else-if="isGenerating" class="flex flex-col items-center justify-center h-full text-center">
            <div class="w-20 h-20 rounded-full bg-cyan-500/10 flex items-center justify-center mb-6 animate-pulse">
              <Loader2 class="w-10 h-10 text-cyan-400 animate-spin" />
            </div>
            <p class="text-cyan-400 text-sm font-medium">AI 正在为您绘制职业蓝图</p>
            <p class="text-gray-600 text-xs mt-2">分析简历与困惑，生成专属规划...</p>
          </div>

          <div v-else class="flex flex-col items-center justify-center h-full text-center">
            <div class="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-6">
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
  font-size: 1.6em;
  font-weight: 800;
  margin: 1.2em 0 0.6em;
  padding-bottom: 0.3em;
  background: linear-gradient(135deg, #22d3ee, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid rgba(6, 182, 212, 0.15);
  text-shadow: 0 0 30px rgba(6, 182, 212, 0.3);
}

.markdown-body :deep(h2) {
  font-size: 1.35em;
  font-weight: 700;
  margin: 1em 0 0.5em;
  padding-bottom: 0.25em;
  background: linear-gradient(135deg, #06b6d4, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid rgba(6, 182, 212, 0.1);
}

.markdown-body :deep(h3) {
  font-size: 1.15em;
  font-weight: 600;
  margin: 0.8em 0 0.4em;
  background: linear-gradient(135deg, #22d3ee, #60a5fa);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(strong),
.markdown-body :deep(b) {
  color: #22d3ee;
  font-weight: 700;
}

.markdown-body :deep(p) {
  margin: 0.6em 0;
  color: rgba(207, 250, 254, 0.85);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.markdown-body :deep(li) {
  margin: 0.3em 0;
  position: relative;
  color: rgba(207, 250, 254, 0.8);
}

.markdown-body :deep(li)::marker {
  color: #22d3ee;
  text-shadow: 0 0 6px rgba(34, 211, 238, 0.6);
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1em 0;
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
}

.markdown-body :deep(thead) {
  background: rgba(6, 182, 212, 0.1);
}

.markdown-body :deep(th) {
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: #22d3ee;
  font-size: 13px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.25);
}

.markdown-body :deep(td) {
  padding: 9px 14px;
  font-size: 13px;
  color: rgba(207, 250, 254, 0.8);
  border-bottom: 1px solid rgba(6, 182, 212, 0.08);
}

.markdown-body :deep(tr:hover td) {
  background: rgba(6, 182, 212, 0.06);
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid rgba(6, 182, 212, 0.4);
  padding: 0.5em 1em;
  margin: 0.8em 0;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 0 8px 8px 0;
  color: rgba(207, 250, 254, 0.7);
}

.markdown-body :deep(code) {
  background: rgba(6, 182, 212, 0.1);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
  color: #67e8f9;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(6, 182, 212, 0.15);
  border-radius: 10px;
  padding: 1em;
  overflow-x: auto;
  margin: 0.8em 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  color: rgba(207, 250, 254, 0.85);
}

.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.3), transparent);
  margin: 1.5em 0;
}

.markdown-body :deep(a) {
  color: #22d3ee;
  text-decoration: none;
  border-bottom: 1px solid rgba(34, 211, 238, 0.3);
  transition: all 0.2s;
}

.markdown-body :deep(a:hover) {
  color: #67e8f9;
  border-bottom-color: rgba(103, 232, 249, 0.5);
}
</style>
