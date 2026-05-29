<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { FileText, ArrowLeft, Paperclip, Sparkles, Bot, Loader2, ScanLine, Target, Briefcase, ListChecks, BookOpen, PenTool } from 'lucide-vue-next'
import { marked } from 'marked'
import { parseFile } from '@/utils/ocrHelper.js'
import { ACCEPTED_EXTENSIONS, validateFile } from '@/utils/fileConstants.js'
import { showToast, resolveLoader } from '@/utils/uiFallbacks'
import CyberRadarChart from '@/components/CyberRadarChart.vue'
import FeaturePageShell from '@/components/FeaturePageShell.vue'
import ActionDock from '@/components/ActionDock.vue'
import SidebarEducationPlaceholder from '@/components/SidebarEducationPlaceholder.vue'
import GlobalProviderSwitcher from '@/components/GlobalProviderSwitcher.vue'
import TTSButton from '@/components/TTSButton.vue'
import { getAuthHeaders } from '@/services/authService.js'
import { upsertSession, generateSessionId, loadRecordById } from '@/services/historyClient.js'
import { useUserStore } from '@/stores/userStore'
import { useLlmProviderStore } from '@/stores/llmProviderStore'
const userStore = useUserStore()
const llmProviderStore = useLlmProviderStore()

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const router = useRouter()
const route = useRoute()

const isRestoring = ref(false)

// 当前诊断会话 ID（用于 session upsert 幂等保存）
const currentSessionId = ref(generateSessionId('resume'))

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

// 三阶段徽章：扫描 / 诊断 / 报告
const STAGE_BADGES = [
  { label: '扫描', tone: 'purple' },
  { label: '诊断', tone: 'purple' },
  { label: '报告', tone: 'purple' }
]

// 报告区空状态的"诊断完成后会得到什么"四张预告卡（仅展示层信息架构）
const REPORT_PREVIEW_CARDS = [
  {
    label: '匹配度',
    title: '岗位匹配度',
    desc: '六维评分 + 综合分，量化简历与目标岗位的契合程度。',
    icon: Target,
    accent: 'purple'
  },
  {
    label: '关键词缺口',
    title: '关键词缺口',
    desc: '识别 JD 中出现但简历未覆盖的硬技能与软技能词。',
    icon: ListChecks,
    accent: 'cyan'
  },
  {
    label: 'STAR 表达',
    title: 'STAR 表达建议',
    desc: '把"我做了 X"改写成"情境 → 任务 → 行动 → 结果"。',
    icon: BookOpen,
    accent: 'pink'
  },
  {
    label: '改写建议',
    title: '可直接改写的语句',
    desc: '逐条给出可粘回简历的优化句式与量化补充。',
    icon: PenTool,
    accent: 'emerald'
  }
]

// 将诊断分数转换为 CyberRadarChart 所需的 chartData 格式
const cyberRadarChartData = computed(() => ({
  indicators: DIAGNOSIS_LABEL_CN.map(name => ({ name, max: 100 })),
  values: DIAGNOSIS_LABELS.map(key => diagnosisScores.value[key])
}))

// 简历字符数（用于扫描仪面板的实时计数显示，不影响业务逻辑）
const resumeCharCount = computed(() => (resumeText.value || '').length)
const jdCharCount = computed(() => (jdText.value || '').length)

// 表单完整度（仅 UI 提示用）：简历必填、目标岗位 + JD 加分
const formReadiness = computed(() => {
  let score = 0
  if ((resumeText.value || '').trim().length >= 20) score += 60
  if ((targetRole.value || '').trim()) score += 20
  if ((jdText.value || '').trim().length >= 30) score += 20
  return Math.min(100, score)
})

// 预解析 StreamingLoader（缺失时降级到内联实现）—— 不在本文件内重复实现降级（Requirement 8.8）
const StreamingLoaderComp = ref(null)
resolveLoader().then(c => { StreamingLoaderComp.value = c })

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
    showToast(validation.error, { type: 'error' })
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
      showToast('文件内容为空或未识别到文字，请检查后重试', { type: 'error' })
      return
    }

    resumeText.value = text
    if (file.type.startsWith('image/')) {
      localStorage.setItem('resume_text', text.trim())
    }
  } catch (e) {
    showToast(e.message || '文件解析失败，请重试', { type: 'error' })
  } finally {
    isParsing.value = false
    isScanPdfDetected.value = false
  }
}

