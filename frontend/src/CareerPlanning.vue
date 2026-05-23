<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Compass, Map, Target, Loader2, FileText, Copy, Download, Route, Flag, Wrench, UserCircle2 } from 'lucide-vue-next'
import { marked } from 'marked'
import FeaturePageShell from './components/FeaturePageShell.vue'
import ActionDock from './components/ActionDock.vue'
import SidebarEducationPlaceholder from './components/SidebarEducationPlaceholder.vue'
import GlobalProviderSwitcher from './components/GlobalProviderSwitcher.vue'
import { showToast, resolveLoader } from '@/utils/uiFallbacks.js'
import { upsertSession, generateSessionId } from '@/services/historyClient.js'
import { useUserStore } from '@/stores/userStore'
import { useLlmProviderStore } from '@/stores/llmProviderStore'

const userStore = useUserStore()
const llmProviderStore = useLlmProviderStore()

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const router = useRouter()
const route = useRoute()

const isRestoring = ref(false)

// 当前规划会话 ID（用于 session upsert 幂等保存）
const currentSessionId = ref(generateSessionId('career'))

const resumeText = ref('')
const userConfusion = ref('')
const reportResult = ref('')
const displayedResult = ref('')
const isGenerating = ref(false)
const isComplete = ref(false)
const error = ref('')

const resultContainer = ref(null)

// 通过 uiFallbacks.resolveLoader() 异步解析 StreamingLoader 组件，
// 缺失时降级到 InlineLoaderFallback（受 Requirement 8.6 / 8.8 约束）
const Loader = shallowRef(null)

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

// FeaturePageShell stage badges：路线图 / 阶段目标 / 能力缺口
const stageBadges = [
  { label: '路线图', tone: 'cyan' },
  { label: '阶段目标', tone: 'blue' },
  { label: '能力缺口', tone: 'purple' }
]

// 用户画像卡的展示字段（仅前端 UI 拼接，不影响业务请求体）
const profileTargetJob = computed(() => userStore.targetJob || '')
const profileResumePreview = computed(() => {
  const text = (resumeText.value || '').trim()
  if (!text) return ''
  return text.length > 120 ? text.slice(0, 120) + '…' : text
})
const profileCharCount = computed(() => (resumeText.value || '').length)

// 路线占位卡：0-3 / 3-6 / 6-12 月（仅展示层信息架构，不发起请求）
const ROADMAP_PLACEHOLDERS = [
  {
    range: '0 — 3 个月',
    title: '快速立足期',
    desc: '梳理简历高频词、补齐基础硬技能、产出 1-2 个可展示作品。',
    icon: Flag,
    accent: 'cyan'
  },
  {
    range: '3 — 6 个月',
    title: '能力跃迁期',
    desc: '攻克目标方向核心技术栈，做出 1 个能写进简历的中型项目。',
    icon: Route,
    accent: 'blue'
  },
  {
    range: '6 — 12 个月',
    title: '影响力沉淀期',
    desc: '行业人脉 + 个人品牌 + 行动复盘，准备目标岗位面试与谈薪。',
    icon: Compass,
    accent: 'purple'
  }
]

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
    showToast('已复制蓝图到剪贴板', { type: 'success' })
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = reportResult.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    showToast('已复制蓝图到剪贴板', { type: 'success' })
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
    // 客户端预校验提示走 showToast，不污染 error.value（后者保留给后端透传错误）
    showToast('请输入您的职业困惑或未来期望', { type: 'error' })
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
        user_confusion: userConfusion.value,
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
                reportResult.value += content
                scrollToBottom()
              }
            } catch {}
          } else if (currentEvent === 'error') {
            // SSE error 事件：直接透传后端 message，禁止前缀/后缀/模板包装（用户补充约束 a）
            try {
              const parsed = JSON.parse(dataStr)
              const msg = parsed?.payload?.message || parsed?.message || ''
              if (msg) error.value = msg
            } catch {}
          }
        }
      }
    }

    if (displayedResult.value) {
      isComplete.value = true

      // ── 自动保存到 PostgreSQL（session upsert，幂等） ──
      try {
        await upsertSession(currentSessionId.value, {
          record_type: 'career_plan',
          user_input: (userConfusion.value || '').slice(0, 200),
          ai_result: (reportResult.value || '').slice(0, 5000),
          scores: {},
          extra_data: {
            resume_text: (resumeText.value || '').slice(0, 3000),
            user_confusion: userConfusion.value,
            target_goal: userStore.targetGoal || ''
          },
          chat_history: [
            { role: 'user', content: userConfusion.value },
            { role: 'ai', content: (reportResult.value || '').slice(0, 5000) }
          ]
        })
      } catch (saveErr) {
        console.error('职业规划自动保存失败:', saveErr)
      }
    }
  } catch (err) {
    console.error('职业规划请求失败:', err)
    // 错误透传纪律：直接展示后端 / 网络层原始 message，不再添加任何前缀 / 后缀 / 模板包装
    error.value = err && err.message ? err.message : '网络连接异常，请重试'
  } finally {
    isGenerating.value = false
  }
}

