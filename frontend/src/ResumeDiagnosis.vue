<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { FileText, ArrowLeft, Paperclip, Sparkles, Bot, Loader2 } from 'lucide-vue-next'
import { marked } from 'marked'
import { parseFile } from '@/utils/ocrHelper.js'
import { ACCEPTED_EXTENSIONS, validateFile } from '@/utils/fileConstants.js'
import CyberRadarChart from '@/components/CyberRadarChart.vue'
import CyberGlassCard from './components/CyberGlassCard.vue'

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const router = useRouter()
const route = useRoute()

const isRestoring = ref(false)

const resumeText = ref('')
const jdText = ref('')
const targetRole = ref('')
const diagnosisResult = ref('')
const displayedResult = ref('')
const isDiagnosing = ref(false)
const isComplete = ref(false)
const error = ref('')
const uploadedFileName = ref('')
const isDragging = ref(false)
const dropZoneActive = ref(false)
const isParsing = ref(false)
const isScanPdfDetected = ref(false)

const DIAGNOSIS_LABELS = ['keywordMatch', 'experienceQuality', 'dataDriven', 'skillCompleteness', 'layoutLogic', 'coreCompetitiveness']
const DIAGNOSIS_LABEL_CN = ['关键词匹配', '经历含金量', '数据化程度', '技能完整性', '逻辑排版', '核心竞争力']

const diagnosisScores = ref({
  keywordMatch: 2,
  experienceQuality: 2,
  dataDriven: 2,
  skillCompleteness: 2,
  layoutLogic: 2,
  coreCompetitiveness: 2
})

// 将诊断分数转换为 CyberRadarChart 所需的 chartData 格式
const cyberRadarChartData = computed(() => ({
  indicators: DIAGNOSIS_LABEL_CN.map(name => ({ name, max: 100 })),
  values: DIAGNOSIS_LABELS.map(key => diagnosisScores.value[key])
}))

const extractScoresFromResult = (text) => {
  try {
    const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[1])
      const required = ['keywordMatch', 'experienceQuality', 'dataDriven', 'skillCompleteness', 'layoutLogic', 'coreCompetitiveness']
      if (required.every(k => k in parsed)) {
        return parsed
      }
    }
  } catch {}
  return null
}

const resultContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (resultContainer.value) {
      resultContainer.value.scrollTop = resultContainer.value.scrollHeight
    }
  })
}

const handleFileDrop = (event) => {
  isDragging.value = false
  dropZoneActive.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) processFile(files[0])
}

const processFile = async (file) => {
  const validation = validateFile(file)
  if (!validation.valid) {
    error.value = validation.error
    setTimeout(() => { error.value = '' }, 4000)
    return
  }

  uploadedFileName.value = file.name
  isParsing.value = true
  isScanPdfDetected.value = false

  try {
    const text = await parseFile(file, {
      onScanDetected: () => { isScanPdfDetected.value = true }
    })

    if (!text.trim()) {
      error.value = '文件内容为空或未识别到文字，请检查后重试'
      setTimeout(() => { error.value = '' }, 4000)
      return
    }

    resumeText.value = text
    if (file.type.startsWith('image/')) {
      localStorage.setItem('resume_text', text.trim())
    }
  } catch (e) {
    error.value = e.message || '文件解析失败，请重试'
    setTimeout(() => { error.value = '' }, 4000)
  } finally {
    isParsing.value = false
    isScanPdfDetected.value = false
  }
}