const startDiagnosis = async () => {
  if (!resumeText.value.trim()) {
    showToast('请先粘贴简历内容或上传简历文件', { type: 'error' })
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
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        resume_text: resumeText.value,
        target_role: targetRole.value,
        jd_text: jdText.value,
        provider_id: llmProviderStore.getCurrentProviderId() || undefined
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
        // Phase 1：打通 Dashboard 右侧雷达图 —— 简历诊断完成时写入 resume 快照
        userStore.updateRadarFromResume(scores)
      }
      const cleanedDisplay = displayedResult.value.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
      displayedResult.value = cleanedDisplay
      const cleanedDiagnosis = diagnosisResult.value.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
      diagnosisResult.value = cleanedDiagnosis

      // ── 自动保存到 PostgreSQL（session upsert，幂等） ──
      try {
        await upsertSession(currentSessionId.value, {
          record_type: 'resume_diagnosis',
          user_input: `目标岗位：${targetRole.value || '未指定'}`,
          ai_result: cleanedDiagnosis.slice(0, 5000),
          scores: scores || diagnosisScores.value,
          extra_data: {
            resume_text: resumeText.value.slice(0, 3000),
            target_role: targetRole.value,
            jd_text: jdText.value.slice(0, 2000)
          },
          chat_history: [
            { role: 'user', content: `简历诊断请求 - 目标岗位：${targetRole.value || '未指定'}` },
            { role: 'ai', content: cleanedDiagnosis.slice(0, 5000) }
          ]
        })
      } catch (saveErr) {
        console.error('简历诊断自动保存失败:', saveErr)
        // 保存失败不阻断诊断结果展示
      }
    }
  } catch (err) {
    console.error('诊断请求失败:', err)
    // 错误透传纪律：直接展示原始错误内容；仅在 message 缺失时使用 llm_service.js 既定的兜底字符串
    error.value = err && err.message ? err.message : '网络连接异常，请重试'
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
      const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history/${recordId}`, {
        headers: { ...getAuthHeaders() }
      })
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
                // Phase 1：历史记录恢复时同步更新雷达图快照
                userStore.updateRadarFromResume(scores)
              }
            } catch {}
          }

          const cleanedResult = rawResult.replace(/```json\s*[\s\S]*?\s*```/g, '').trim()
          diagnosisResult.value = cleanedResult
          displayedResult.value = cleanedResult

          // 恢复 session_id，后续再保存时 upsert 到同一条记录
          if (record.session_id) {
            currentSessionId.value = record.session_id
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
    uploadedFileName.value = '已加载全局简历'
  }

  // 优先读 userStore，降级兼容 target_role / target_job 两个键名
  targetRole.value = userStore.targetJob
    || localStorage.getItem('target_role')
    || localStorage.getItem('target_job')
    || ''

  // 补全 jdText 读取（原先完全缺失），多键名降级策略与 PremiumInterview 保持一致
  jdText.value = userStore.jobDescription
    || localStorage.getItem('job_description')
    || localStorage.getItem('current_interview_jd')
    || localStorage.getItem('jd_content')
    || ''
}

onMounted(() => { initResume() })
onUnmounted(() => {})
</script>

<template>
  <div class="resume-page min-h-[100dvh] bg-[#020205] text-gray-300 relative overflow-x-hidden">
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

    <!-- 顶部 AI Provider 切换器（compact） -->
    <div class="absolute top-4 right-4 z-20">
      <GlobalProviderSwitcher :compact="true" placement="bottom-right" />
    </div>

    <!-- 主内容：侧边栏 + Shell 主体 -->
    <div class="relative z-10 flex flex-col lg:flex-row gap-4 lg:gap-6 px-3 md:px-6 pt-14 pb-8 max-w-[1280px] mx-auto">
      <!-- 侧边栏：升学占位（顶部 / 左侧） -->
      <aside class="w-full lg:w-[220px] lg:flex-shrink-0 lg:sticky lg:top-14 lg:self-start">
        <SidebarEducationPlaceholder data-test="sidebar-placeholder" />
      </aside>

      <!-- Shell 主体 -->
      <main class="flex-1 min-w-0">
        <FeaturePageShell
          title="简历诊断"
          subtitle="AI 简历扫描 · JD 匹配 · STAR 表达优化"
          :stageBadges="STAGE_BADGES"
          variant="purple"
          max-width="1280px"
        >
          <!-- ============ Control 区：左输入 / 右目标 + JD ============ -->
          <template #control>
            <div class="control-grid grid grid-cols-1 lg:grid-cols-12 gap-4 p-2">
              <!-- ── 左侧：扫描仪上传 + 简历预览（跨 7 列） ── -->
              <div class="lg:col-span-7 space-y-3">
                <div class="flex items-center justify-between">
                  <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                    <ScanLine class="w-3.5 h-3.5 text-purple-400" />
                    简历扫描入口
                  </h3>
                  <span class="text-[10px] text-gray-500 font-mono">
                    SCAN STATUS · {{ isParsing ? 'PARSING' : (resumeCharCount > 0 ? 'READY' : 'IDLE') }}
                  </span>
                </div>

                <!-- 扫描仪 dropzone：扫描线 + 紫色边框辉光 -->
                <div
                  class="scanner-dropzone relative bg-white/[0.02] backdrop-blur-xl border rounded-xl p-5 cursor-pointer transition-all duration-300 overflow-hidden"
                  :class="[
                    dropZoneActive ? 'border-purple-400/60 bg-purple-500/[0.06] shadow-[0_0_28px_rgba(168,85,247,0.20)]' : 'border-white/[0.06]',
                    isParsing ? 'scanner-dropzone--scanning' : '',
                    resumeCharCount > 0 ? 'scanner-dropzone--has-data' : ''
                  ]"
                  @dragover.prevent="dropZoneActive = true; isDragging = true"
                  @dragleave.prevent="dropZoneActive = false; isDragging = false"
                  @drop.prevent="handleFileDrop"
                  data-test="upload-dropzone"
                >
                  <input type="file" ref="fileInput" class="hidden" :accept="ACCEPTED_EXTENSIONS" @change="handleFileSelect" />
                  <div class="scanner-dropzone__bar" aria-hidden="true"></div>

                  <div class="flex items-center gap-3 relative z-10">
                    <div
                      class="w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-300"
                      :class="dropZoneActive ? 'bg-purple-500/20 ring-1 ring-purple-400/40' : 'bg-white/[0.04]'"
                    >
                      <Paperclip class="w-4 h-4" :class="dropZoneActive ? 'text-purple-300' : 'text-gray-400'" />
                    </div>
                    <div class="flex-1 text-left min-w-0">
                      <p class="text-sm text-gray-200">
                        <span class="text-purple-300 cursor-pointer font-semibold underline-offset-2 hover:underline" @click="$refs.fileInput.click()">点击上传简历</span>
                        <span class="text-gray-400"> 或将文件拖入此处</span>
                      </p>
                      <p class="text-[11px] text-gray-500 mt-0.5">PDF / Word / TXT / JPG / PNG / WEBP · 扫描件自动 OCR</p>
                    </div>
                  </div>

                  <p v-if="uploadedFileName && !isParsing" class="mt-3 text-xs text-purple-300/90 flex items-center gap-1.5 relative z-10">
                    <FileText class="w-3.5 h-3.5" />
                    <span class="truncate">已加载：{{ uploadedFileName }}</span>
                  </p>
                  <div v-if="isParsing" class="mt-3 flex items-center gap-2 relative z-10">
                    <Loader2 class="w-3.5 h-3.5 text-purple-300 animate-spin" />
                    <span class="text-xs text-purple-200">{{ isScanPdfDetected ? '深度视觉扫描中…' : '解析文件中…' }}</span>
                  </div>
                </div>

                <!-- 简历内容预览 -->
                <div class="flex items-center justify-between pt-1">
                  <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">简历正文</h3>
                  <span class="text-[10px] text-gray-500 font-mono">{{ resumeCharCount }} 字</span>
                </div>
                <div class="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3 text-xs md:text-sm text-gray-300 leading-relaxed min-h-[200px] max-h-[320px] overflow-y-auto whitespace-pre-wrap font-mono tracking-[0.01em]">
                  <span v-if="resumeText">{{ resumeText }}</span>
                  <span v-else class="text-gray-500 not-italic">尚未读取简历内容。上传文件、粘贴扫描件，或将文本直接拖入上方扫描入口，简历正文会显示在这里供 AI 分析。</span>
                </div>
              </div>

              <!-- ── 右侧：目标岗位 + JD（跨 5 列） ── -->
              <div class="lg:col-span-5 space-y-3">
                <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                  <Briefcase class="w-3.5 h-3.5 text-purple-400" />
                  目标岗位
                </h3>
                <input
                  v-model="targetRole"
                  type="text"
                  placeholder="如：Java 后端开发工程师"
                  class="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl px-3 py-2 md:px-4 md:py-3 text-sm md:text-base text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25 transition-all duration-300"
                  data-test="target-role-input"
                />

                <div class="flex items-center justify-between pt-1">
                  <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">岗位描述（可选）</h3>
                  <span class="text-[10px] text-gray-500 font-mono">{{ jdCharCount }} 字</span>
                </div>
                <textarea
                  v-model="jdText"
                  placeholder="粘贴目标岗位的 JD 内容，AI 会与简历做关键词与能力匹配……"
                  rows="9"
                  class="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl px-3 py-2 md:px-4 md:py-3 text-xs md:text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25 transition-all duration-300 resize-none leading-relaxed min-h-[220px]"
                  data-test="jd-textarea"
                ></textarea>

                <!-- 表单完整度（仅 UI 提示，不影响业务） -->
                <div class="pt-1">
                  <div class="flex items-center justify-between text-[11px] text-gray-500 mb-1">
                    <span>表单完整度</span>
                    <span class="font-mono">{{ formReadiness }}%</span>
                  </div>
                  <div class="h-1 bg-white/5 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-purple-500/70 to-cyan-400/70 transition-all duration-500" :style="{ width: formReadiness + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ActionDock：触发诊断按钮 -->
            <div class="mt-4 px-2">
              <ActionDock align="right">
                <template #primary>
                  <button
                    @click="startDiagnosis"
                    :disabled="isDiagnosing || !resumeText.trim()"
                    class="diagnose-cta bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 md:px-10 py-3 md:py-3.5 rounded-2xl font-semibold text-sm md:text-base shadow-lg shadow-purple-500/20 hover:shadow-xl hover:shadow-purple-500/40 hover:from-purple-500 hover:to-indigo-500 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:bg-none disabled:bg-gray-600/30 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed disabled:hover:translate-y-0 flex items-center justify-center gap-2"
                    data-test="diagnose-trigger"
                  >
                    <Loader2 v-if="isDiagnosing" class="w-4 h-4 animate-spin" />
                    <ScanLine v-else class="w-4 h-4" />
                    {{ isDiagnosing ? '诊断中...' : '开始深度诊断' }}
                  </button>
                </template>
              </ActionDock>
            </div>

            <!-- 错误展示区域：透传后端 / 网络错误原始内容，禁止任何前缀 / 后缀 / 模板包装文案 -->
            <div
              v-if="error"
              class="mt-3 mx-2 bg-red-500/[0.06] border border-red-500/[0.20] rounded-xl p-3 text-xs text-red-300 text-center"
              data-test="error-display"
              role="alert"
            >{{ error }}</div>
          </template>

          <!-- ============ Result 区：报告标题 + 雷达图 + 流式 Markdown ============ -->
          <template #result>
            <div class="result-zone flex flex-col min-h-[480px]">
              <!-- 报告标题栏 -->
              <div class="px-3 py-2 md:px-4 md:py-3 border-b border-white/[0.05] flex items-center justify-between bg-white/[0.012]">
                <div class="flex items-center gap-2">
                  <Bot class="w-4 h-4 text-purple-400" />
                  <h2 class="text-sm font-semibold text-gray-200" data-test="report-title">AI 诊断报告</h2>
                </div>
                <div class="flex items-center gap-2">
                  <!-- 朗读按钮（Beta）：仅在已有报告内容时显示，streaming 中禁用 -->
                  <TTSButton
                    v-if="displayedResult"
                    variant="inline"
                    :text="displayedResult"
                    :cache-key="`resume:${currentSessionId}:diagnosis`"
                    :disabled="isDiagnosing && !isComplete"
                  />
                  <div v-if="isComplete" class="flex items-center gap-1.5">
                    <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                    <span class="text-xs text-green-400">分析完成</span>
                  </div>
                  <div v-else-if="isDiagnosing" class="flex items-center gap-1.5">
                    <Loader2 class="w-3 h-3 animate-spin text-purple-400" />
                    <span class="text-xs text-purple-300">导师正在查阅你的职业档案…</span>
                  </div>
                  <div v-else class="flex items-center gap-1.5">
                    <div class="w-1.5 h-1.5 rounded-full bg-gray-500/60"></div>
                    <span class="text-xs text-gray-500">待启动</span>
                  </div>
                </div>
              </div>

              <!-- 报告内容 -->
              <div ref="resultContainer" class="flex-1 overflow-y-auto p-4 md:p-6">
                <!-- 六维雷达图 -->
                <div v-if="isComplete" class="mb-6" data-test="radar-container">
                  <div class="flex items-center gap-2 mb-3">
                    <Sparkles class="w-4 h-4 text-purple-400" />
                    <h3 class="text-sm font-semibold text-purple-300">六维简历评分</h3>
                  </div>
                  <CyberRadarChart :chartData="cyberRadarChartData" />
                  <div class="grid grid-cols-6 gap-1 mt-3">
                    <div
                      v-for="(label, i) in DIAGNOSIS_LABEL_CN"
                      :key="i"
                      class="text-center"
                      data-test="report-item"
                    >
                      <div class="text-sm font-bold text-purple-300">{{ diagnosisScores[DIAGNOSIS_LABELS[i]] }}</div>
                      <div class="text-[9px] text-gray-500">{{ label }}</div>
                    </div>
                  </div>
                </div>

                <div v-if="displayedResult" class="markdown-body max-w-full" data-test="report-item">
                  <div v-html="marked.parse(displayedResult)"></div>
                  <span v-if="!isComplete" class="inline-block w-2 h-[1.2em] bg-purple-500 animate-pulse rounded-sm ml-0.5 align-middle"></span>
                </div>

                <div v-else-if="isDiagnosing" class="flex flex-col items-center justify-center h-full text-center min-h-[320px]">
                  <component
                    v-if="StreamingLoaderComp"
                    :is="StreamingLoaderComp"
                    label="导师正在查阅你的职业档案..."
                  />
                  <div v-else class="relative mb-6">
                    <div class="w-20 h-20 rounded-2xl bg-purple-500/[0.04] border border-purple-500/[0.10] flex items-center justify-center">
                      <Loader2 class="w-8 h-8 text-purple-400 animate-spin" />
                    </div>
                    <div class="absolute -inset-2 rounded-2xl bg-purple-500/[0.02] blur-xl animate-pulse"></div>
                  </div>
                  <p class="text-purple-300/85 text-sm font-medium mt-4">导师正在查阅你的职业档案…</p>
                  <p class="text-gray-500 text-xs mt-2 max-w-[260px]">正在深度分析简历、目标岗位与 JD，为你出具精准诊断报告。</p>
                </div>

                <!-- 空状态：4 张预告卡（替代单图标） -->
                <div v-else class="space-y-5">
                  <div class="flex items-start gap-3">
                    <div class="w-10 h-10 rounded-xl bg-purple-500/[0.06] border border-purple-500/[0.15] flex items-center justify-center flex-shrink-0 shadow-[0_0_16px_rgba(168,85,247,0.10)]">
                      <FileText class="w-4 h-4 text-purple-300" />
                    </div>
                    <div>
                      <p class="text-gray-200 text-sm font-medium">填写简历信息后开始深度诊断</p>
                      <p class="text-gray-500 text-xs mt-1 leading-relaxed">诊断完成后，你将在这里得到以下四类输出：</p>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div
                      v-for="card in REPORT_PREVIEW_CARDS"
                      :key="card.label"
                      class="report-preview-card group rounded-xl p-3 border bg-white/[0.02] backdrop-blur-md transition-all duration-300"
                      :class="`report-preview-card--${card.accent}`"
                    >
                      <div class="flex items-center gap-2 mb-1.5">
                        <span class="report-preview-card__icon w-7 h-7 rounded-lg flex items-center justify-center">
                          <component :is="card.icon" class="w-3.5 h-3.5" />
                        </span>
                        <span class="text-xs font-semibold text-gray-200">{{ card.title }}</span>
                      </div>
                      <p class="text-[11px] text-gray-400 leading-relaxed pl-9">{{ card.desc }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 底部：模拟面试入口（保留原有功能入口） -->
              <div v-if="isComplete" class="px-4 py-3 md:px-6 md:py-4 border-t border-white/[0.05] bg-gradient-to-r from-pink-600/[0.05] to-rose-600/[0.05]">
                <button
                  @click="goToMockInterview"
                  class="w-full bg-gradient-to-r from-pink-500 to-rose-500 text-white py-3 rounded-xl font-semibold text-sm hover:shadow-lg hover:shadow-pink-500/25 transition-all duration-300 hover:-translate-y-0.5 flex items-center justify-center gap-2 group"
                  data-test="mock-interview-cta"
                >
                  <svg class="w-4 h-4 group-hover:rotate-12 transition-transform duration-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="8" r="4" />
                    <path d="M4 20c0-4 4-7 8-7s8 3 8 7" />
                  </svg>
                  已根据诊断生成专属题目，立即开启 AI 模拟面试
                </button>
              </div>
            </div>
          </template>
        </FeaturePageShell>
      </main>
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

/* ── 扫描仪 dropzone：扫描线 + 紫色辉光 ────────────────────── */
.scanner-dropzone {
  isolation: isolate;
}
.scanner-dropzone__bar {
  position: absolute;
  inset: -20% 0 auto 0;
  height: 30%;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(168, 85, 247, 0.10) 45%,
    rgba(168, 85, 247, 0.22) 55%,
    transparent 100%
  );
  filter: blur(2px);
  pointer-events: none;
  opacity: 0;
  transform: translateY(0);
  z-index: 0;
}
.scanner-dropzone--scanning .scanner-dropzone__bar {
  opacity: 1;
  animation: scanner-bar-sweep 2.4s ease-in-out infinite;
}
.scanner-dropzone--has-data {
  border-color: rgba(168, 85, 247, 0.30);
  box-shadow: 0 0 18px rgba(168, 85, 247, 0.10) inset;
}
@keyframes scanner-bar-sweep {
  0%   { transform: translateY(0%);   opacity: 0; }
  10%  { opacity: 0.9; }
  90%  { opacity: 0.9; }
  100% { transform: translateY(420%); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .scanner-dropzone--scanning .scanner-dropzone__bar { animation: none; }
}

/* ── 报告区空状态预告卡 ──────────────────────────────────────── */
.report-preview-card {
  transition: transform 0.2s ease-out, border-color 0.2s, box-shadow 0.2s;
}
.report-preview-card:hover {
  transform: translateY(-1px);
}
.report-preview-card--purple   { border-color: rgba(168,85,247,0.25); }
.report-preview-card--cyan     { border-color: rgba(34,211,238,0.25); }
.report-preview-card--pink     { border-color: rgba(236,72,153,0.25); }
.report-preview-card--emerald  { border-color: rgba(16,185,129,0.25); }
.report-preview-card--purple:hover   { box-shadow: 0 0 18px rgba(168,85,247,0.18); }
.report-preview-card--cyan:hover     { box-shadow: 0 0 18px rgba(34,211,238,0.18); }
.report-preview-card--pink:hover     { box-shadow: 0 0 18px rgba(236,72,153,0.18); }
.report-preview-card--emerald:hover  { box-shadow: 0 0 18px rgba(16,185,129,0.18); }
.report-preview-card--purple .report-preview-card__icon  { background: rgba(168,85,247,0.14); color: #d8b4fe; }
.report-preview-card--cyan .report-preview-card__icon    { background: rgba(34,211,238,0.14);  color: #67e8f9; }
.report-preview-card--pink .report-preview-card__icon    { background: rgba(236,72,153,0.14);  color: #f9a8d4; }
.report-preview-card--emerald .report-preview-card__icon { background: rgba(16,185,129,0.14);  color: #6ee7b7; }

.markdown-body {
  color: rgba(233, 213, 255, 0.9);
  font-size: 14px;
  line-height: 1.85;
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
  margin: 0.55em 0;
  color: rgba(233, 213, 255, 0.85);
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.markdown-body :deep(li) {
  margin: 0.3em 0;
  color: rgba(233, 213, 255, 0.82);
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
  color: rgba(233, 213, 255, 0.78);
  border-bottom: 1px solid rgba(168, 85, 247, 0.06);
}

.markdown-body :deep(tr:hover td) { background: rgba(168, 85, 247, 0.04); }

.markdown-body :deep(blockquote) {
  border-left: 2px solid rgba(168, 85, 247, 0.3);
  padding: 0.3em 0.8em;
  margin: 0.6em 0;
  background: rgba(168, 85, 247, 0.03);
  border-radius: 0 6px 6px 0;
  color: rgba(233, 213, 255, 0.7);
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
  color: rgba(233, 213, 255, 0.85);
}

.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.2), transparent);
  margin: 1.2em 0;
}
</style>