onMounted(async () => {
  // 异步解析 Loader 组件（真实 StreamingLoader.vue 缺失时降级到 InlineLoaderFallback）
  Loader.value = await resolveLoader()

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

  // 简历来源：优先 userStore，降级 localStorage（保持向后兼容）
  const sourceResume = userStore.resumeText || localStorage.getItem('resume_text') || ''
  if (sourceResume) {
    resumeText.value = sourceResume
    isResumeValid.value = sourceResume.trim().length >= 20
    if (isResumeValid.value) loadSuggestions()
  }
})

onUnmounted(() => {})
</script>

<template>
  <div class="min-h-[100dvh] relative overflow-hidden bg-[#020205]">
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

    <!-- 主内容：FeaturePageShell 三段骨架（Hero / Control / Result） -->
    <div class="relative z-10 w-full min-h-[100dvh] pt-14 pb-6 overflow-y-auto">
      <div class="max-w-[1280px] mx-auto px-4 md:px-6">
        <FeaturePageShell
          title="职业规划"
          subtitle="阶段路线 · 能力缺口 · 行动蓝图"
          :stageBadges="stageBadges"
          variant="default"
          max-width="1280px"
        >
          <!-- 自定义 Hero：保留品牌叙事 + 系统状态徽章 -->
          <template #hero>
            <div class="flex flex-col gap-3 px-1">
              <div class="flex items-start justify-between gap-4 flex-wrap">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                    <Compass class="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 class="text-2xl md:text-3xl font-bold text-white tracking-tight" data-test="career-page-title">
                      🧭 职业规划
                    </h1>
                    <p class="text-xs md:text-sm text-cyan-200/80 mt-1">
                      {{ isGenerating ? '导师正在查阅你的职业档案…' : '阶段路线 · 能力缺口 · 行动蓝图' }}
                    </p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <GlobalProviderSwitcher :compact="true" placement="bottom-right" />
                </div>
              </div>
              <!-- 三阶段徽章：路线图 / 阶段目标 / 能力缺口 -->
              <div class="flex flex-wrap gap-2 mt-1" data-test="career-stage-badges">
                <span
                  v-for="(badge, i) in stageBadges"
                  :key="i"
                  data-test="stage-badge"
                  class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border backdrop-blur-md"
                  :class="{
                    'text-cyan-300 border-cyan-500/40 bg-cyan-500/10 shadow-[0_0_12px_rgba(6,182,212,0.18)]': badge.tone === 'cyan',
                    'text-blue-300 border-blue-500/40 bg-blue-500/10 shadow-[0_0_12px_rgba(59,130,246,0.18)]': badge.tone === 'blue',
                    'text-purple-300 border-purple-500/40 bg-purple-500/10 shadow-[0_0_12px_rgba(168,85,247,0.18)]': badge.tone === 'purple'
                  }"
                >
                  {{ badge.label }}
                </span>
              </div>
            </div>
          </template>

          <!-- ============ Control：画像卡 + 困惑输入（左 5 / 右 7） ============ -->
          <template #control>
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
              <!-- ── 左侧：用户画像卡 + 升学占位（跨 5 列） ── -->
              <div class="lg:col-span-5 space-y-3">
                <SidebarEducationPlaceholder />

                <!-- 用户画像卡 -->
                <div class="profile-card rounded-xl border bg-white/[0.02] backdrop-blur-xl p-4 transition-all duration-300"
                  :class="isResumeValid ? 'profile-card--valid' : 'profile-card--missing'">
                  <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                      <UserCircle2 class="w-5 h-5" :class="isResumeValid ? 'text-cyan-300' : 'text-amber-300'" />
                      <h2 class="text-sm font-bold" :class="isResumeValid ? 'text-cyan-300' : 'text-amber-300'">用户画像</h2>
                    </div>
                    <span
                      v-if="isResumeValid"
                      class="text-[10px] font-medium text-emerald-300/90 px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10"
                    >已读取 · 将参与规划</span>
                    <span
                      v-else
                      class="text-[10px] font-medium text-amber-300/90 px-2 py-0.5 rounded-full border border-amber-500/30 bg-amber-500/10"
                    >未读取 · 走通用规划</span>
                  </div>

                  <template v-if="isResumeValid">
                    <div class="space-y-2 text-xs">
                      <div class="flex items-baseline gap-2">
                        <span class="text-cyan-400/70 w-16 flex-shrink-0">目标岗位</span>
                        <span class="text-cyan-100">{{ profileTargetJob || '—' }}</span>
                      </div>
                      <div class="flex items-baseline gap-2">
                        <span class="text-cyan-400/70 w-16 flex-shrink-0">简历字数</span>
                        <span class="text-cyan-100 font-mono">{{ profileCharCount }} 字</span>
                      </div>
                      <div class="flex items-start gap-2 pt-1 border-t border-cyan-500/15">
                        <span class="text-cyan-400/70 w-16 flex-shrink-0 mt-0.5">简历摘要</span>
                        <p class="text-cyan-100/80 leading-relaxed">{{ profileResumePreview }}</p>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <p class="text-xs text-amber-200/85 leading-relaxed">
                      暂未读取简历内容，AI 将基于你右侧的"职业困惑"生成<strong class="text-amber-100">通用规划</strong>。<br />
                      想得到更贴合简历的方案？回到简历诊断完成上传，再回到此页即可。
                    </p>
                  </template>
                </div>
              </div>

              <!-- ── 右侧：职业困惑输入区（跨 7 列） ── -->
              <div class="lg:col-span-7 space-y-3">
                <div>
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <Target class="w-5 h-5 text-cyan-400" />
                      <h2 class="text-sm font-bold text-cyan-300">你的职业困惑</h2>
                    </div>
                    <span class="text-[10px] text-cyan-400/60 font-mono hidden sm:block">背景 · 目标 · 时间窗 · 限制</span>
                  </div>
                  <textarea
                    v-model="userConfusion"
                    rows="6"
                    placeholder="例如：我现在在传统行业做运营，想转前端开发，希望 6 个月内拿到一线大厂的初级前端 offer，业余时间每天 2-3 小时，应该如何规划？"
                    class="career-confusion-textarea w-full rounded-xl px-4 py-3 text-sm md:text-base resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 border border-cyan-500/20 text-cyan-100 placeholder-cyan-300/45 focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-500/25 focus:shadow-[0_0_24px_rgba(34,211,238,0.18)] min-h-[180px]"
                    data-test="career-confusion-input"
                  ></textarea>
                  <p class="mt-1.5 text-[11px] text-cyan-300/55 leading-relaxed">
                    输入越具体（当前背景、目标方向、时间窗口、限制条件），AI 的规划越精准。
                  </p>
                </div>

                <!-- 快捷困惑 Chips -->
                <div class="flex flex-wrap gap-2" data-test="career-suggestion-chips">
                  <template v-if="isLoadingSuggestions">
                    <div v-for="i in 4" :key="'skel-'+i" class="px-3 py-1.5 rounded-full text-[11px] font-medium border border-cyan-500/10 bg-cyan-500/5 animate-pulse">
                      <span class="inline-block w-24 h-3 bg-cyan-500/10 rounded"></span>
                    </div>
                    <p class="w-full text-[10px] text-cyan-400/40 mt-1">AI 正在深度剖析您的简历，生成专属问题…</p>
                  </template>
                  <template v-else>
                    <button
                      v-for="(chip, i) in recommendedQuestions"
                      :key="i"
                      @click="fillConfusion(chip)"
                      data-test="career-suggestion-chip"
                      class="chip-btn px-3 py-1.5 rounded-full text-[11px] font-medium transition-all duration-300 border border-cyan-500/20 text-cyan-400/75 hover:text-cyan-200 hover:border-cyan-500/55 hover:shadow-[0_0_12px_rgba(6,182,212,0.20)] hover:bg-cyan-500/5"
                    >
                      {{ chip }}
                    </button>
                  </template>
                </div>
              </div>
            </div>

            <div class="px-2">
              <!-- ActionDock：聚合「生成蓝图」(primary) + 「复制 / 导出」(secondary) -->
              <ActionDock align="right" :sticky="false">
                <template #secondary>
                  <transition name="fade">
                    <div v-if="isComplete" class="flex items-center gap-2 flex-wrap">
                      <button
                        @click="copyReport"
                        data-test="career-copy-btn"
                        class="action-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-1.5 border border-cyan-500/30 text-cyan-300 hover:text-cyan-200 hover:border-cyan-400/60 hover:shadow-[0_0_15px_rgba(6,182,212,0.25)] bg-blue-950/40"
                      >
                        <Copy class="w-3.5 h-3.5" />
                        一键复制蓝图
                      </button>
                      <button
                        @click="exportTxt"
                        data-test="career-export-btn"
                        class="action-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-1.5 border border-cyan-500/30 text-cyan-300 hover:text-cyan-200 hover:border-cyan-400/60 hover:shadow-[0_0_15px_rgba(6,182,212,0.25)] bg-blue-950/40"
                      >
                        <Download class="w-3.5 h-3.5" />
                        导出为 TXT
                      </button>
                    </div>
                  </transition>
                </template>
                <template #primary>
                  <button
                    @click="generatePlan"
                    :disabled="isGenerating || !userConfusion.trim()"
                    data-test="career-generate-btn"
                    class="generate-btn min-w-[200px] px-6 py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] disabled:bg-none disabled:bg-gray-600/30 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50 hover:from-cyan-400 hover:to-blue-500"
                  >
                    <span class="generate-btn-shimmer"></span>
                    <Loader2 v-if="isGenerating" class="w-4 h-4 animate-spin relative z-10" />
                    <Compass v-else class="w-4 h-4 relative z-10" />
                    <span class="relative z-10">{{ isGenerating ? '生成蓝图中...' : '生成专属职业蓝图' }}</span>
                  </button>
                </template>
              </ActionDock>

              <!-- 错误展示区：错误透传纪律 —— textContent 严格等于后端 message，无任何包装文案 -->
              <div
                v-if="error"
                data-test="error-display"
                class="mt-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-300 text-center"
              >{{ error }}</div>
            </div>
          </template>

          <!-- ============ Result：流式 Markdown 蓝图 + 路线图占位 ============ -->
          <template #result>
            <div ref="resultContainer" class="career-result-zone overflow-y-auto p-4 md:p-8 min-h-[320px] max-h-[78vh]">
              <div
                v-if="displayedResult"
                class="markdown-body max-w-full"
                data-test="career-blueprint"
              >
                <div v-html="parsedReport"></div>
                <span v-if="!isComplete" class="inline-block w-2 h-[1.2em] bg-cyan-500 animate-pulse rounded-sm ml-0.5 align-middle"></span>
              </div>

              <div v-else-if="isGenerating" class="flex flex-col items-center justify-center py-10 text-center" data-test="career-loading">
                <component
                  :is="Loader"
                  v-if="Loader"
                  label="导师正在查阅你的职业档案..."
                />
                <p class="text-gray-500 text-xs mt-3 max-w-[280px]">正在深度分析简历与职业困惑，为你绘制专属职业蓝图。</p>
              </div>

              <!-- 空状态：路线图三段占位 + 输出说明 -->
              <div v-else class="career-empty space-y-5" data-test="career-empty">
                <div class="flex items-start gap-3">
                  <div class="w-10 h-10 rounded-xl bg-cyan-500/[0.08] border border-cyan-500/[0.20] flex items-center justify-center flex-shrink-0 shadow-[0_0_18px_rgba(6,182,212,0.12)]">
                    <Map class="w-4 h-4 text-cyan-300" />
                  </div>
                  <div>
                    <p class="text-gray-100 text-sm font-medium">输入你的职业困惑，开启 AI 蓝图生成</p>
                    <p class="text-gray-500 text-xs mt-1 leading-relaxed">
                      AI 将结合简历与目标，输出三段路线图、能力缺口对照、以及可立即执行的行动任务。
                    </p>
                  </div>
                </div>

                <!-- 路线图占位卡：0-3 / 3-6 / 6-12 月 -->
                <div class="roadmap-grid grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div
                    v-for="step in ROADMAP_PLACEHOLDERS"
                    :key="step.range"
                    class="roadmap-card group rounded-xl border bg-white/[0.02] backdrop-blur-md p-4 transition-all duration-300"
                    :class="`roadmap-card--${step.accent}`"
                  >
                    <div class="flex items-center gap-2 mb-1.5">
                      <span class="roadmap-card__icon w-7 h-7 rounded-lg flex items-center justify-center">
                        <component :is="step.icon" class="w-3.5 h-3.5" />
                      </span>
                      <span class="text-[11px] font-mono tracking-wide" :class="{
                        'text-cyan-300': step.accent === 'cyan',
                        'text-blue-300': step.accent === 'blue',
                        'text-purple-300': step.accent === 'purple'
                      }">{{ step.range }}</span>
                    </div>
                    <h4 class="text-sm font-semibold text-gray-100 mb-1">{{ step.title }}</h4>
                    <p class="text-[11px] text-gray-400 leading-relaxed">{{ step.desc }}</p>
                  </div>
                </div>

                <!-- 能力缺口预告 -->
                <div class="rounded-xl border border-cyan-500/15 bg-cyan-500/[0.03] p-3 flex items-center gap-3">
                  <span class="w-7 h-7 rounded-lg bg-cyan-500/15 text-cyan-300 flex items-center justify-center flex-shrink-0">
                    <Wrench class="w-3.5 h-3.5" />
                  </span>
                  <div>
                    <p class="text-xs text-gray-200 font-medium">能力缺口清单</p>
                    <p class="text-[11px] text-gray-500 mt-0.5">完成生成后，AI 会列出"已具备 / 缺口 / 优先补齐"三栏，并附上可执行的学习路径。</p>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </FeaturePageShell>
      </div>
    </div>
  </div>