const startDiagnosis = async () => {
  if (!resumeText.value.trim()) {
    error.value = '请先粘贴简历内容或上传简历文件'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }

  isDiagnosing.value = true
  isComplete.value = false
  diagnosisResult.value = ''
  displayedResult.value = ''
  error.value = ''
  diagnosisScores.value = { keywordMatch: 2, experienceQuality: 2, dataDriven: 2, skillCompleteness: 2, layoutLogic: 2, coreCompetitiveness: 2 }

  try {
    const response = await fetch(`${API_BASE_URL}/resume/diagnose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: resumeText.value,
        target_role: targetRole.value,
        jd_text: jdText.value
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
                diagnosisResult.value += content
                scrollToBottom()
              }
            } catch {}
          }
        }
      }
    }

    if (displayedResult.value) {
      isComplete.value = true
      const scores = extractScoresFromResult(diagnosisResult.value)
      if (scores) {
        diagnosisScores.value = { ...diagnosisScores.value, ...scores }
      }
      const cleanedDisplay = displayedResult.value.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
      displayedResult.value = cleanedDisplay
      const cleanedDiagnosis = diagnosisResult.value.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
      diagnosisResult.value = cleanedDiagnosis
    }
  } catch (err) {
    console.error('诊断请求失败:', err)
    error.value = err.message.includes('Failed to fetch')
      ? '😵 导师正在开小差，请检查网络后重试哦~'
      : `⚠️ ${err.message}`
    setTimeout(() => { error.value = '' }, 8000)
  } finally {
    isDiagnosing.value = false
  }
}

const goToMockInterview = () => {
  localStorage.setItem('resume_text', resumeText.value)
  localStorage.setItem('target_role', targetRole.value)
  localStorage.setItem('jd_content', jdText.value)
  router.push('/premium-interview')
}

const initResume = async () => {
  const recordId = route.query.id
  if (recordId) {
    isRestoring.value = true
    try {
      const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history/${recordId}`)
      if (res.ok) {
        const data = await res.json()
        if (data.success && data.data) {
          const record = data.data

          if (record.extra_data) {
            try {
              const extra = typeof record.extra_data === 'string' ? JSON.parse(record.extra_data) : record.extra_data
              if (extra.resume_text) resumeText.value = extra.resume_text
              if (extra.target_role) targetRole.value = extra.target_role
              if (extra.jd_text) jdText.value = extra.jd_text
            } catch {}
          }

          if (record.user_input) {
            const match = record.user_input.match(/目标岗位: (.+)/)
            if (match && !targetRole.value) targetRole.value = match[1]
          }

          let rawResult = record.ai_result || ''

          if (record.scores) {
            try {
              const scores = typeof record.scores === 'string' ? JSON.parse(record.scores) : record.scores
              const required = ['keywordMatch', 'experienceQuality', 'dataDriven', 'skillCompleteness', 'layoutLogic', 'coreCompetitiveness']
              if (required.every(k => k in scores)) {
                diagnosisScores.value = { ...diagnosisScores.value, ...scores }
              }
            } catch {}
          }

          const cleanedResult = rawResult.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
          diagnosisResult.value = cleanedResult
          displayedResult.value = cleanedResult

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
    uploadedFileName.value = '已加载全局简历'
  }
  const globalRole = localStorage.getItem('target_role')
  if (globalRole) targetRole.value = globalRole
}

onMounted(() => { initResume() })
onUnmounted(() => {})
</script>

<template>
  <div class="min-h-[100dvh] bg-[#020205] text-gray-300 relative flex flex-col lg:flex-row overflow-x-hidden">
    <!-- 统一紫/青 blur 背景层 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vw] bg-purple-600/20 blur-[150px] rounded-full"></div>
      <div class="absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-cyan-600/15 blur-[150px] rounded-full"></div>
    </div>

    <!-- 返回按钮 - 页面级别 -->
    <div class="absolute top-4 left-4 z-20">
      <button
        @click="router.push('/dashboard')"
        class="flex items-center gap-2 text-cyan-400/70 hover:text-cyan-400 transition-all duration-300 group focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:ring-offset-2 focus:ring-offset-[#020205] rounded-lg px-2 py-1"
      >
        <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-300" />
        <span class="text-sm">返回工作台</span>
      </button>
    </div>

    <!-- 主内容 -->
    <div class="relative z-10 flex w-full flex-col lg:flex-row min-h-[100dvh] pt-14 overflow-y-auto">
      <!-- 左栏 40%：简历参考区 -->
      <CyberGlassCard variant="purple" headerless no-padding class="w-full lg:w-[40%] flex flex-col min-h-0 overflow-y-auto border-r border-purple-500/10">
            <!-- 文件上传区 -->
            <div class="p-3 md:p-4 border-b border-white/[0.04]">
              <div
                class="upload-zone relative bg-white/[0.02] backdrop-blur-xl border rounded-xl p-3 md:p-4 cursor-pointer transition-all duration-300"
                :class="dropZoneActive ? 'border-purple-500/40 bg-purple-500/[0.04]' : 'border-white/[0.05]'"
                @dragover.prevent="dropZoneActive = true; isDragging = true"
                @dragleave.prevent="dropZoneActive = false; isDragging = false"
                @drop.prevent="handleFileDrop"
              >
                <input type="file" ref="fileInput" class="hidden" :accept="ACCEPTED_EXTENSIONS" @change="handleFileSelect" />
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300" :class="dropZoneActive ? 'bg-purple-500/15' : 'bg-white/[0.03]'">
                    <Paperclip class="w-4 h-4" :class="dropZoneActive ? 'text-purple-400' : 'text-gray-500'" />
                  </div>
                  <div class="flex-1 text-left min-w-0">
                    <p class="text-xs md:text-sm text-gray-300 truncate">
                      <span class="text-purple-400 cursor-pointer font-medium" @click="$refs.fileInput.click()">点击上传</span>
                      <span class="text-gray-500"> 或拖拽文件到此处</span>
                    </p>
                    <p class="text-[10px] md:text-xs text-gray-600 mt-0.5">支持文档与图片格式上传（PDF/Word/TXT/JPG/PNG/WEBP）</p>
                  </div>
                </div>
                <p v-if="uploadedFileName && !isParsing" class="mt-2 text-xs text-purple-400 flex items-center gap-1">
                  <FileText class="w-3 h-3" />
                  已加载：{{ uploadedFileName }}
                </p>
                <div v-if="isParsing" class="mt-3 flex items-center gap-2">
                  <Loader2 class="w-3.5 h-3.5 text-purple-400 animate-spin" />
                  <span class="text-xs text-purple-300">{{ isScanPdfDetected ? '深度视觉扫描中...' : '解析文件中...' }}</span>
                </div>
              </div>
            </div>

            <!-- 简历内容 -->
            <div class="p-3 md:p-4 border-b border-white/[0.04]">
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">简历内容</h3>
              <div class="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 text-xs md:text-sm text-gray-300 leading-relaxed max-h-[200px] overflow-y-auto whitespace-pre-wrap font-mono tracking-[0.01em]">
                {{ resumeText || '等待输入简历内容...' }}
              </div>
            </div>

            <!-- 目标岗位 -->
            <div class="p-3 md:p-4 border-b border-white/[0.04]">
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">目标岗位</h3>
              <input
                v-model="targetRole"
                type="text"
                placeholder="如：Java后端开发工程师"
                class="w-full bg-white/[0.02] border border-white/[0.05] rounded-xl px-3 py-2 md:px-4 md:py-3 text-sm md:text-base text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500/40 focus:ring-1 focus:ring-purple-500/20 transition-all duration-300"
              />
            </div>

            <!-- 岗位描述 -->
            <div class="p-3 md:p-4 border-b border-white/[0.04]">
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">岗位描述 (可选)</h3>
              <textarea
                v-model="jdText"
                placeholder="粘贴目标岗位的 JD 内容..."
                rows="4"
                class="w-full bg-white/[0.02] border border-white/[0.05] rounded-xl px-3 py-2 md:px-4 md:py-3 text-xs md:text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500/40 focus:ring-1 focus:ring-purple-500/20 transition-all duration-300 resize-none leading-relaxed"
              ></textarea>
            </div>

            <!-- 诊断按钮 -->
            <div class="p-3 md:p-4 mt-auto">
              <button
                @click="startDiagnosis"
                :disabled="isDiagnosing || !resumeText.trim()"
                class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3 md:py-4 rounded-2xl font-semibold text-sm md:text-base shadow-lg shadow-purple-500/20 hover:shadow-xl hover:shadow-purple-500/30 transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 flex items-center justify-center gap-2"
              >
                <Loader2 v-if="isDiagnosing" class="w-4 h-4 animate-spin" />
                <Sparkles v-else class="w-4 h-4" />
                {{ isDiagnosing ? 'AI 深度分析中...' : '开始深度诊断' }}
              </button>
              <div v-if="error" class="mt-3 bg-red-500/[0.06] border border-red-500/[0.15] rounded-xl p-3 text-xs text-red-400 text-center">
                {{ error }}
              </div>
            </div>
          </CyberGlassCard>

          <!-- 右栏 60%：AI 诊断报告 -->
          <CyberGlassCard variant="purple" headerless no-padding class="flex-1 lg:w-[60%] flex flex-col min-h-0">
            <!-- 报告标题栏 -->
            <div class="px-3 py-2 md:px-6 md:py-3 border-b border-white/[0.04] flex items-center justify-between bg-white/[0.01]">
              <div class="flex items-center gap-2">
                <Bot class="w-4 h-4 text-purple-400" />
                <h2 class="text-sm font-semibold text-gray-300">AI 诊断报告</h2>
              </div>
              <div class="flex items-center gap-2">
                <div v-if="isComplete" class="flex items-center gap-1.5">
                  <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                  <span class="text-xs text-green-400">分析完成</span>
                </div>
                <div v-else-if="isDiagnosing" class="flex items-center gap-1.5">
                  <Loader2 class="w-3 h-3 animate-spin text-purple-400" />
                  <span class="text-xs text-purple-400">导师正在查阅你的职业档案...</span>
                </div>
              </div>
            </div>

            <!-- 报告内容 -->
            <div ref="resultContainer" class="flex-1 overflow-y-auto p-4 md:p-8">
              <!-- 六维雷达图 -->
              <div v-if="isComplete" class="mb-6">
                <div class="flex items-center gap-2 mb-3">
                  <Sparkles class="w-4 h-4 text-purple-400" />
                  <h3 class="text-sm font-semibold text-purple-400">六维简历评分</h3>
                </div>
                <CyberRadarChart :chartData="cyberRadarChartData" />
                <div class="grid grid-cols-6 gap-1 mt-3">
                  <div v-for="(label, i) in DIAGNOSIS_LABEL_CN" :key="i" class="text-center">
                    <div class="text-sm font-bold text-purple-400">{{ diagnosisScores[DIAGNOSIS_LABELS[i]] }}</div>
                    <div class="text-[9px] text-gray-500">{{ label }}</div>
                  </div>
                </div>
              </div>

              <div v-if="displayedResult" class="markdown-body max-w-full">
                <div v-html="marked.parse(displayedResult)"></div>
                <span v-if="!isComplete" class="inline-block w-2 h-[1.2em] bg-purple-500 animate-pulse rounded-sm ml-0.5 align-middle"></span>
              </div>

              <div v-else-if="isDiagnosing" class="flex flex-col items-center justify-center h-full text-center">
                <div class="relative mb-6">
                  <div class="w-20 h-20 rounded-2xl bg-purple-500/[0.04] border border-purple-500/[0.08] flex items-center justify-center">
                    <Loader2 class="w-8 h-8 text-purple-400 animate-spin" />
                  </div>
                  <div class="absolute -inset-2 rounded-2xl bg-purple-500/[0.02] blur-xl animate-pulse"></div>
                </div>
                <p class="text-purple-300/80 text-sm font-medium">导师正在查阅你的职业档案...</p>
                <p class="text-gray-600 text-xs mt-2 max-w-[240px]">正在深度分析简历、目标岗位与 JD，为你出具精准诊断报告</p>
              </div>

              <div v-else class="flex flex-col items-center justify-center h-full text-center">
                <div class="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-center mb-4">
                  <FileText class="w-7 h-7 text-gray-600" />
                </div>
                <p class="text-gray-500 text-sm">在左侧输入简历信息</p>
                <p class="text-gray-600 text-xs mt-1.5 max-w-[220px]">点击"开始深度诊断"，AI 将对照 JD 逐条剖析，提供优化方案</p>
              </div>
            </div>

            <!-- 底部：模拟面试入口 -->
            <div v-if="isComplete" class="px-4 py-3 md:px-6 md:py-4 border-t border-white/[0.04] bg-gradient-to-r from-pink-600/[0.04] to-rose-600/[0.04]">
              <button
                @click="goToMockInterview"
                class="w-full bg-gradient-to-r from-pink-500 to-rose-500 text-white py-3 rounded-xl font-semibold text-sm hover:shadow-lg hover:shadow-pink-500/20 transition-all duration-300 hover:-translate-y-0.5 flex items-center justify-center gap-2 group"
              >
                <svg class="w-4 h-4 group-hover:rotate-12 transition-transform duration-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 20c0-4 4-7 8-7s8 3 8 7" />
                </svg>
                已根据诊断生成专属题目，立即开启 AI 模拟面试
              </button>
            </div>
          </CyberGlassCard>
    </div>
  </div>
</template>

<style scoped>
*::-webkit-scrollbar {
  width: 5px;
}
*::-webkit-scrollbar-track {
  background: transparent;
}
*::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
}
*::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.12);
}