</template>

<style scoped>
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

/* ── 用户画像卡 ─────────────────────────────────────────── */
.profile-card--valid {
  border-color: rgba(34, 211, 238, 0.22);
  box-shadow: inset 0 0 18px rgba(34, 211, 238, 0.05);
}
.profile-card--missing {
  border-color: rgba(245, 158, 11, 0.22);
  background: rgba(245, 158, 11, 0.04);
}

/* ── 路线图占位卡 ───────────────────────────────────────── */
.roadmap-card {
  position: relative;
  transition: transform 0.2s ease-out, border-color 0.2s, box-shadow 0.2s;
}
.roadmap-card:hover {
  transform: translateY(-2px);
}
.roadmap-card--cyan   { border-color: rgba(34,211,238,0.25); }
.roadmap-card--blue   { border-color: rgba(59,130,246,0.25); }
.roadmap-card--purple { border-color: rgba(168,85,247,0.25); }
.roadmap-card--cyan:hover   { box-shadow: 0 0 22px rgba(34,211,238,0.18); }
.roadmap-card--blue:hover   { box-shadow: 0 0 22px rgba(59,130,246,0.18); }
.roadmap-card--purple:hover { box-shadow: 0 0 22px rgba(168,85,247,0.18); }
.roadmap-card--cyan .roadmap-card__icon   { background: rgba(34,211,238,0.14);  color: #67e8f9; }
.roadmap-card--blue .roadmap-card__icon   { background: rgba(59,130,246,0.14);  color: #93c5fd; }
.roadmap-card--purple .roadmap-card__icon { background: rgba(168,85,247,0.14);  color: #d8b4fe; }
.roadmap-card::after {
  /* 路线图卡顶部渐变线，指示"阶段顺序" */
  content: '';
  position: absolute;
  top: 0; left: 16px; right: 16px; height: 1px;
  background: linear-gradient(90deg, transparent, currentColor, transparent);
  opacity: 0.35;
  pointer-events: none;
}
.roadmap-card--cyan::after   { color: #22d3ee; }
.roadmap-card--blue::after   { color: #3b82f6; }
.roadmap-card--purple::after { color: #a855f7; }

@media (prefers-reduced-motion: reduce) {
  .roadmap-card { transition: none; }
  .roadmap-card:hover { transform: none; }
}

.markdown-body {
  color: rgba(207, 250, 254, 0.92);
  font-size: 14px;
  line-height: 1.95;
  word-wrap: break-word;
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
  font-weight: 800;
  margin: 0 0 0.6em;
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
  margin: 1.3em 0 0.55em;
  background: linear-gradient(135deg, #06b6d4, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body :deep(h3) {
  font-size: 1.08em;
  font-weight: 600;
  margin: 0.95em 0 0.4em;
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
  margin: 0.75em 0;
  color: rgba(207, 250, 254, 0.85);
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 1.7em;
  margin: 0.65em 0;
}

.markdown-body :deep(li) {
  margin: 0.45em 0;
  color: rgba(207, 250, 254, 0.86);
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
  color: rgba(207, 250, 254, 0.82);
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