.upload-zone {
  transition: all 0.3s ease;
}

.markdown-body {
  color: rgba(233, 213, 255, 0.9);
  font-size: 14px;
  line-height: 1.8;
  word-wrap: break-word;
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
  font-weight: 800;
  margin: 0 0 0.5em;
  padding-bottom: 0.25em;
  background: linear-gradient(135deg, #c084fc, #818cf8);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid rgba(168, 85, 247, 0.12);
}

.markdown-body :deep(h2) {
  font-size: 1.25em;
  font-weight: 700;
  margin: 1em 0 0.4em;
  background: linear-gradient(135deg, #a855f7, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(h3) {
  font-size: 1.08em;
  font-weight: 600;
  margin: 0.7em 0 0.3em;
  background: linear-gradient(135deg, #c084fc, #a78bfa);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(strong), .markdown-body :deep(b) {
  color: #c084fc;
  font-weight: 700;
}

.markdown-body :deep(p) {
  margin: 0.5em 0;
  color: rgba(233, 213, 255, 0.82);
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 1.4em;
  margin: 0.4em 0;
}

.markdown-body :deep(li) {
  margin: 0.25em 0;
  color: rgba(233, 213, 255, 0.78);
}

.markdown-body :deep(li)::marker {
  color: #a855f7;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0.8em 0;
  border: 1px solid rgba(168, 85, 247, 0.12);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.15);
}

.markdown-body :deep(thead) { background: rgba(168, 85, 247, 0.06); }

.markdown-body :deep(th) {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #c084fc;
  font-size: 12px;
  border-bottom: 1px solid rgba(168, 85, 247, 0.15);
}

.markdown-body :deep(td) {
  padding: 7px 12px;
  font-size: 12px;
  color: rgba(233, 213, 255, 0.75);
  border-bottom: 1px solid rgba(168, 85, 247, 0.06);
}

.markdown-body :deep(tr:hover td) { background: rgba(168, 85, 247, 0.04); }

.markdown-body :deep(blockquote) {
  border-left: 2px solid rgba(168, 85, 247, 0.3);
  padding: 0.3em 0.8em;
  margin: 0.6em 0;
  background: rgba(168, 85, 247, 0.03);
  border-radius: 0 6px 6px 0;
  color: rgba(233, 213, 255, 0.65);
}

.markdown-body :deep(code) {
  background: rgba(168, 85, 247, 0.08);
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.88em;
  color: #d8b4fe;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(168, 85, 247, 0.1);
  border-radius: 8px;
  padding: 0.8em;
  overflow-x: auto;
  margin: 0.6em 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: rgba(233, 213, 255, 0.82);
}

.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.2), transparent);
  margin: 1.2em 0;
}
</style>
