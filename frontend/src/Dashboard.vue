<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { llmService, streamChat } from '@/services/llm_service.js'
import { normalizeRecordType, resolveHistoryRoute, getRecordColorClass, RECORD_TYPES } from '@/utils/historyRecordTypes.js'
import { getAuthHeaders } from '@/services/authService.js'
import { useRouter, useRoute } from 'vue-router'
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import QrcodeVue from 'qrcode.vue'
import { marked } from 'marked'

// Pinia store
import { useUserStore } from '@/stores/userStore'
import { useChatSessionStore } from '@/stores/chatSessionStore'
import { useLlmProviderStore } from '@/stores/llmProviderStore'
import {
  buildResumeRadarData,
  buildInterviewRadarData,
  emptyResumeRadar,
  emptyInterviewRadar,
  hasNonZeroScores
} from '@/utils/radarMapping.js'
import { formatRecordTime, getRecordTimestamp } from '@/utils/dateFormat.js'
import CyberRadarChart from '@/components/CyberRadarChart.vue'
import SetupModal from '@/components/SetupModal.vue'
import DataSourceModal from '@/components/DataSourceModal.vue'
import ChatPreviewModal from '@/components/ChatPreviewModal.vue'
import KnowledgePanel from '@/components/KnowledgePanel.vue'
import ChatDock from '@/components/chat/ChatDock.vue'
import CareerPreviewPanel from '@/components/CareerPreviewPanel.vue'
import GlobalProviderSwitcher from '@/components/GlobalProviderSwitcher.vue'

import { Bot, Bookmark, FileText, MessageSquare, Folder, Settings, Clock, Puzzle, Plus, Search, MoreHorizontal, ChevronLeft, ChevronRight, Upload, CheckCircle, X, Loader2, History, Sparkles, Mic, GraduationCap, Star, Trash2, Compass }
  from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const chatStore = useChatSessionStore()
const llmProviderStore = useLlmProviderStore()
const radarData = computed(() => userStore.radarData)

// ── Radar 手动选择状态（数据面板联动）──────────────────────
// 用户从数据面板选中具体记录后，存储该 record 引用；切换 tab 不清除
const manualResumeRecord = ref(null)
const manualInterviewRecord = ref(null)

// ── Radar tab 独立数据源（每 tab 使用各自原始六维）────────
const displayedRadarData = computed(() => {
  if (activeDataTab.value === 'resume') {
    // 优先：手动选择的简历记录
    if (manualResumeRecord.value) {
      return buildResumeRadarData(manualResumeRecord.value.scores)
    }
    // 兜底：bento 池中最近一次简历诊断（通过 computed 派生）
    const latest = resumeRadarRecords.value[0]
    if (latest) return buildResumeRadarData(latest.scores)
    return emptyResumeRadar()
  }

  if (activeDataTab.value === 'interview') {
    if (manualInterviewRecord.value) {
      return buildInterviewRadarData(manualInterviewRecord.value.scores)
    }
    const latest = interviewRadarRecords.value[0]
    if (latest) return buildInterviewRadarData(latest.scores)
    return emptyInterviewRadar()
  }

  // career tab：返回空态简历指标占位（实际模板不渲染雷达）
  return emptyResumeRadar()
})

// ── 条形列表数据：与 radar chart 同源 ──────────────────────
const displayedRadarItems = computed(() => {
  const data = displayedRadarData.value
  return data.indicators.map((ind, i) => ({
    name: ind.name,
    value: data.values[i] || 0
  }))
})

// ── DataSourceModal 数据源（按当前 tab 筛选）────────────────
const dataSourceRecords = computed(() => {
  if (activeDataTab.value === 'resume') return resumeRadarRecords.value
  if (activeDataTab.value === 'interview') return interviewRadarRecords.value
  if (activeDataTab.value === 'career') return careerRecords.value
  return []
})

// ── 手动选择是否激活（用于显示"恢复最新"按钮）──────────────
const hasManualSelection = computed(() => {
  if (activeDataTab.value === 'resume') return manualResumeRecord.value !== null
  if (activeDataTab.value === 'interview') return manualInterviewRecord.value !== null
  return false
})

const restoreAutoRadar = () => {
  if (activeDataTab.value === 'resume') manualResumeRecord.value = null
  else if (activeDataTab.value === 'interview') manualInterviewRecord.value = null
}

// ── 数据面板选择记录后的联动 ────────────────────────────────
const handleDataSourceSelect = (record) => {
  if (!record) return
  const t = normalizeRecordType(record).type

  // 简历诊断记录
  if (t === RECORD_TYPES.RESUME_DIAGNOSIS) {
    activeDataTab.value = 'resume'
    if (hasNonZeroScores(record.scores)) {
      manualResumeRecord.value = record
      userStore.activeDataSourceId = record.id
      showToastMsg('已切换雷达数据源', 1500)
    } else {
      showToastMsg('该记录暂无评分数据', 2000)
    }
    showDataSourceModal.value = false
    return
  }

  // 模拟面试记录
  if (t === RECORD_TYPES.INTERVIEW) {
    activeDataTab.value = 'interview'
    if (hasNonZeroScores(record.scores)) {
      manualInterviewRecord.value = record
      userStore.activeDataSourceId = record.id
      showToastMsg('已切换雷达数据源', 1500)
    } else {
      showToastMsg('该记录暂无评分数据', 2000)
    }
    showDataSourceModal.value = false
    return
  }

  // 职业规划记录：切到 career tab，打开预览浮窗，不更新 radar
  if (t === RECORD_TYPES.CAREER_PLAN) {
    activeDataTab.value = 'career'
    showDataSourceModal.value = false
    // 定位到该记录在 careerRecords 中的位置
    const idx = careerRecords.value.findIndex(r => r.id === record.id)
    careerPreviewIndex.value = idx >= 0 ? idx : 0
    showCareerPreview.value = true
    return
  }

  // 其他类型：仅关闭弹窗
  showDataSourceModal.value = false
}

// 雷达图数据来源提示（基于当前 tab、手动选择和 bento 池）
const radarSourceHint = computed(() => {
  if (activeDataTab.value === 'resume') {
    if (manualResumeRecord.value) {
      const t = formatRecordTime(manualResumeRecord.value)
      return { label: `当前选择：简历诊断${t ? ' · ' + t : ''}`, type: 'manual' }
    }
    if (resumeRadarRecords.value.length > 0) {
      return { label: '数据来源：最近一次简历诊断', type: 'resume' }
    }
    return { label: '完成简历诊断后生成能力雷达', type: 'empty' }
  }

  if (activeDataTab.value === 'interview') {
    if (manualInterviewRecord.value) {
      const t = formatRecordTime(manualInterviewRecord.value)
      return { label: `当前选择:模拟面试${t ? ' · ' + t : ''}`, type: 'manual' }
    }
    if (interviewRadarRecords.value.length > 0) {
      return { label: '数据来源：最近一次模拟面试', type: 'interview' }
    }
    return { label: '完成模拟面试后生成能力雷达', type: 'empty' }
  }

  return { label: '暂无综合规划评分数据', type: 'empty' }
})

// 考试类型标签映射（升学模式侧边栏展示用）
// 使用 hasOwnProperty 而非 map[key] || fallback，避免原型链属性（如 'toString'）被误判为合法 key
const examTypeLabel = computed(() => {
  const map = {
    'zhuanchaben': '专插本',
    'gaokao': '普通高考',
    'kaoyan': '考研',
    'kaogong': '考公',
    'other': '其他'
  }
  if (Object.prototype.hasOwnProperty.call(map, userStore.examType)) {
    return map[userStore.examType]
  }
  return '未设置'
})


const activeDataTab = ref('resume'); // 'resume' | 'interview' | 'career'

// ── LLM Provider 切换器：已组件化为 GlobalProviderSwitcher.vue
//    Dashboard 顶部 Online 徽章直接使用该组件，本文件不再持有下拉状态。

// ── 职业规划浮窗 ──────────────────────────────────────────
const showCareerPreview = ref(false)
// 当前预览的 career 记录索引（用于上一条/下一条翻阅）
const careerPreviewIndex = ref(0)

// 最近一条 career_plan（取自 bento 池，不再依赖 historyRecords limit=2）
const latestCareerRecord = computed(() => {
  return careerRecords.value[0] || null
})

const openCareerPreview = (index = 0) => {
  careerPreviewIndex.value = Math.max(0, Math.min(index, careerRecords.value.length - 1))
  showCareerPreview.value = true
}
const closeCareerPreview = () => { showCareerPreview.value = false }
const goCareerFull = (recordId = null) => {
  showCareerPreview.value = false
  if (recordId) {
    router.push(`/career-planning?id=${recordId}`)
  } else {
    router.push('/career-planning')
  }
}

// ── 历史记录类型标签 / 颜色 ──
// 单一事实源:走 utils/historyRecordTypes.js 的 normalizeRecordType。
// 旧 category 兼容、新 record_type 映射、未知类型兜底全部收敛到那一处。
const getRecordTypeLabel = (record) => normalizeRecordType(record).label

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const historyRecords = ref([])
const isHistoryLoading = ref(true)

// ── Bento 数据源（独立于首页"继续上次"的最近 2 条）──────────
// 全量历史池（最多 100 条），用于派生三个分类列表
const bentoRecordsPool = ref([])

// 按类型分类 & 排序的最近 10 条记录（computed 派生）
const resumeRadarRecords = computed(() => {
  return bentoRecordsPool.value
    .filter(r => normalizeRecordType(r).type === RECORD_TYPES.RESUME_DIAGNOSIS && hasNonZeroScores(r.scores))
    .sort((a, b) => getRecordTimestamp(b) - getRecordTimestamp(a))
    .slice(0, 10)
})

const interviewRadarRecords = computed(() => {
  return bentoRecordsPool.value
    .filter(r => normalizeRecordType(r).type === RECORD_TYPES.INTERVIEW && hasNonZeroScores(r.scores))
    .sort((a, b) => getRecordTimestamp(b) - getRecordTimestamp(a))
    .slice(0, 10)
})

const careerRecords = computed(() => {
  return bentoRecordsPool.value
    .filter(r => normalizeRecordType(r).type === RECORD_TYPES.CAREER_PLAN)
    // career 不要求 scores
    .sort((a, b) => getRecordTimestamp(b) - getRecordTimestamp(a))
    .slice(0, 10)
})

// 新手启航舱卡片配置（静态数据，不依赖任何响应式数据源）
// Requirements: 7.1, 7.2, 7.3, 7.4, 8.3
const onboardingCards = [
  {
    id: 'resume',
    emoji: '📄',
    title: '简历诊断',
    subtitle: 'Resume Scanner',
    desc: '深度解析过往经历，精准对齐目标岗位。找出致命失分项并提供重构建议，让你的简历一击必中。',
    action: '立即诊断',
    path: '/resume-diagnosis',
    locked: false,
    themeColor: 'purple',
  },
  {
    id: 'interview',
    emoji: '🎙️',
    title: '模拟面试',
    subtitle: 'Combat Simulator',
    desc: '沉浸式 AI 语音实战对练。模拟真实业务场景与高频拷问，生成多维度能力雷达，彻底消除实战恐慌。',
    action: '开启实战',
    path: '/interview',
    locked: false,
    themeColor: 'pink',
  },
  {
    id: 'career',
    emoji: '🗺️',
    title: '职业规划',
    subtitle: 'Career Compass',
    desc: '基于个人特质与行业真实大数据，打破信息壁垒，为你定制科学、清晰的长线职场发展路径。',
    action: '生成路线',
    path: '/career-planning',
    locked: false,
    themeColor: 'blue',
  },
  {
    id: 'education',
    emoji: '🎓',
    title: '升学与避坑',
    subtitle: 'Academic Radar',
    desc: '专插本、考研真实数据导航。帮你平衡繁重的课业规划与升学抉择，绕开前人踩过的坑。',
    action: '模块构筑中...',
    path: null,
    locked: true,
    themeColor: 'emerald',
  },
]

const loadHistory = async () => {
  isHistoryLoading.value = true
  try {
    const res = await fetch(`${API_BASE_URL}/history?limit=2`, {
      headers: { ...getAuthHeaders() }
    })
    if (res.ok) {
      const data = await res.json()
      historyRecords.value = data.records || []
    } else {
      // 非 2xx 响应：保持 historyRecords 为空数组
      historyRecords.value = []
    }
  } catch {
    // 网络错误：保持 historyRecords 为空数组
    historyRecords.value = []
  } finally {
    isHistoryLoading.value = false
  }
}

/**
 * 加载 Bento 数据池（独立于首页"继续上次"的 limit=2 调用）
 *
 * 拉取最近 100 条记录到 bentoRecordsPool，
 * 由 resumeRadarRecords / interviewRadarRecords / careerRecords computed 自动派生。
 *
 * 失败时静默保持空数组，不阻断页面渲染。
 */
const loadDashboardBentoRecords = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/history?limit=100`, {
      headers: { ...getAuthHeaders() }
    })
    if (res.ok) {
      const data = await res.json()
      bentoRecordsPool.value = data.records || []
    } else {
      bentoRecordsPool.value = []
    }
  } catch {
    bentoRecordsPool.value = []
  }
}

// getCategoryLabel / getCategoryColor 历史上接受 category 字符串,
// 现在统一收敛到 utils/historyRecordTypes.js,接受完整 record 即可。
// 保留同名函数避免影响模板/旧调用,但内部一律走 normalizeRecordType。
const getCategoryLabel = (record) => normalizeRecordType(record).label

const getCategoryColor = (record) => getRecordColorClass(record)

const getDifficultyBadge = (record) => {
  if (!record.extra_data) return null
  try {
    const extra = typeof record.extra_data === 'string' ? JSON.parse(record.extra_data) : record.extra_data
    return extra.difficulty || null
  } catch {
    return null
  }
}

const getDifficultyBadgeConfig = (difficulty) => {
  if (difficulty === 'beginner') {
    return { label: '🌱 温和鼓励', class: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' }
  } else if (difficulty === 'standard') {
    return { label: '💼 标准专业', class: 'text-blue-400 border-blue-500/30 bg-blue-500/10' }
  } else if (difficulty === 'p8') {
    return { label: '🔥 P8 压力面', class: 'text-pink-400 border-pink-500/30 bg-pink-500/10' }
  }
  return null
}

// ChatPreviewModal 弹窗控制（Requirements 13.1, 13.5, 13.6）
const showChatPreviewModal = ref(false)
const chatPreviewRecordId = ref(null)

const goToHistory = (record) => {
  // 单一事实源走 utils/historyRecordTypes.js,
  // 这里只针对 legacy_chat 在 Dashboard 内部用 ChatPreviewModal 展开(Requirement 13.5),
  // 其它类型一律 router.push 到对应路由。
  const norm = normalizeRecordType(record)

  if (norm.type === RECORD_TYPES.LEGACY_CHAT) {
    // agent_*/general_chat 等旧聊天记录:打开 ChatPreviewModal,而非整页跳转
    showChatPreviewModal.value = true
    chatPreviewRecordId.value = record.id
    return
  }

  const target = resolveHistoryRoute(record)
  if (target?.name === 'route') {
    router.push(target.path)
  }
  // UNKNOWN 类型不动,避免把用户带到错的页面
}

/**
 * 接收 ChatPreviewModal 的 load-context 事件：
 * 将历史对话消息载入当前聊天，并在 nextTick 后 focus 输入框并滚动到底部（Requirements 13.1）
 */
const handleChatPreviewLoadContext = async (payload) => {
  chatStore.restoreFromHistory(payload.recordId, payload.messages)
  await nextTick()
  chatDockRef.value?.focus()
  scrollChatToBottom()
}

/**
 * 接收 ChatPreviewModal 的 close 事件：关闭弹窗（Requirements 13.6）
 */
const handleChatPreviewClose = () => {
  showChatPreviewModal.value = false
}

// 本地存储用户名
const userName = ref(localStorage.getItem('candidate_name') || '')

// 全局简历状态 — 初始化时检查 localStorage resume_text 去除首尾空白后是否非空
const globalResumeStatus = ref(
  (localStorage.getItem('resume_text') || '').trim().length > 0 ? 'ready' : 'missing'
)
const showResumeDialog = ref(false)
const pendingResumeText = ref('')
const pendingFileName = ref('')

// SetupModal 弹窗控制
const showSetupModal = ref(false)
// DataSourceModal 弹窗控制（数据面板设置，与 SetupModal 解耦）
const showDataSourceModal = ref(false)
// KnowledgePanel 悬浮面板控制
const showKnowledgePanel = ref(false)

const handleSetupComplete = () => {
  showSetupModal.value = false
  globalResumeStatus.value = 'ready'
  userName.value = localStorage.getItem('candidate_name') || ''
}

// 面试舱门模态框
const showInterviewModal = ref(false)
const interviewJd = ref('')
const isInterviewUnlocking = ref(false)
const interviewPaymentDone = ref(false)

// 内测彩蛋二维码文本
const mockPayUrl = ref("【内测福利】检测到您为特邀体验官，恭喜获得免单特权！请直接点击「开启挑战」进入系统。")

// 响应式数据
const userId = ref('user_001')
const activeWorkspace = ref('机构')
const activeMenu = ref('功能模板')
const placeholderText = ref('')
const toastMessage = ref('')
const showToast = ref(false)
let toastTimer = null

const showToastMsg = (msg, duration = 3000) => {
  toastMessage.value = msg
  showToast.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    showToast.value = false
  }, duration)
}

const showComingSoonToast = () => {
  showToastMsg('工程师正在玩命开发中，敬请期待！🚀', 2400)
}

// 动态时间问候语
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour >= 6 && hour < 12) return '早上好'
  if (hour >= 12 && hour < 14) return '中午好'
  if (hour >= 14 && hour < 18) return '下午好'
  if (hour >= 18 && hour < 24) return '晚上好'
  return '夜深了'
})

// 打字机占位符效果
const placeholders = [
  '想了解互联网大厂的最新面试套路吗？|',
  '输入你想查询的行业薪资情况 |',
  '向 AI 职场领航员提问...'
]
let placeholderIndex = 0
let charIndex = 0
let isDeleting = false
let placeholderTimer = null

const typeWriter = () => {
  const currentText = placeholders[placeholderIndex]
  
  if (!isDeleting) {
    placeholderText.value = currentText.substring(0, charIndex + 1)
    charIndex++
    
    if (charIndex === currentText.length) {
      isDeleting = true
      placeholderTimer = setTimeout(typeWriter, 2000)
      return
    }
    
    placeholderTimer = setTimeout(typeWriter, 80 + Math.random() * 40)
  } else {
    placeholderText.value = currentText.substring(0, charIndex - 1)
    charIndex--
    
    if (charIndex === 0) {
      isDeleting = false
      placeholderIndex = (placeholderIndex + 1) % placeholders.length
    }
    
    placeholderTimer = setTimeout(typeWriter, 40)
  }
}

// 鼠标跟随微光效果
const mouseX = ref(50)
const mouseY = ref(50)
const handleMouseMove = (e) => {
  const x = (e.clientX / window.innerWidth) * 100
  const y = (e.clientY / window.innerHeight) * 100
  mouseX.value = x
  mouseY.value = y
}

const confirmResumeUpdate = () => {
  localStorage.setItem('resume_text', pendingResumeText.value.trim())
  localStorage.setItem('resume_file_name', pendingFileName.value)
  globalResumeStatus.value = 'ready'
  showResumeDialog.value = false
  pendingResumeText.value = ''
  pendingFileName.value = ''
}

const cancelResumeUpdate = () => {
  showResumeDialog.value = false
  pendingResumeText.value = ''
  pendingFileName.value = ''
}

// 监听其他标签页更新简历（storage 事件仅在其他标签页修改时触发）
// 100ms 内更新 globalResumeStatus，此处为同步赋值，远快于 100ms
const handleStorageChange = (e) => {
  if (e.key === 'resume_text') {
    const newVal = (e.newValue || '').trim()
    globalResumeStatus.value = newVal.length > 0 ? 'ready' : 'missing'
  }
}

// 面试舱门逻辑
const openInterviewModal = () => {
  if (globalResumeStatus.value === 'missing') {
    showToastMsg('请先在【全局信息录入】或侧边栏上传您的简历')
    return
  }
  const savedJd = localStorage.getItem('current_interview_jd')
  if (savedJd) interviewJd.value = savedJd
  showInterviewModal.value = true
}

const closeInterviewModal = () => {
  showInterviewModal.value = false
  interviewJd.value = ''
  interviewPaymentDone.value = false
  isInterviewUnlocking.value = false
}

const unlockInterview = () => {
  if (!interviewJd.value.trim()) {
    showToastMsg('请先粘贴岗位描述 (JD)')
    return
  }
  localStorage.setItem('current_interview_jd', interviewJd.value.trim())
  showInterviewModal.value = false
  interviewPaymentDone.value = false
  isInterviewUnlocking.value = false
  router.push('/interview')
}


const chatInputRef = ref(null)
const chatDockRef = ref(null)

const askEducationPlanning = async () => {
  chatStore.setCollapsed(false)
  await nextTick()
  chatDockRef.value?.setInput('你好，我是大专生，我想咨询升学避坑与路线规划。')
  chatDockRef.value?.focus()
}

const handleQuickAction = async (text) => {
  chatStore.setCollapsed(false)
  await nextTick()
  chatDockRef.value?.setInput(text)
  chatDockRef.value?.focus()
}

const features = [
  {
    id: 'resume',
    title: '简历诊断',
    desc: '分析简历优缺点，提供优化建议',
    icon: FileText,
    actionType: 'route',
    path: '/resume-diagnosis',
    iconWrapClass: 'bg-purple-500/10',
    iconClass: 'text-purple-400',
    themeClass: 'border-purple-500/50 shadow-[0_0_30px_rgba(168,85,247,0.3)]',
    themeIconGlow: 'drop-shadow-[0_0_12px_rgba(168,85,247,0.5)]',
    dotColor: 'bg-purple-300 shadow-[0_0_10px_rgba(168,85,247,0.65)]'
  },
  {
    id: 'interview',
    title: '模拟面试',
    desc: 'AI 模拟面试，提供反馈和建议',
    icon: Mic,
    actionType: 'route',
    path: '/interview',
    iconWrapClass: 'bg-pink-500/10',
    iconClass: 'text-pink-400',
    themeClass: 'border-pink-500/50 shadow-[0_0_30px_rgba(236,72,153,0.3)]',
    themeIconGlow: 'drop-shadow-[0_0_12px_rgba(236,72,153,0.5)]',
    dotColor: 'bg-pink-300 shadow-[0_0_10px_rgba(236,72,153,0.65)]'
  },
  {
    id: 'career',
    title: '职业规划',
    desc: '基于你的背景，制定职业发展路径',
    icon: MessageSquare,
    actionType: 'route',
    path: '/career-planning',
    iconWrapClass: 'bg-blue-500/10',
    iconClass: 'text-blue-400',
    themeClass: 'border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.3)]',
    themeIconGlow: 'drop-shadow-[0_0_12px_rgba(59,130,246,0.5)]',
    dotColor: 'bg-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.65)]'
  },
  {
    id: 'education',
    title: '升学与避坑',
    desc: '专插本/考研等真实数据',
    icon: GraduationCap,
    actionType: 'function',
    action: askEducationPlanning,
    iconWrapClass: 'bg-emerald-500/10',
    iconClass: 'text-emerald-400',
    themeClass: 'border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.3)]',
    themeIconGlow: 'drop-shadow-[0_0_12px_rgba(16,185,129,0.5)]',
    dotColor: 'bg-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.65)]'
  }
]

const FEATURE_COUNT = features.length
const TRANSITION_DURATION = 700

const extendedFeatures = computed(() => {
  const multiplied = []
  for (let i = 0; i < 7; i++) multiplied.push(...features)
  return multiplied.map((f, i) => ({
    ...f,
    _extIndex: i,
    _realIndex: i % FEATURE_COUNT
  }))
})

const virtualIndex = ref(FEATURE_COUNT * 3)
const isTransitioning = ref(true)

const realIndex = computed(() => virtualIndex.value % FEATURE_COUNT)

const featureTrackStyle = computed(() => ({
  transform: `translateX(calc(-${virtualIndex.value} * var(--feature-card-width)))`,
  transitionDuration: isTransitioning.value ? `${TRANSITION_DURATION}ms` : '0ms',
  transitionTimingFunction: 'ease-in-out',
  transitionProperty: 'transform'
}))

let jumpTimer = null

const checkAndJump = () => {
  const len = FEATURE_COUNT
  const safeCenterOffset = len * 3
  const currentRealIndex = ((virtualIndex.value % len) + len) % len
  const targetIndex = safeCenterOffset + currentRealIndex

  if (virtualIndex.value !== targetIndex) {
    isTransitioning.value = false
    virtualIndex.value = targetIndex
    nextTick(() => {
      document.body.offsetHeight
      isTransitioning.value = true
    })
  }
}

const slideFeature = (direction) => {
  if (!isTransitioning.value) return
  virtualIndex.value += direction
  if (jumpTimer) clearTimeout(jumpTimer)
  jumpTimer = setTimeout(checkAndJump, TRANSITION_DURATION + 20)
}

const setActiveFeature = (index) => {
  virtualIndex.value = FEATURE_COUNT + index
}

let autoPlayTimer = null

const startAutoPlay = () => {
  if (autoPlayTimer) clearInterval(autoPlayTimer)
  autoPlayTimer = setInterval(() => {
    slideFeature(1)
  }, 3000)
}

const stopAutoPlay = () => {
  if (autoPlayTimer) {
    clearInterval(autoPlayTimer)
    autoPlayTimer = null
  }
}

const onCardClick = (index, feature) => {
  if (index === virtualIndex.value) {
    handleFeatureAction(feature)
  } else {
    if (!isTransitioning.value) return
    virtualIndex.value = index
    if (jumpTimer) clearTimeout(jumpTimer)
    jumpTimer = setTimeout(checkAndJump, TRANSITION_DURATION + 20)
  }
}

const handleFeatureAction = (feature) => {
  if (feature.actionType === 'function' && typeof feature.action === 'function') {
    feature.action()
    return
  }

  if (feature.path) {
    router.push(feature.path)
  }
}

// 快捷操作
const quickActions = [
  'Java后端前景如何？',
  '如何写好自我介绍？',
  '简历怎么突出亮点？',
  '前端面试常考什么？',
  '转行IT来得及吗？',
  '大厂面试流程是怎样的？'
]

// 工作区选项
const workspaces = [
  '机构',
  '团队',
  '个人',
  '营销',
  '线索'
]

// 菜单项
const menuItems = [
  {
    category: '主要功能',
    items: [
      { icon: 'file-text', label: '功能模板' },
      { icon: 'folder', label: '文档工作台' },
      { icon: 'clock', label: '历史记录' },
      { icon: 'plugin', label: '插件集成' },
      { icon: 'settings', label: '系统设置' }
    ]
  },
  {
    category: '我的项目',
    items: [
      { icon: 'folder', label: '商业分析' },
      { icon: 'bot', label: '个人规划' },
      { icon: 'file-text', label: '项目进度' }
    ]
  }
]

const handleSidebarItemClick = (item, menu) => {
  activeMenu.value = item.label

  if (item.label === '历史记录') {
    router.push('/history-archive')
    return
  }

  if (item.label === '文档工作台') {
    // Task A：左侧菜单统一跳转 /files（文档工作台）；
    // 不再触发 KnowledgePanel 悬浮面板（保留组件代码以便后续复用）。
    router.push('/files')
    return
  }

  if (item.label === '功能模板' || item.label === '插件集成' || item.label === '系统设置' || menu.category === '我的项目') {
    showComingSoonToast()
    return
  }

  showComingSoonToast()
}

const toggleSaveRecord = async (record) => {
  const nextSaved = !record.is_saved
  try {
    const response = await fetch(API_BASE_URL + '/history/' + record.id + '/save', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ is_saved: nextSaved })
    })
    if (!response.ok) throw new Error('HTTP ' + response.status)
    historyRecords.value = historyRecords.value.map((item) =>
      item.id === record.id ? { ...item, is_saved: nextSaved } : item
    )
  } catch (error) {
    console.error('保存状态切换失败', error)
  }
}

const deleteHistoryRecord = async (record) => {
  try {
    const response = await fetch(API_BASE_URL + '/history/' + record.id, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    })
    if (!response.ok) throw new Error('HTTP ' + response.status)
    historyRecords.value = historyRecords.value.filter((item) => item.id !== record.id)
  } catch (error) {
    console.error('删除历史记录失败', error)
  }
}

// 图标映射
const iconMap = {
  'file-text': FileText,
  'message-square': MessageSquare,
  'folder': Folder,
  'clock': Clock,
  'plugin': Puzzle,
  'settings': Settings,
  'bot': Bot
}

const chatMessages = computed(() => chatStore.messages)
const userChatInput = ref('')
const isChatLoading = computed(() => chatStore.isLoading)
const uploadedGlobalResume = ref('')
const chatContainerRef = ref(null)

// ── ChatDock 流式生命周期管控 ────────────────────────────
// 每次发送消息生成一个 runId,onMeta/onMessage/onDone/onError/finally 都校验:
//   1. runId 仍是 activeChatRunId(否则旧流已被新流取代,丢弃回调)
//   2. currentSessionId 仍等于发送时记录的 sessionIdAtStart(否则用户已切换会话,丢弃)
// 同时持有一个 AbortController,新建对话时 abort() 切断旧流。
const chatAbortController = ref(null)
const activeChatRunId = ref(0)
let _runIdCounter = 0
const nextRunId = () => {
  _runIdCounter = (_runIdCounter + 1) | 0
  return _runIdCounter
}

// 「保存并新建」按钮使用的 record id:必须来自后端归档结果(archivedRecordId),
// 绝对不能再从 currentSessionId 取(后者是前端会话 id,与后端 record_id 是两个概念)。
// 该按钮只有在用户先点击「归档本次对话」拿到 record_id 后才有意义,否则走兜底逻辑。
const currentRecordId = computed({
  get: () => chatStore.archivedRecordId,
  set: (val) => { chatStore.archivedRecordId = val }
})
const showNewChatModal = ref(false)

// 浮动对话框折叠状态：由 chatSessionStore 管理
const isChatDockCollapsed = computed(() => chatStore.isCollapsed)

// 折叠态 pill 中展示的最近一条用户消息预览
const lastUserPreview = computed(() => chatStore.lastUserPreview)
const toggleChatDock = async () => {
  chatStore.toggleCollapsed()
  if (!chatStore.isCollapsed) {
    await nextTick()
    chatDockRef.value?.focus()
  }
}

const scrollChatToBottom = () => {
  nextTick(() => {
    chatDockRef.value?.scrollToBottom()
  })
}

const sendGeneralChatMessage = async (inputText) => {
  // inputText 可以从 ChatDock @send 事件传入，也可以从旧 userChatInput 取
  const userMessage = (inputText || userChatInput.value || '').trim()
  if (!userMessage || chatStore.isLoading) return

  chatStore.appendUserMessage(userMessage)
  const aiMessage = chatStore.appendAIMessage()
  userChatInput.value = ''
  chatStore.isLoading = true
  scrollChatToBottom()

  // 本次流的身份标识:
  //   - runId 唯一标识本次 streamChat 调用,任何异步回调都先校验 runId 是否还是 activeChatRunId
  //   - sessionIdAtStart 锁定发送时的 session;任何回调若发现 currentSessionId 已变,直接丢弃
  // 这样可以彻底避免「新建会话 / 二次发送时旧流 onMessage 仍在 += 内容污染新会话」。
  const runId = nextRunId()
  const sessionIdAtStart = chatStore.currentSessionId
  activeChatRunId.value = runId

  // 一个 AbortController 控制本次 fetch;新建对话时调用 abort() 立即切断流。
  // 上一轮如果还有未释放的 controller,先把它 abort 掉(理论上 isLoading 守卫已经挡住,
  // 但保险起见做幂等清理)。
  try { chatAbortController.value?.abort() } catch (_) { /* 忽略 */ }
  const controller = new AbortController()
  chatAbortController.value = controller

  /** 校验回调是否仍属于当前 active run。不属于直接丢弃,不写 store。 */
  const isStillActive = () =>
    runId === activeChatRunId.value &&
    chatStore.currentSessionId === sessionIdAtStart

  try {
    const payload = {
      user_input: userMessage,
      history: chatStore.messages
        .slice(-10, -1)
        .map((message) => ({
          role: message.role === 'user' ? 'user' : 'assistant',
          content: message.content || ''
        }))
    }

    const savedResume = uploadedGlobalResume.value || localStorage.getItem('resume_text') || ''
    if (savedResume) payload.resume_text = savedResume

    const savedJd = localStorage.getItem('current_interview_jd') || ''
    if (savedJd) payload.jd_text = savedJd

    // 注入求职意向，让 AI 知道用户的目标岗位
    const targetJobValue = userStore.targetJob || localStorage.getItem('target_job') || ''
    if (targetJobValue) payload.target_job = targetJobValue

    // 附加当前选中的 LLM Provider（若有）
    const providerId = llmProviderStore.getCurrentProviderId()
    if (providerId) payload.provider_id = providerId

    await streamChat({
      endpoint: '/agent/chat',
      payload,
      signal: controller.signal,
      onMeta: (meta) => {
        if (!isStillActive()) return
        if (meta?.agent_label) aiMessage.agentLabel = meta.agent_label
      },
      onMessage: (delta) => {
        if (!isStillActive()) return
        if (!delta) return
        aiMessage.content += delta
        scrollChatToBottom()
      },
      onDone: (_donePayload) => {
        if (!isStillActive()) return
        // 注意:done.record_id 是后端落库 id,不应当作前端 currentSessionId 使用。
        // currentSessionId 永远保持前端生成的 session id,record_id 只允许进入 archivedRecordId
        // (而 archivedRecordId 由「归档本次对话」按钮显式触发的 markArchived(record_id) 写入)。
        // 这里不再把 record_id 写到 currentSessionId,避免新建对话时残留旧流的服务端 id。
      },
      onError: (msg) => {
        if (!isStillActive()) return
        aiMessage.content += (aiMessage.content ? '\n\n' : '') + (msg || 'Agent 暂时无法连接,请稍后重试。')
        scrollChatToBottom()
      }
    })

    if (isStillActive() && !aiMessage.content.trim()) {
      aiMessage.content = '模型没有返回有效内容，请稍后再试。'
    }
  } catch (error) {
    // streamChat 内部已对 AbortError 做静默处理,这里仅处理同步抛出的异常
    if (error?.name === 'AbortError') {
      // 主动取消,不弹错误 toast,不写 store
    } else if (isStillActive()) {
      console.error('发送 Agent 聊天消息失败', error)
      aiMessage.content = error.message || 'Agent 暂时无法连接，请稍后重试。'
    }
  } finally {
    // 只有当本次 run 仍是 active run 时才释放 isLoading;否则旧流的 finally 不应把新流的状态提前关掉。
    if (isStillActive()) {
      chatStore.isLoading = false
      chatStore.persistLocal()
      scrollChatToBottom()
      // 流自然结束,清掉 controller 引用(同一引用还可能被新 run 替换)
      if (chatAbortController.value === controller) {
        chatAbortController.value = null
      }
    }
  }
}

const forceStartNew = () => {
  // 切断当前可能仍在 streaming 的请求,使旧流的回调全部失效:
  //   1. abort fetch 让浏览器立即关掉连接
  //   2. 推进 activeChatRunId 让旧 run 的 isStillActive() 返回 false
  //   3. clearSession 生成新的 currentSessionId,旧 run 的 sessionIdAtStart 也对不上
  // 三道保险任意一条都足以丢弃旧流的 onMessage / onDone。
  try { chatAbortController.value?.abort() } catch (_) { /* 忽略 */ }
  chatAbortController.value = null
  activeChatRunId.value = nextRunId()
  // 兜底关闭 isLoading(旧 run 的 finally 不会再触发了)
  chatStore.isLoading = false
  chatStore.clearSession()
  userChatInput.value = ''
  showNewChatModal.value = false
  router.push('/')
}

/** ChatDock 「新建对话」按钮回调:abort + clearSession + focus 输入框 */
const handleChatDockNewChat = () => {
  try { chatAbortController.value?.abort() } catch (_) { /* 忽略 */ }
  chatAbortController.value = null
  activeChatRunId.value = nextRunId()
  chatStore.isLoading = false
  chatStore.clearSession()
  nextTick(() => chatDockRef.value?.focus())
}

const handleNewChat = () => {
  if (!chatStore.hasConversation) {
    forceStartNew()
    return
  }

  showNewChatModal.value = true
}

const saveAndStartNew = async () => {
  if (!currentRecordId.value) {
    // TODO: 如果后端没有在最终 done SSE 中返回 record_id，这里无法调用收藏接口。
    // 当前后端已按方案 A 返回 payload.record_id；保留兜底，避免旧服务版本下阻塞新建对话。
    console.warn('当前对话尚未拿到 record_id，无法执行保存收藏')
    forceStartNew()
    return
  }

  try {
    const response = await fetch(API_BASE_URL + '/history/' + currentRecordId.value + '/save', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ is_saved: true })
    })
    if (!response.ok) throw new Error('HTTP ' + response.status)
    await loadHistory()
  } catch (error) {
    console.error('保存当前对话失败', error)
  } finally {
    forceStartNew()
  }
}

const handleChatEnter = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendGeneralChatMessage()
  }
}

const chatPlaceholder = computed(() => {
  if (uploadedGlobalResume.value) return '请输入关于此文件的问题...'
  return placeholderText.value || '系统预设已就绪，问专业、志愿、就业都可以...'
})

const systemCarouselTexts = [
  '[系统预设：张雪峰灵魂已注入]',
  '[系统预设：广东专插本避坑指南已就绪]',
  '[系统预设：考研/公考大专限制库已加载]',
  '[系统预设：全量职场与升学数据已联网]'
]
const carouselIndex = ref(0)
const carouselFade = ref(true)
let carouselTimer = null

const startCarousel = () => {
  if (carouselTimer) clearInterval(carouselTimer)
  carouselTimer = setInterval(() => {
    carouselFade.value = false
    setTimeout(() => {
      carouselIndex.value = (carouselIndex.value + 1) % systemCarouselTexts.length
      carouselFade.value = true
    }, 300)
  }, 4000)
}

const currentCarouselText = computed(() => systemCarouselTexts[carouselIndex.value])

// 系统初始化控制台动画
const playConsoleAnimation = async () => {
  if (window.__EGG_LOGGED__) return
  window.__EGG_LOGGED__ = true

  console.clear()

  const messages = [
    { text: '>> System Initializing...', style: 'color: #9ca3af; font-size: 14px; font-family: monospace;', delay: 0 },
    { text: '>> Model: DeepSeek-V3 Active [OK]', style: 'color: #22c55e; font-size: 14px; font-family: monospace; font-weight: bold;', delay: 500 },
    { text: '>> Identity Verified: Moyingjun', style: 'color: #a855f7; font-size: 14px; font-family: monospace; font-weight: bold;', delay: 500 },
    { text: '%c ✨ AI Career Navigator | Designed & Developed by Moyingjun @ 广东水利电力职业技术学院 ✨ ', style: 'background: linear-gradient(90deg, #a855f7, #6366f1, #06b6d4, #a855f7); background-size: 200% auto; color: #fff; font-size: 14px; font-weight: bold; padding: 8px 16px; border-radius: 4px; animation: gradient 2s linear infinite; font-family: monospace;', delay: 800 }
  ]

  for (const msg of messages) {
    await new Promise(resolve => setTimeout(resolve, msg.delay))
    console.log(msg.text, msg.style)
  }
}

// 加载最新雷达图数据
//
// Phase B 修复：原版本调用 userStore.updateRadarData(中文 key setter)，
// 但 history.scores 字段存的是英文 6 维（professional / keywordMatch 等），
// 字段不匹配导致雷达图永远是 0。
//
// 新策略：拉取最近 10 条带 scores 的记录，按 record category 分类：
//   - resume_diagnosis → updateRadarFromResume（走 RESUME_TO_RADAR 映射）
//   - interview_*      → updateRadarFromInterview（走 INTERVIEW_TO_RADAR 映射）
// 各类只取最新一条，分别写入两份 store 快照；
// store._recomputeRadarData() 自然会取较新的一份合成 radarData。
async function loadLatestRadarData() {
  try {
    const response = await fetch(`${API_BASE_URL}/history?has_scores=true&limit=10`, {
      headers: { ...getAuthHeaders() }
    })
    if (!response.ok) return  // 网络错误时保持当前状态不变，不向用户展示错误

    const data = await response.json()
    const records = data.records || []

    // 找到每类最新一条（records 已按 id DESC 返回，第一条命中即最新）
    let latestResume = null
    let latestInterview = null
    for (const r of records) {
      const t = normalizeRecordType(r).type
      if (t === RECORD_TYPES.RESUME_DIAGNOSIS && !latestResume) latestResume = r
      if (t === RECORD_TYPES.INTERVIEW && !latestInterview) latestInterview = r
      if (latestResume && latestInterview) break
    }

    const parseScores = (raw) => {
      if (!raw) return null
      if (typeof raw === 'object') return raw
      try { return JSON.parse(raw) } catch { return null }
    }

    const resumeScores = parseScores(latestResume?.scores)
    const interviewScores = parseScores(latestInterview?.scores)

    if (resumeScores && Object.keys(resumeScores).length > 0) {
      userStore.updateRadarFromResume(resumeScores)
    }
    if (interviewScores && Object.keys(interviewScores).length > 0) {
      userStore.updateRadarFromInterview(interviewScores)
    }

    // activeDataSourceId 取较新的一条（auto 策略下展示的来源）
    if (latestResume && latestInterview) {
      const resumeNewer = (latestResume.id || 0) >= (latestInterview.id || 0)
      userStore.activeDataSourceId = resumeNewer ? latestResume.id : latestInterview.id
    } else if (latestResume) {
      userStore.activeDataSourceId = latestResume.id
    } else if (latestInterview) {
      userStore.activeDataSourceId = latestInterview.id
    } else {
      userStore.activeDataSourceId = null
    }

    // 两边都没有：保持空状态（store 默认 [0,0,0,0,0,0]）
  } catch {
    // 请求失败时保持当前 radarData 状态不变，不向用户展示错误
  }
}

// 恢复对话上下文
async function restoreChatContext(chatId) {
  if (!chatId) return

  try {
    const response = await fetch(`${API_BASE_URL}/history/${chatId}`, {
      headers: { ...getAuthHeaders() }
    })
    if (!response.ok) {
      // 404 或其他错误：清空聊天，用户可开始新对话
      chatStore.clearSession()
      return
    }

    const record = await response.json()
    let chatHistory = record.chat_history

    // 解析 chat_history（可能是 JSON 字符串）
    if (typeof chatHistory === 'string') {
      try { chatHistory = JSON.parse(chatHistory) } catch { chatHistory = [] }
    }

    let messages = []
    if (!Array.isArray(chatHistory) || chatHistory.length === 0) {
      // 降级：从 user_input + ai_result 构建最小上下文
      if (record.user_input) {
        messages.push({ role: 'user', content: record.user_input, timestamp: record.created_at })
      }
      if (record.ai_result) {
        messages.push({ role: 'ai', content: record.ai_result, timestamp: record.created_at })
      }
    } else {
      messages = chatHistory.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content || '',
        timestamp: record.created_at
      }))
    }

    chatStore.restoreFromHistory(Number(chatId), messages)
    await nextTick()
    scrollChatToBottom()
  } catch (error) {
    console.error('恢复对话上下文失败:', error)
    chatStore.clearSession()
  }
}

// ─────────────────────────────────────────────
// 雷达图 Pinned ID 动态数据绑定（Requirements 10.1, 10.2, 10.3, 10.7）
// ─────────────────────────────────────────────

/** 雷达图 fetch 错误状态，fetch 失败时显示提示，不重置数据 */
const radarFetchError = ref('')

/** 用于取消上一次 in-flight 请求的 AbortController */
let radarAbortController = null

/**
 * 根据当前激活 Tab 和 pinnedId 拉取对应历史记录的 scores 并更新雷达图。
 * - pinnedId 为 null 时：调用 resetRadarData() 显示空状态
 * - fetch 失败时：保留现有 radarData，显示错误提示，不重置为零
 * - 使用 AbortController 取消上一次 in-flight 请求（Requirements 10.7）
 *
 * @param {string} tab - 'resume' | 'interview' | 'career'
 * @param {number|null} pinnedId - 置顶记录 ID
 */
async function fetchPinnedRadarData(tab, pinnedId) {
  // 取消上一次尚未完成的请求，避免竞态条件
  if (radarAbortController) {
    radarAbortController.abort()
  }

  if (pinnedId === null) {
    // 无置顶记录时：不清空已有雷达图，仅清除错误提示
    // 雷达图保持当前 auto 策略（最近一次诊断/面试的数据）
    radarFetchError.value = ''
    return
  }

  radarAbortController = new AbortController()
  const signal = radarAbortController.signal

  try {
    radarFetchError.value = ''
    const response = await fetch(`${API_BASE_URL}/history/${pinnedId}`, {
      headers: { ...getAuthHeaders() },
      signal
    })

    if (!response.ok) {
      // fetch 失败：保留现有 radarData，显示错误提示（Requirements 10.2）
      radarFetchError.value = `数据加载失败（HTTP ${response.status}），显示上次缓存数据`
      return
    }

    const record = await response.json()

    // 解析 scores（可能是 JSON 字符串）
    let scores = record.scores
    if (typeof scores === 'string') {
      try { scores = JSON.parse(scores) } catch { scores = {} }
    }

    if (scores && Object.keys(scores).length > 0) {
      // Phase B 修复：按 tab 类型走新链路，不再使用旧 updateRadarData
      if (tab === 'resume') {
        userStore.updateRadarFromResume(scores)
      } else if (tab === 'interview') {
        userStore.updateRadarFromInterview(scores)
      }
      // career tab 不写 radar（无明确 scores 映射）
    }
    // 记录存在但 scores 为空时：保留当前已有 radar，不归零
  } catch (err) {
    if (err.name === 'AbortError') {
      // 请求被主动取消（新请求已发出），静默处理
      return
    }
    // 网络错误：保留现有 radarData，显示错误提示（Requirements 10.2）
    radarFetchError.value = '网络异常，显示上次缓存数据'
    console.error('雷达图数据加载失败:', err)
  }
}

/**
 * 防抖包装的雷达图数据拉取函数（300ms 防抖，Requirements 10.7）
 * 快速切换 Tab 或 pinnedId 时只触发最后一次请求
 */
const debouncedFetchRadarData = useDebounceFn((tab, pinnedId) => {
  fetchPinnedRadarData(tab, pinnedId)
}, 300)

// 监听 activeDataTab 切换：Tab 变化时用新 Tab 的 pinnedId 更新雷达图（Requirements 10.3）
watch(activeDataTab, (newTab) => {
  const pinnedId = userStore.getPinnedIdByTab(newTab)
  debouncedFetchRadarData(newTab, pinnedId)
})

// 监听当前激活 Tab 的 pinnedId 变化：用户在 DataSourceModal 选中新记录时触发（Requirements 10.1）
watch(
  () => userStore.getPinnedIdByTab(activeDataTab.value),
  (newPinnedId) => {
    debouncedFetchRadarData(activeDataTab.value, newPinnedId)
  }
)

// 监听 chat_id 路由参数，恢复历史对话上下文
watch(() => route.query.chat_id, async (chatId) => {
  if (!chatId) return
  await restoreChatContext(chatId)
}, { immediate: true })

// 监听 session_id 路由参数，恢复 ChatDock 会话（从 HistoryArchive 继续对话）
watch(() => route.query.session_id, async (sessionId) => {
  if (!sessionId) return
  try {
    const { loadSession } = await import('@/services/historyClient.js')
    const record = await loadSession(sessionId)
    if (!record) return

    let chatHistory = record.chat_history
    if (typeof chatHistory === 'string') {
      try { chatHistory = JSON.parse(chatHistory) } catch { chatHistory = [] }
    }
    if (!Array.isArray(chatHistory)) chatHistory = []

    chatStore.restoreFromHistory(sessionId, chatHistory, record.id)
    chatStore.setCollapsed(false)
    await nextTick()
    chatDockRef.value?.focus()
    scrollChatToBottom()
  } catch (err) {
    console.error('恢复会话失败:', err)
  }
}, { immediate: true })

// ─────────────────────────────────────────────
// 目标志愿展示（Requirements 15.1 ~ 15.5）
// ─────────────────────────────────────────────

/**
 * 读取 localStorage 或 userStore 中的 target_goal，
 * trim 后为空则返回 null，否则返回 trimmed 字符串。
 * localStorage 优先（保证跨组件写入后立即可见），
 * 同时依赖 userStore.targetGoal 触发响应式更新。
 */
const targetGoalDisplay = computed(() => {
  // 先读 localStorage（最新写入值），再 fallback 到 store
  const raw = localStorage.getItem('target_goal') || userStore.targetGoal || ''
  const trimmed = raw.trim()
  return trimmed.length > 0 ? trimmed : null
})

// 当 userStore.targetGoal 变化时，computed 会自动重新求值；
// 此 watch 的作用是确保其他组件（如 SetupModal）通过 store 更新后，
// Dashboard 能立即响应，无需页面刷新（Requirements 15.4）
watch(() => userStore.targetGoal, () => {
  // targetGoalDisplay 是 computed，依赖 userStore.targetGoal，会自动更新。
  // 此处无需额外操作，watch 的存在本身保证了响应式追踪链路完整。
})

// 生命周期
onMounted(() => {
  // 清理已下线的旧 ChatDock 附件挂载残留(/api/knowledge/upload 已被后端 410)。
  // 这两个 key 在新版本不再写入,只做幂等清除,避免老用户残留态影响。
  try {
    localStorage.removeItem('dashboard_knowledge_id')
    localStorage.removeItem('dashboard_knowledge_file_name')
  } catch (e) {
    /* localStorage 不可用时忽略 */
  }
  // loadFromStorage() 已在 main.js 应用启动时统一调用（Phase 1.1 收口），此处无需重复调用
  chatStore.restoreFromLocalStorage()
  typeWriter()
  startCarousel()
  startAutoPlay()
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('storage', handleStorageChange)
  playConsoleAnimation()
  loadHistory()
  loadDashboardBentoRecords()
  loadLatestRadarData()
})

onUnmounted(() => {
  if (placeholderTimer) {
    clearTimeout(placeholderTimer)
  }
  if (carouselTimer) {
    clearInterval(carouselTimer)
  }
  if (toastTimer) {
    clearTimeout(toastTimer)
  }
  stopAutoPlay()
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('storage', handleStorageChange)
  // 组件卸载时取消任何 in-flight 的雷达图请求，避免内存泄漏
  if (radarAbortController) {
    radarAbortController.abort()
  }
  // 同步取消 ChatDock 流式请求,防止卸载后旧流仍在写 store(虽然 isStillActive 也会兜底)
  try { chatAbortController.value?.abort() } catch (_) { /* 忽略 */ }
  chatAbortController.value = null
})
</script>

<template>
  <div class="app-container bg-[#020205] h-screen w-screen relative overflow-hidden flex text-gray-300">
    <transition name="toast-slide">
      <div
        v-if="showToast"
        class="fixed top-5 left-1/2 -translate-x-1/2 z-[120] px-4 py-2.5 rounded-full border border-cyan-400/30 bg-[#0b1020]/85 backdrop-blur-2xl text-sm text-cyan-100 shadow-[0_0_28px_rgba(6,182,212,0.18)] flex items-center gap-2"
      >
        <Sparkles class="w-4 h-4 text-cyan-300" />
        <span>{{ toastMessage }}</span>
      </div>
    </transition>

    <Teleport to="body">
      <transition name="modal-fade">
        <div
          v-if="showNewChatModal"
          class="fixed inset-0 z-[130] flex items-center justify-center px-4 bg-black/60 backdrop-blur-sm"
          @click.self="showNewChatModal = false"
        >
          <div class="w-full max-w-md rounded-xl border border-cyan-500/30 bg-gray-900/95 p-6 shadow-[0_0_30px_rgba(34,211,238,0.15)]">
            <div class="mb-5">
              <div class="mb-4 w-12 h-12 rounded-xl border border-cyan-400/30 bg-cyan-500/10 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.12)]">
                <Bookmark class="w-6 h-6 text-cyan-300" />
              </div>
              <h3 class="text-lg font-bold text-white">开启新对话前，要保存当前内容吗？</h3>
              <p class="mt-2 text-sm text-gray-400 leading-relaxed">
                当前对话已经产生内容。你可以先收藏这次对话，或直接清空后进入新的会话。
              </p>
            </div>

            <div class="flex flex-col gap-3">
              <button
                @click="saveAndStartNew"
                class="w-full px-4 py-3 rounded-xl border border-cyan-500/50 bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 hover:shadow-[0_0_22px_rgba(34,211,238,0.18)] transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Bookmark class="w-4 h-4" />
                保存并开启新对话
              </button>
              <button
                @click="forceStartNew"
                class="w-full px-4 py-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:shadow-[0_0_22px_rgba(248,113,113,0.14)] transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Trash2 class="w-4 h-4" />
                直接清空，不保存
              </button>
              <button
                @click="showNewChatModal = false"
                class="w-full px-4 py-3 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-300"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
    <!-- 背景光影效果 -->
    <div class="absolute top-0 left-0 w-full h-full z-0 pointer-events-none overflow-hidden">
      <div class="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vw] bg-purple-600/35 blur-[150px] rounded-full mix-blend-screen animate-ambient-1 pointer-events-none"></div>
      
      <div class="absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-cyan-600/30 blur-[150px] rounded-full mix-blend-screen animate-ambient-2 pointer-events-none"></div>
      
      <div class="absolute top-[45%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[80vw] h-[30vw] bg-indigo-500/25 blur-[120px] rounded-[100%] mix-blend-screen animate-ambient-center pointer-events-none"></div>
      <div class="absolute inset-0 z-[-1] opacity-[0.03]" style="background-image: linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px); background-size: 40px 40px; mask-image: radial-gradient(circle at 50% 50%, black 40%, transparent 80%); -webkit-mask-image: radial-gradient(circle at 50% 50%, black 40%, transparent 80%);"></div>
      <div class="absolute inset-0 z-[1] opacity-[0.02] mix-blend-overlay pointer-events-none" style="background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E');"></div>
    </div>

    <div class="relative z-10 flex flex-col md:flex-row h-[100dvh] w-full overflow-hidden">
      <!-- 左侧侧边栏 -->
      <div class="left-sidebar hidden md:flex w-64 m-4 rounded-3xl z-10 flex-shrink-0">
        <div class="bg-[#0a0f1a]/60 backdrop-blur-2xl border border-white/5 shadow-[inset_0_0_20px_rgba(255,255,255,0.02),0_0_40px_rgba(0,0,0,0.5)] rounded-3xl h-full w-full flex flex-col overflow-y-auto custom-scrollbar">
          <div class="logo p-4 border-b border-white/5 cursor-pointer flex items-center gap-3" @click="router.push('/')">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-[0_0_15px_rgba(168,85,247,0.5)] border border-purple-400/30">
              <svg class="w-5 h-5 text-white drop-shadow-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>
              </svg>
            </div>
            <div class="flex flex-col">
              <h1 class="text-xl text-white font-bold leading-tight tracking-wide drop-shadow-md">AI 职业导航</h1>
              <p class="text-xs text-purple-300/70 leading-tight mt-0.5">智能终端在线</p>
            </div>
          </div>

          <div class="new-chat p-4">
            <button
              @click="handleNewChat"
              class="w-full bg-gradient-to-r from-white/[0.08] to-white/[0.04] backdrop-blur-sm hover:from-white/[0.12] hover:to-white/[0.06] hover:shadow-[0_0_20px_rgba(168,85,247,0.3),inset_0_1px_0_rgba(255,255,255,0.1)] text-white py-2.5 px-4 rounded-full transition-all duration-300 flex items-center gap-2 border border-white/[0.08] hover:border-purple-500/40 hover:-translate-y-0.5 group shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
            >
              <Plus class="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />
              <span>新建对话</span>
            </button>
          </div>

          <div class="navigation p-4 flex-1">
            <div v-for="menu in menuItems" :key="menu.category" class="mb-6">
              <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
                {{ menu.category }}
              </h2>
              <div class="space-y-1">
                <div
                  v-for="(item, index) in menu.items"
                  :key="index"
                  class="menu-item flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-white/10 hover:bg-gradient-to-r hover:from-purple-500/10 hover:to-transparent transition-all duration-300 cursor-pointer hover:translate-x-2 hover:text-white group"
                  :class="{ 'bg-gradient-to-r from-purple-500/15 to-purple-500/5 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)] border border-purple-500/30': item.label === activeMenu }"
                  @click="handleSidebarItemClick(item, menu)"
                >
                  <component :is="iconMap[item.icon]" class="w-5 h-5 text-gray-400 group-hover:text-purple-400 transition-colors duration-300" />
                  <span class="text-sm">{{ item.label }}</span>
                </div>
              </div>
            </div>

            <!-- 全局简历状态卡片 -->
            <div class="mt-6">
              <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
                全局资产
              </h2>
              <div
                class="p-3 rounded-xl border backdrop-blur-sm transition-all duration-300 cursor-pointer hover:-translate-y-0.5 hover:shadow-lg group/asset"
                :class="globalResumeStatus === 'ready'
                  ? 'bg-green-500/[0.03] border-green-500/15 hover:border-green-500/30 hover:shadow-green-500/10'
                  : 'bg-red-500/[0.03] border-red-500/15 hover:border-red-500/30 hover:shadow-red-500/10'"
                @click="showSetupModal = true"
              >
                <div class="flex items-center gap-2 mb-1">
                  <div class="w-2 h-2 rounded-full transition-all duration-300"
                    :class="globalResumeStatus === 'ready'
                      ? 'bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]'
                      : 'bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]'"></div>
                  <span class="text-xs font-medium transition-colors duration-300"
                    :class="globalResumeStatus === 'ready' ? 'text-green-400' : 'text-red-400'">
                    {{ globalResumeStatus === 'ready' ? '个人信息：已就绪' : '信息缺失' }}
                  </span>
                </div>
                <!-- 升学模式：展示考试类型标签 + 分数 + 排位 -->
                <template v-if="userStore.activeMode === 'education'">
                  <div class="flex items-center gap-2 mt-1.5">
                    <span class="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {{ examTypeLabel }}
                    </span>
                  </div>
                  <p class="text-xs text-gray-400 mt-1">
                    分数: {{ userStore.estimatedScore || '未设置' }} /
                    排位: {{ userStore.examRank || '未设置' }}
                  </p>
                </template>
                <!-- 求职模式：展示目标岗位 + 简历就绪状态 -->
                <template v-else>
                  <p class="text-xs text-gray-400 mt-1 truncate">
                    {{ userStore.targetJob || '点击完善个人信息' }}
                  </p>
                  <div v-if="userStore.resumeText" class="flex items-center gap-1.5 mt-1">
                    <div class="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.8)]"></div>
                    <span class="text-xs text-green-400">简历已就绪</span>
                  </div>
                </template>
              </div>


              <div
                class="mt-2 px-2.5 py-1.5 rounded-lg system-knowledge-tag-sidebar flex items-center gap-2"
              >
                <Sparkles class="w-3.5 h-3.5 text-emerald-300 flex-shrink-0" />
                <span class="text-xs text-emerald-200 truncate flex-1 system-carousel-text" :class="{ 'carousel-fade-out': !carouselFade, 'carousel-fade-in': carouselFade }">{{ currentCarouselText }}</span>
              </div>


            </div>

            <!-- 侧边栏底部署名 -->
            <div class="mt-auto pt-4 border-t border-white/5 pl-2 group/credit">
              <p class="text-xs text-gray-400 font-medium cursor-pointer relative">
                Moyingjun
                <span class="absolute left-0 bottom-full mb-2 px-2 py-1 bg-gray-800/90 backdrop-blur-sm text-xs text-gray-300 rounded-md opacity-0 group-hover/credit:opacity-100 transition-opacity duration-300 whitespace-nowrap pointer-events-none border border-white/10 shadow-lg">
                  嘘...按 F12 看看？
                </span>
              </p>
              <p class="text-xs text-gray-500 mt-0.5">广东水利电力职业技术学院</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧主工作区 -->
      <div class="right-workspace m-4 ml-0 z-10 relative flex-1 flex flex-col h-[calc(100dvh-2rem)] min-w-0 overflow-x-hidden overflow-y-hidden">
        <div class="bg-white/[0.02] backdrop-blur-xl border border-white/5 rounded-3xl flex-1 shadow-xl shadow-black/50 overflow-hidden flex flex-col relative">
          <div class="top-bar p-4 border-b border-white/10 flex items-center justify-between animate-[fadeIn_0.3s_ease-out] flex-shrink-0">
            <div class="search-container flex items-center gap-2">
              <div class="relative">
                <input
                  type="text"
                  placeholder="搜索..."
                  class="bg-white/[0.03] backdrop-blur-md border border-white/5 rounded-lg py-2 px-4 pl-10 text-base w-full md:w-64 focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_20px_rgba(34,211,238,0.25)] transition-all duration-300"
                />
                <Search class="absolute left-3 top-2.5 text-gray-500 w-4 h-4" />
              </div>
            </div>
            <div class="flex items-center gap-3">
              <!-- AI 引擎切换器（统一组件：GlobalProviderSwitcher） -->
              <GlobalProviderSwitcher placement="bottom-right" />
              <button class="bg-white/10 border border-white/10 rounded-lg py-2 px-4 text-sm hover:bg-white/15 hover:border-purple-500/50 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/20">
                邀请
              </button>
            </div>
          </div>

          <div class="main-content flex-1 overflow-hidden relative flex flex-col">
            <!-- 鼠标跟随环境光 -->
            <div 
              class="absolute w-[600px] h-[600px] bg-purple-600/15 rounded-full blur-[150px] pointer-events-none z-0 transition-all duration-700 ease-out"
              :style="{ left: `calc(${mouseX}% - 300px)`, top: `calc(${mouseY}% - 300px)` }"
            ></div>
            <div class="absolute bottom-20 right-10 w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[150px] pointer-events-none z-0"></div>
            
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 pb-48 overflow-y-auto overflow-x-hidden custom-scrollbar relative z-10">
              <div class="lg:col-span-8 flex flex-col gap-5">
              
              <!-- 顶部信息条：Hero + 工作区标签 -->
              <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 animate-fade-in-up animation-delay-0">
                <div class="flex flex-col">
                  <h1 class="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-200 tracking-tighter">{{ greeting }}，{{ userName || '新' }}同学</h1>
                  <p class="text-sm text-white/45 mt-0.5">选择一个 AI 职业任务开始</p>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="(workspace, index) in workspaces"
                    :key="workspace"
                    class="px-3 py-1 rounded-full text-xs font-medium border transition-all duration-300"
                    :class="activeWorkspace === workspace
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 border-transparent text-white shadow-lg shadow-purple-500/25'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white'
                    "
                    @click="activeWorkspace = workspace"
                  >
                    {{ workspace }}
                  </button>
                </div>
              </div>

              <!-- 核心任务控制台容器 -->
              <div class="relative rounded-[32px] border border-white/10 bg-white/[0.025] backdrop-blur-xl p-6 min-h-[420px] overflow-hidden shadow-[0_20px_80px_rgba(0,0,0,0.25)] animate-fade-in-up animation-delay-200">
                <!-- 容器顶部标题行 -->
                <div class="mb-4 flex items-center justify-between">
                  <div>
                    <h2 class="text-lg font-semibold text-gray-200 text-left">核心功能</h2>
                    <p class="text-xs text-gray-500 mt-0.5">选择一个 AI 职业任务开始</p>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <button
                      v-for="(feature, index) in features"
                      :key="feature.id + '-dot'"
                      @click="setActiveFeature(index)"
                      class="h-1.5 rounded-full transition-all duration-300"
                      :class="index === realIndex ? ['w-6', feature.dotColor] : 'w-1.5 bg-white/20 hover:bg-white/40'"
                      :aria-label="'切换到' + feature.title"
                    ></button>
                  </div>
                </div>

                <div
                  class="feature-slider-wrapper relative w-full overflow-hidden h-[320px]"
                  @mouseenter="stopAutoPlay"
                  @mouseleave="startAutoPlay"
                >
                  <button
                    @click.stop="slideFeature(-1)"
                    class="pointer-events-auto absolute left-2 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-black/50 backdrop-blur border border-white/10 text-gray-300 hover:text-white hover:border-cyan-300/50 hover:bg-cyan-500/20 hover:shadow-[0_0_22px_rgba(34,211,238,0.28)] transition-all duration-300 flex items-center justify-center"
                    aria-label="上一张"
                  >
                    <ChevronLeft class="w-5 h-5" />
                  </button>

                  <div
                    class="feature-slider-track flex flex-nowrap items-center h-full"
                    :style="featureTrackStyle"
                  >
                    <div class="feature-spacer flex-shrink-0 w-0 sm:w-1/4 md:w-1/3 px-2 pointer-events-none" aria-hidden="true"></div>
                    <div
                      v-for="(feature, index) in extendedFeatures"
                      :key="feature.id + '-' + index"
                      class="feature-slide flex-shrink-0 w-full sm:w-1/2 md:w-1/3 px-2 transition-all"
                      :class="[index === virtualIndex ? 'scale-100 opacity-100 z-10' : 'scale-95 opacity-45 z-0', isTransitioning ? 'duration-700' : 'duration-0']"
                    >
                      <div
                        class="feature-card h-[280px] w-full max-w-[420px] mx-auto relative overflow-hidden backdrop-blur-2xl border rounded-3xl p-5 md:p-6 cursor-pointer text-left flex flex-col items-start transition-all hover:-translate-y-1"
                        :class="[index === virtualIndex
                          ? [feature.themeClass, 'bg-white/[0.07]']
                          : 'bg-[#151520]/60 border-white/5 shadow-none', isTransitioning ? 'duration-700' : 'duration-0']"
                        @click="onCardClick(index, feature)"
                      >
                        <div class="absolute inset-0 opacity-0 transition-opacity pointer-events-none"
                          :class="[index === virtualIndex ? 'opacity-100 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent' : '', isTransitioning ? 'duration-700' : 'duration-0']"
                        ></div>
                        <div
                          class="cyber-border-wrapper transition-opacity"
                          :class="[index === virtualIndex ? 'opacity-100' : 'opacity-0', isTransitioning ? 'duration-700' : 'duration-0']"
                        >
                          <div class="cyber-border-inner" :style="{ '--glow-color': feature.id === 'resume' ? '#a855f7' : feature.id === 'interview' ? '#ec4899' : feature.id === 'career' ? '#3b82f6' : '#10b981' }"></div>
                        </div>
                        <div
                          class="w-14 h-14 flex items-center justify-center rounded-xl mb-4 transition-all"
                          :class="[feature.iconWrapClass, index === virtualIndex ? ['scale-110', feature.themeIconGlow] : '', isTransitioning ? 'duration-700' : 'duration-0']"
                        >
                          <component
                            :is="feature.icon"
                            class="w-7 h-7 transition-all"
                            :class="[feature.iconClass, index === virtualIndex ? 'brightness-125' : '', isTransitioning ? 'duration-700' : 'duration-0']"
                          />
                        </div>
                        <h3
                          class="text-xl md:text-2xl font-black tracking-tight mb-2 text-left transition-colors"
                          :class="[index === virtualIndex ? 'text-white' : 'text-gray-100', isTransitioning ? 'duration-700' : 'duration-0']"
                        >{{ feature.title }}</h3>
                        <p class="text-base text-gray-400 text-left leading-relaxed">{{ feature.desc }}</p>
                      </div>
                    </div>
                    <div class="feature-spacer flex-shrink-0 w-0 sm:w-1/4 md:w-1/3 px-2 pointer-events-none" aria-hidden="true"></div>
                  </div>

                  <button
                    @click.stop="slideFeature(1)"
                    class="pointer-events-auto absolute right-2 top-1/2 -translate-y-1/2 z-30 w-10 h-10 rounded-full bg-black/50 backdrop-blur border border-white/10 text-gray-300 hover:text-white hover:border-cyan-300/50 hover:bg-cyan-500/20 hover:shadow-[0_0_22px_rgba(34,211,238,0.28)] transition-all duration-300 flex items-center justify-center"
                    aria-label="下一张"
                  >
                    <ChevronRight class="w-5 h-5" />
                  </button>
                </div>
              </div>

              <!-- 继续上次模块（含零数据态 OnboardingPanel 与加载占位） -->
              <transition name="onboarding-fade" mode="out-in">
                <!-- 加载中：显示骨架占位 -->
                <div
                  v-if="isHistoryLoading"
                  key="loading"
                  class="rounded-[28px] border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5"
                >
                  <div class="mb-4 flex items-center justify-between">
                    <div class="flex flex-col gap-2">
                      <div class="h-4 w-24 rounded-md bg-white/10 animate-pulse"></div>
                      <div class="h-3 w-40 rounded-md bg-white/5 animate-pulse"></div>
                    </div>
                    <div class="h-3 w-16 rounded-md bg-white/5 animate-pulse"></div>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="h-24 rounded-2xl bg-white/[0.015] border border-white/5 animate-pulse"></div>
                    <div class="h-24 rounded-2xl bg-white/[0.015] border border-white/5 animate-pulse"></div>
                  </div>
                </div>

                <!-- 零数据态：新手启航舱 OnboardingPanel -->
                <div
                  v-else-if="historyRecords.length === 0"
                  key="onboarding"
                  class="rounded-[28px] border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 animate-fade-in-up animation-delay-500"
                >
                  <!-- 全局引导语 -->
                  <div class="border-l-2 border-purple-500/50 pl-3 mb-4">
                    <p class="text-xs text-gray-400">系统初始化完成。欢迎登舰，新同学。四大核心引擎已就绪，请选择你的首个突破口进行全息扫描。</p>
                  </div>

                  <!-- 引导卡片网格 -->
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div v-for="card in onboardingCards" :key="card.id">

                      <!-- 激活卡片 -->
                      <div
                        v-if="!card.locked"
                        class="rounded-2xl border bg-white/[0.02] backdrop-blur-md p-4 flex flex-col gap-3 transition-all duration-300 hover:-translate-y-1"
                        :class="{
                          'border-purple-500/40': card.themeColor === 'purple',
                          'border-pink-500/40': card.themeColor === 'pink',
                          'border-blue-500/40': card.themeColor === 'blue',
                          'hover:shadow-[0_8px_24px_rgba(168,85,247,0.2)]': card.themeColor === 'purple',
                          'hover:shadow-[0_8px_24px_rgba(236,72,153,0.2)]': card.themeColor === 'pink',
                          'hover:shadow-[0_8px_24px_rgba(59,130,246,0.2)]': card.themeColor === 'blue',
                        }"
                      >
                        <!-- Emoji 图标区域 -->
                        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
                             :class="{
                               'bg-purple-500/20': card.themeColor === 'purple',
                               'bg-pink-500/20': card.themeColor === 'pink',
                               'bg-blue-500/20': card.themeColor === 'blue',
                             }">
                          {{ card.emoji }}
                        </div>
                        <!-- 标题行 -->
                        <div>
                          <h3 class="text-sm font-bold text-white">{{ card.title }}</h3>
                          <p class="text-xs text-gray-500">{{ card.subtitle }}</p>
                        </div>
                        <!-- 描述文本 -->
                        <p class="text-xs text-gray-400 leading-relaxed line-clamp-3">{{ card.desc }}</p>
                        <!-- 操作按钮 -->
                        <button
                          class="mt-auto w-full py-1.5 px-3 rounded-lg text-xs font-medium transition-all duration-200"
                          :class="{
                            'text-purple-300 bg-purple-500/20 hover:bg-purple-500/30': card.themeColor === 'purple',
                            'text-pink-300 bg-pink-500/20 hover:bg-pink-500/30': card.themeColor === 'pink',
                            'text-blue-300 bg-blue-500/20 hover:bg-blue-500/30': card.themeColor === 'blue',
                          }"
                          @click="router.push(card.path)"
                        >
                          {{ card.action }}
                        </button>
                      </div>

                      <!-- 锁定卡片 -->
                      <div
                        v-else
                        class="rounded-2xl border border-emerald-500/40 bg-white/[0.02] backdrop-blur-md p-4 flex flex-col gap-3 opacity-60 cursor-not-allowed"
                      >
                        <!-- Emoji 图标区域 -->
                        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl bg-emerald-500/10">
                          {{ card.emoji }}
                        </div>
                        <!-- 标题行 -->
                        <div>
                          <h3 class="text-sm font-bold text-white">{{ card.title }}</h3>
                          <p class="text-xs text-gray-500">{{ card.subtitle }}</p>
                        </div>
                        <!-- 描述文本 -->
                        <p class="text-xs text-gray-400 leading-relaxed line-clamp-3">{{ card.desc }}</p>
                        <!-- 锁定按钮：@click.prevent 阻止默认行为，showToastMsg 反馈用户，不触发 router.push -->
                        <button
                          class="mt-auto w-full py-1.5 px-3 rounded-lg text-xs font-medium border border-emerald-500/20 bg-emerald-500/5 text-emerald-500/50 animate-pulse cursor-not-allowed"
                          @click.prevent="showToastMsg('该模块正在开发中，敬请期待！', 3000)"
                        >
                          模块构筑中... Coming Soon
                        </button>
                      </div>

                    </div>
                  </div>
                </div>

                <!-- 有数据态：继续上次 HistoryPanel -->
                <div
                  v-else
                  key="history"
                  class="rounded-[28px] border border-white/10 bg-white/[0.03] backdrop-blur-xl p-5 animate-fade-in-up animation-delay-500"
                >
                  <div class="mb-4 flex items-center justify-between">
                    <div>
                      <h2 class="text-base font-semibold text-gray-200 text-left flex items-center gap-2">
                        <History class="w-4 h-4 text-purple-400" />
                        继续上次
                      </h2>
                      <p class="text-xs text-gray-500 mt-0.5">最近的 AI 职业咨询记录</p>
                    </div>
                    <button
                      @click="router.push('/history-archive')"
                      class="text-xs text-purple-400 hover:text-purple-300 transition-colors duration-300 flex items-center gap-1"
                    >
                      查看全部
                      <ChevronRight class="w-4 h-4" />
                    </button>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                    <div
                      v-for="record in historyRecords"
                      :key="record.id"
                      class="relative overflow-hidden bg-white/[0.015] backdrop-blur-md border border-white/5 rounded-2xl p-4 pb-10 cursor-pointer transition-all duration-500 group hover:-translate-y-1 hover:bg-white/[0.03] hover:border-purple-500/30 hover:shadow-[0_10px_30px_rgba(168,85,247,0.15)] text-left"
                      @click="goToHistory(record)"
                    >
                      <div class="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-purple-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                      <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                          <span class="text-xs px-2 py-0.5 rounded-full border" :class="getCategoryColor(record)">{{ getRecordTypeLabel(record) }}</span>
                          <span v-if="getDifficultyBadge(record) && getDifficultyBadgeConfig(getDifficultyBadge(record))" class="text-xs px-1.5 py-0.5 rounded-full border" :class="getDifficultyBadgeConfig(getDifficultyBadge(record)).class">{{ getDifficultyBadgeConfig(getDifficultyBadge(record)).label }}</span>
                        </div>
                        <span class="text-xs text-gray-500">{{ record.created_at }}</span>
                      </div>
                      <p class="text-xs text-gray-400 truncate">{{ record.user_input }}</p>
                      <p v-if="record.ai_result" class="text-xs text-gray-500 truncate mt-1">{{ record.ai_result.substring(0, 60) }}...</p>
                      <div class="absolute right-3 bottom-3 flex items-center gap-2">
                        <button
                          @click.stop="toggleSaveRecord(record)"
                          class="w-7 h-7 rounded-full border backdrop-blur flex items-center justify-center transition-all duration-300"
                          :class="record.is_saved
                            ? 'border-amber-300/50 bg-amber-400/10 text-amber-300 shadow-[0_0_14px_rgba(251,191,36,0.2)]'
                            : 'border-white/10 bg-black/20 text-gray-500 hover:text-amber-300 hover:border-amber-300/40 hover:bg-amber-400/10'"
                          title="保存/取消保存"
                        >
                          <Star class="w-3 h-3" :fill="record.is_saved ? 'currentColor' : 'none'" />
                        </button>
                        <button
                          @click.stop="deleteHistoryRecord(record)"
                          class="w-7 h-7 rounded-full border border-white/10 bg-black/20 text-gray-500 backdrop-blur flex items-center justify-center hover:text-red-300 hover:border-red-400/40 hover:bg-red-500/10 transition-all duration-300"
                          title="删除记录"
                        >
                          <Trash2 class="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <!-- 快捷问题 chips 收拢在历史记录下方 -->
                  <div class="flex flex-wrap gap-2 pt-4 border-t border-white/5">
                    <button
                      v-for="action in quickActions"
                      :key="action"
                      @click="handleQuickAction(action)"
                      class="group px-3 py-1.5 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-cyan-500/10 hover:border-cyan-500/30 transition-all duration-300 flex items-center gap-2"
                    >
                      <span class="text-cyan-500/40 group-hover:text-cyan-400 font-mono text-xs transition-colors duration-300">&gt;&gt;</span>
                      <span class="text-xs text-gray-400 group-hover:text-cyan-100 transition-colors duration-300">{{ action }}</span>
                    </button>
                  </div>
                </div>
              </transition>



              </div>

              <!-- 右侧 Bento 辅助面板 -->
              <div class="lg:col-span-4 flex flex-col gap-4 sticky top-6 self-start">
                <!-- 卡片 1：系统状态（动态读取 LLM Provider 列表） -->
                <div class="bg-white/[0.015] backdrop-blur-xl border border-white/5 rounded-2xl p-4 shadow-[inset_0_0_20px_rgba(255,255,255,0.01)] transition-all duration-500 hover:-translate-y-1 hover:bg-white/[0.03] hover:border-purple-500/20 hover:shadow-[0_10px_30px_rgba(168,85,247,0.1)] group">
                  <div class="flex items-center justify-between mb-2">
                    <h3 class="text-xs font-semibold text-gray-300">系统状态</h3>
                    <span class="text-xs text-gray-500">实时</span>
                  </div>
                  <div class="space-y-1.5">
                    <div
                      v-for="provider in llmProviderStore.providers"
                      :key="provider.id"
                      class="flex items-center justify-between"
                    >
                      <div class="flex items-center gap-2">
                        <div
                          class="w-1.5 h-1.5 rounded-full"
                          :class="llmProviderStore.currentProviderId === provider.id && provider.status === 'online'
                            ? 'bg-emerald-500 animate-pulse shadow-[0_0_6px_rgba(16,185,129,0.8)]'
                            : 'bg-gray-600'"
                        ></div>
                        <span
                          class="text-xs"
                          :class="llmProviderStore.currentProviderId === provider.id ? 'text-gray-300' : 'text-gray-500'"
                        >{{ provider.display_name }}</span>
                      </div>
                      <span
                        class="text-xs"
                        :class="llmProviderStore.currentProviderId === provider.id && provider.status === 'online'
                          ? 'text-emerald-400'
                          : provider.status === 'unconfigured'
                            ? 'text-gray-500 italic'
                            : 'text-gray-500'"
                      >{{ provider.status === 'unconfigured' ? 'Unconfigured' : (llmProviderStore.currentProviderId === provider.id ? 'Online' : 'Standby') }}</span>
                    </div>
                    <div v-if="llmProviderStore.providers.length === 0" class="flex items-center justify-between">
                      <div class="flex items-center gap-2">
                        <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_6px_rgba(16,185,129,0.8)]"></div>
                        <span class="text-xs text-gray-300">Default LLM</span>
                      </div>
                      <span class="text-xs text-emerald-400">Online</span>
                    </div>
                  </div>
                </div>

                <!-- 卡片 2：今日建议 -->
                <div class="bg-white/[0.015] backdrop-blur-xl border border-white/5 rounded-2xl p-4 shadow-[inset_0_0_20px_rgba(255,255,255,0.01)] transition-all duration-500 hover:-translate-y-1 hover:bg-white/[0.03] hover:border-purple-500/20 hover:shadow-[0_10px_30px_rgba(168,85,247,0.1)] group">
                  <div class="flex items-center justify-between mb-2">
                    <h3 class="text-xs font-semibold text-gray-300">今日建议</h3>
                    <span class="text-xs text-gray-500">3 条</span>
                  </div>
                  <div class="space-y-1.5">
                    <div class="flex items-center gap-2 group/item cursor-default">
                      <div class="w-1.5 h-1.5 rounded-full bg-cyan-400/60 group-hover/item:shadow-[0_0_8px_rgba(34,211,238,0.8)] transition-all duration-300 flex-shrink-0"></div>
                      <span class="text-xs text-gray-400">简历优化建议已就绪</span>
                    </div>
                    <div class="flex items-center gap-2 group/item cursor-default">
                      <div class="w-1.5 h-1.5 rounded-full bg-purple-400/60 group-hover/item:shadow-[0_0_8px_rgba(168,85,247,0.8)] transition-all duration-300 flex-shrink-0"></div>
                      <span class="text-xs text-gray-400">专属院校政策更新 3 条</span>
                    </div>
                    <div class="flex items-center gap-2 group/item cursor-default">
                      <div class="w-1.5 h-1.5 rounded-full bg-amber-400/60 group-hover/item:shadow-[0_0_8px_rgba(251,191,36,0.8)] transition-all duration-300 flex-shrink-0"></div>
                      <span class="text-xs text-gray-400">面试模拟热度 TOP1</span>
                    </div>
                  </div>
                </div>

                <!-- 卡片 3：动态多维数据栈（Widget Stack） -->
                <div class="bg-white/[0.015] backdrop-blur-xl border border-white/5 rounded-2xl p-4 shadow-[inset_0_0_20px_rgba(255,255,255,0.01)] flex-1 transition-all duration-500 hover:bg-white/[0.03] hover:border-cyan-500/20 hover:shadow-[0_10px_30px_rgba(34,211,238,0.1)] group flex flex-col">
                  <div class="flex items-center justify-between mb-4">
                    <div class="flex bg-black/20 rounded-lg p-1 border border-white/5 backdrop-blur-sm">
                      <button @click="activeDataTab = 'resume'" :class="activeDataTab === 'resume' ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' : 'text-gray-500 hover:text-gray-300 border-transparent'" class="px-2 py-1 rounded text-xs font-medium transition-all border">简历诊断</button>
                      <button @click="activeDataTab = 'interview'" :class="activeDataTab === 'interview' ? 'bg-pink-500/20 text-pink-300 border-pink-500/30' : 'text-gray-500 hover:text-gray-300 border-transparent'" class="px-2 py-1 rounded text-xs font-medium transition-all border">面试评估</button>
                      <button @click="activeDataTab = 'career'" :class="activeDataTab === 'career' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'text-gray-500 hover:text-gray-300 border-transparent'" class="px-2 py-1 rounded text-xs font-medium transition-all border">综合规划</button>
                    </div>
                    <span class="text-xs text-cyan-500/70 cursor-pointer hover:text-cyan-400" @click="showDataSourceModal = true">数据面板设置 &gt;</span>
                  </div>

                  <!-- 雷达图 fetch 失败提示：保留现有数据，不重置为零（Requirements 10.2） -->
                  <transition name="widget-fade">
                    <div
                      v-if="radarFetchError"
                      class="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-300"
                    >
                      <span class="flex-shrink-0">⚠</span>
                      <span class="flex-1">{{ radarFetchError }}</span>
                      <button
                        @click="radarFetchError = ''"
                        class="flex-shrink-0 text-red-400/60 hover:text-red-300 transition-colors"
                        aria-label="关闭错误提示"
                      >✕</button>
                    </div>
                  </transition>

                  <div class="relative flex-1 overflow-hidden">
                    <transition name="widget-fade" mode="out-in">
                      <div v-if="activeDataTab === 'resume'" key="resume" class="flex flex-col">
                        <CyberRadarChart :chartData="displayedRadarData" style="height: 220px;" class="-mt-4 -mb-2" />
                        <div class="grid grid-cols-2 gap-x-4 gap-y-3">
                          <div v-for="(item, idx) in displayedRadarItems" :key="'resume-' + item.name">
                            <div class="flex justify-between text-xs text-gray-500 mb-1">
                              <span>{{ item.name }}</span>
                              <span :class="idx % 2 === 0 ? 'text-purple-400' : 'text-cyan-400'">{{ item.value }}%</span>
                            </div>
                            <div class="h-1 bg-white/5 rounded-full overflow-hidden">
                              <div class="h-full animate-boot-bar" :class="idx % 2 === 0 ? 'bg-purple-500/60' : 'bg-cyan-500/60'" :style="{ width: item.value + '%' }"></div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div v-else-if="activeDataTab === 'interview'" key="interview" class="flex flex-col">
                        <CyberRadarChart :chartData="displayedRadarData" style="height: 220px;" class="-mt-4 -mb-2" />
                        <div class="grid grid-cols-2 gap-x-4 gap-y-3">
                          <div v-for="(item, idx) in displayedRadarItems" :key="'interview-' + item.name">
                            <div class="flex justify-between text-xs text-gray-500 mb-1">
                              <span>{{ item.name }}</span>
                              <span class="text-pink-400">{{ item.value }}%</span>
                            </div>
                            <div class="h-1 bg-white/5 rounded-full overflow-hidden">
                              <div class="h-full bg-pink-500/60 animate-boot-bar" :style="{ width: item.value + '%' }"></div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div v-else key="career" class="flex flex-col items-center justify-center h-full gap-3 py-6">
                        <Compass class="w-8 h-8 text-gray-600" />
                        <template v-if="careerRecords.length > 0">
                          <p class="text-xs text-gray-300 text-center leading-relaxed">
                            已找到 {{ careerRecords.length }} 条职业规划记录<br>
                            <span class="text-gray-500">最近一次：{{ formatRecordTime(latestCareerRecord) }}</span>
                          </p>
                          <button
                            @click="openCareerPreview(0)"
                            class="px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/[0.06] text-xs text-cyan-300 font-medium hover:bg-cyan-500/15 hover:border-cyan-400/50 hover:shadow-[0_0_14px_rgba(6,182,212,0.18)] transition-all duration-300 flex items-center gap-1.5"
                          >
                            <Compass class="w-3 h-3" />
                            快速规划预览
                          </button>
                          <button
                            @click="router.push('/career-planning')"
                            class="px-3 py-1.5 rounded-lg border border-white/10 bg-white/[0.02] text-xs text-gray-400 hover:text-gray-200 hover:border-white/20 hover:bg-white/[0.04] transition-all duration-300"
                          >
                            前往完整功能页
                          </button>
                        </template>
                        <template v-else>
                          <p class="text-xs text-gray-500 text-center leading-relaxed">
                            暂无职业规划记录<br>
                            请在职业规划页生成一次职业蓝图
                          </p>
                          <button
                            @click="router.push('/career-planning')"
                            class="px-3 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/[0.06] text-xs text-cyan-300 font-medium hover:bg-cyan-500/15 hover:border-cyan-400/50 transition-all duration-300"
                          >
                            前往完整功能页
                          </button>
                        </template>
                      </div>
                    </transition>
                  </div>

                  <!-- Phase B：雷达图数据来源提示 + 手动选择恢复按钮 -->
                  <div class="mt-2 flex items-center justify-center gap-2 flex-wrap">
                    <div class="flex items-center gap-1.5">
                      <div
                        class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                        :class="radarSourceHint.type === 'empty'
                          ? 'bg-gray-600'
                          : radarSourceHint.type === 'manual'
                            ? 'bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.7)]'
                            : radarSourceHint.type === 'resume'
                              ? 'bg-purple-400 shadow-[0_0_6px_rgba(168,85,247,0.6)]'
                              : 'bg-pink-400 shadow-[0_0_6px_rgba(236,72,153,0.6)]'"
                      ></div>
                      <span
                        class="text-xs"
                        :class="radarSourceHint.type === 'empty'
                          ? 'text-gray-600 italic'
                          : radarSourceHint.type === 'manual'
                            ? 'text-cyan-300/90'
                            : 'text-gray-500'"
                      >{{ radarSourceHint.label }}</span>
                    </div>
                    <button
                      v-if="hasManualSelection"
                      @click="restoreAutoRadar"
                      class="text-[10px] px-2 py-0.5 rounded-full border border-cyan-500/25 bg-cyan-500/[0.06] text-cyan-300/90 hover:text-cyan-200 hover:border-cyan-400/50 transition-all duration-200"
                      title="恢复显示最新一次评估"
                    >恢复最新</button>
                  </div>
                </div>

                <!-- 卡片 4：智能预测看板 (骨架版) -->
                <div class="bg-white/[0.015] backdrop-blur-xl border border-white/5 rounded-2xl p-4 shadow-[inset_0_0_20px_rgba(255,255,255,0.01)] transition-all duration-500 hover:-translate-y-1 hover:bg-white/[0.03] hover:border-purple-500/20 hover:shadow-[0_10px_30px_rgba(168,85,247,0.1)] group">
                  <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2 min-w-0">
                      <h3 class="text-xs font-semibold text-gray-300 shrink-0">智能预测</h3>
                      <!-- 目标志愿：有值时显示徽章，无值时显示占位提示（Requirements 15.1, 15.2, 15.3） -->
                      <span
                        v-if="targetGoalDisplay"
                        class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 border border-indigo-500/25 text-indigo-300 font-medium truncate max-w-[140px]"
                        :title="targetGoalDisplay"
                      >🎯 {{ targetGoalDisplay }}</span>
                      <span
                        v-else
                        class="text-xs text-gray-600 italic"
                      >设置目标志愿</span>
                    </div>
                    <div class="flex items-center gap-1.5 bg-indigo-500/10 backdrop-blur-sm border border-indigo-500/20 rounded-full px-2.5 py-1 shadow-[0_0_8px_rgba(99,102,241,0.1)]">
                      <div class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse shadow-[0_0_6px_rgba(129,140,248,0.8)]"></div>
                      <span class="text-xs text-indigo-300/80 font-mono">AI 计算中</span>
                    </div>
                  </div>
                  <div class="space-y-2.5">
                    <!-- 冲 -->
                    <div class="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 transition-all duration-300 hover:bg-rose-500/10 cursor-default">
                      <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold tracking-wider shadow-[0_0_6px_rgba(244,63,94,0.3)]">冲</span>
                        <span class="text-xs text-gray-500">胜率 30%-50%</span>
                      </div>
                      <div class="flex gap-2">
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.2s;"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.4s;"></div>
                      </div>
                    </div>
                    <!-- 稳 -->
                    <div class="bg-blue-500/5 border border-blue-500/10 rounded-xl p-3 transition-all duration-300 hover:bg-blue-500/10 cursor-default">
                      <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-semibold tracking-wider shadow-[0_0_6px_rgba(59,130,246,0.3)]">稳</span>
                        <span class="text-xs text-gray-500">胜率 60%-80%</span>
                      </div>
                      <div class="flex gap-2">
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.3s;"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.5s;"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.7s;"></div>
                      </div>
                    </div>
                    <!-- 保 -->
                    <div class="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3 transition-all duration-300 hover:bg-emerald-500/10 cursor-default">
                      <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold tracking-wider shadow-[0_0_6px_rgba(16,185,129,0.3)]">保</span>
                        <span class="text-xs text-gray-500">胜率 95%以上</span>
                      </div>
                      <div class="flex gap-2">
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.6s;"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 0.8s;"></div>
                        <div class="h-6 w-full bg-white/5 border border-white/5 rounded backdrop-blur-sm animate-pulse" style="animation-delay: 1s;"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部 Dock 输入框 - 通用职业助手（浮动 + 可折叠） -->
          <ChatDock
            ref="chatDockRef"
            :placeholder="chatPlaceholder"
            :carouselText="currentCarouselText"
            :carouselFade="carouselFade"
            @send="sendGeneralChatMessage"
            @new-chat="handleChatDockNewChat"
            @toast="showToastMsg"
          />
        </div>
      </div>
    </div>

    <!-- 全局简历更新对话框 -->
    <div v-if="showResumeDialog" class="fixed inset-0 z-[100] flex items-center justify-center">
      <!-- 背景遮罩 -->
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="cancelResumeUpdate"></div>
      
      <!-- 对话框内容 -->
      <div class="relative z-10 w-full max-w-md mx-4 bg-[#0f0f15]/95 backdrop-blur-xl border border-purple-500/30 rounded-2xl p-6 shadow-2xl shadow-purple-500/20"
        style="animation: dialogFadeIn 0.3s ease-out;">
        <!-- 标题 -->
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
            <Upload class="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 class="text-lg font-semibold text-white">检测到新简历文件</h3>
            <p class="text-xs text-gray-500">{{ pendingFileName }}</p>
          </div>
        </div>

        <!-- 内容预览 -->
        <div class="bg-white/5 rounded-xl p-3 mb-4 max-h-32 overflow-y-auto">
          <p class="text-xs text-gray-400 leading-relaxed line-clamp-4">{{ pendingResumeText.substring(0, 200) }}...</p>
        </div>

        <!-- 提示文字 -->
        <p class="text-sm text-gray-300 mb-6">
          是否覆盖并更新全局简历库？更新后所有功能将使用此简历内容。
        </p>

        <!-- 按钮组 -->
        <div class="flex gap-3">
          <button
            @click="cancelResumeUpdate"
            class="flex-1 py-3 rounded-xl border border-white/10 text-gray-400 hover:bg-white/5 hover:text-white transition-all duration-300 flex items-center justify-center gap-2"
          >
            <X class="w-4 h-4" />
            取消
          </button>
          <button
            @click="confirmResumeUpdate"
            class="flex-1 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-medium hover:shadow-lg hover:shadow-purple-500/30 transition-all duration-300 flex items-center justify-center gap-2"
          >
            <CheckCircle class="w-4 h-4" />
            确认更新
          </button>
        </div>
      </div>
    </div>

    <!-- 面试舱门模态框 -->
    <div v-if="showInterviewModal" class="fixed inset-0 z-[100] flex items-center justify-center">
      <!-- 背景遮罩 -->
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" @click="closeInterviewModal"></div>
      
      <!-- 舱门对话框 -->
      <div class="relative z-10 w-full max-w-lg mx-4 bg-[#0f0f15]/95 backdrop-blur-xl border border-pink-500/30 rounded-2xl shadow-2xl shadow-pink-500/20 overflow-hidden"
        style="animation: dialogFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;">
        
        <!-- 顶部装饰线 -->
        <div class="h-1 w-full bg-gradient-to-r from-pink-500 via-fuchsia-500 to-purple-500"></div>
        
        <div class="p-6">
          <!-- 标题区 -->
          <div class="flex items-center gap-3 mb-5">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500/20 to-fuchsia-500/20 border border-pink-500/30 flex items-center justify-center">
              <Bot class="w-6 h-6 text-pink-400" />
            </div>
            <div>
              <h3 class="text-xl font-bold text-white">即将进入高压面试舱</h3>
              <p class="text-xs text-gray-500 mt-0.5">AI 面试官已就绪，等待目标锁定</p>
            </div>
          </div>

          <!-- 简历状态提示 -->
          <div class="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg bg-green-500/5 border border-green-500/20">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
            <p class="text-xs text-green-400">系统已加载您的全局简历</p>
          </div>

          <!-- JD 输入区 -->
          <div class="mb-5">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300 mb-2">
              <span class="text-pink-400">*</span>
              请贴入您本次要挑战的岗位描述 (JD)
            </label>
            <textarea
              v-model="interviewJd"
              rows="5"
              placeholder="在此粘贴目标岗位的完整描述，包括岗位要求、技术栈、职责等信息..."
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 resize-none focus:outline-none transition-all duration-300 focus:border-pink-500/50 focus:ring-2 focus:ring-pink-500/20 focus:shadow-[0_0_20px_rgba(236,72,153,0.15)] text-sm leading-relaxed"
            ></textarea>
          </div>

          <!-- 内测免单区 -->
          <div class="mb-5 p-4 rounded-xl border bg-gradient-to-br from-pink-500/5 to-purple-500/5 border-pink-500/20">
            <p class="text-center text-sm font-semibold text-pink-300 mb-3">👑 内测阶段 · 尊享免单</p>
            <div class="bg-white rounded-2xl p-4 w-44 h-44 mx-auto flex items-center justify-center shadow-lg shadow-white/10">
              <QrcodeVue :value="mockPayUrl" :size="140" level="H" />
            </div>
            <p class="text-center text-xs text-gray-500 mt-3">扫码获取内测福利</p>
          </div>

          <!-- 按钮组 -->
          <button
            @click="unlockInterview"
            :disabled="!interviewJd.trim() || isInterviewUnlocking"
            class="shimmer-btn w-full py-4 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-pink-500 to-fuchsia-500 text-white shadow-lg shadow-pink-500/30 hover:shadow-xl hover:shadow-pink-500/50"
          >
            <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
            <Loader2 v-if="isInterviewUnlocking" class="w-4 h-4 animate-spin relative z-10" />
            <CheckCircle v-else class="w-4 h-4 relative z-10" />
            <span class="relative z-10">{{ isInterviewUnlocking ? '舱门开启中...' : '直接开启挑战 (已免单)' }}</span>
          </button>

          <!-- 关闭按钮 -->
          <button
            @click="closeInterviewModal"
            class="w-full mt-3 py-3 rounded-xl border border-white/10 text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all duration-300 text-sm flex items-center justify-center gap-2"
          >
            <X class="w-4 h-4" />
            暂不挑战，返回工作台
          </button>
        </div>
      </div>
    </div>

    <!-- SetupModal 挂载 -->
    <SetupModal
      v-if="showSetupModal"
      @close="showSetupModal = false"
      @complete="handleSetupComplete"
    />

    <!-- DataSourceModal 挂载（数据面板设置，与 SetupModal 解耦） -->
    <DataSourceModal
      :visible="showDataSourceModal"
      :records="dataSourceRecords"
      :activeType="activeDataTab"
      @close="showDataSourceModal = false"
      @select="handleDataSourceSelect"
    />

    <!-- ChatPreviewModal 挂载：预览 agent_ 类别的历史对话（Requirements 13.1, 13.5, 13.6） -->
    <ChatPreviewModal
      :visible="showChatPreviewModal"
      :recordId="chatPreviewRecordId"
      @load-context="handleChatPreviewLoadContext"
      @close="handleChatPreviewClose"
    />

    <!-- KnowledgePanel 悬浮面板：知识库资产背包 -->
    <KnowledgePanel v-model="showKnowledgePanel" />

    <!-- CareerPreviewPanel 浮窗：职业规划快速预览（支持上一条/下一条翻阅） -->
    <CareerPreviewPanel
      :visible="showCareerPreview"
      :records="careerRecords"
      :initialIndex="careerPreviewIndex"
      @close="closeCareerPreview"
      @go-full="goCareerFull"
    />
  </div>
</template>

<style scoped>
.app-container {
  background-color: #050505;
}

.hide-scrollbar {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}

.feature-slider-wrapper {
  --feature-card-width: 100%;
}

@media (min-width: 640px) {
  .feature-slider-wrapper {
    --feature-card-width: 50%;
  }
}

@media (min-width: 768px) {
  .feature-slider-wrapper {
    --feature-card-width: 33.333333%;
  }
}

.feature-slider-track {
  will-change: transform;
}

.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translate(-50%, -12px);
}

/* 继续上次区块：空态 ↔ 有数据 切换过渡（Requirements 6.1, 6.2, 6.3） */
.onboarding-fade-enter-active,
.onboarding-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.onboarding-fade-enter-from,
.onboarding-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.input-wrapper:focus-within {
  border-color: rgba(168, 85, 247, 0.5) !important;
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.2) !important;
}

.menu-item:hover {
  position: relative;
}

.menu-item:hover::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(to bottom, #a855f7, #4f46e5);
  border-radius: 0 2px 2px 0;
}

.card {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

button.bg-gradient-to-r.from-purple-500.to-indigo-600 {
  box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse-slow {
  0%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.1);
    opacity: 1;
  }
}

@keyframes pulse-slower {
  0%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.1);
    opacity: 1;
  }
}

.animate-pulse-slow {
  animation: pulse-slow 8s ease-in-out infinite;
}

.animate-pulse-slower {
  animation: pulse-slower 8s ease-in-out infinite;
  animation-delay: -4s;
}

/* 入场动画 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
  opacity: 0;
}

/* 动画延迟 */
.animation-delay-0 {
  animation-delay: 0s;
}

.animation-delay-100 {
  animation-delay: 0.1s;
}

.animation-delay-200 {
  animation-delay: 0.2s;
}

.animation-delay-300 {
  animation-delay: 0.3s;
}

.animation-delay-400 {
  animation-delay: 0.4s;
}

.animation-delay-500 {
  animation-delay: 0.5s;
}

.menu-item {
  transition: all 0.3s ease;
}

.menu-item:hover span:last-child {
  color: white;
}

.quick-action {
  transition: all 0.2s ease;
}

@keyframes dialogFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dashboard-markdown :deep(h1) { font-size: 1.2em; font-weight: 700; margin: 0.5em 0 0.3em; color: #67e8f9; }
.dashboard-markdown :deep(h2) { font-size: 1.1em; font-weight: 600; margin: 0.4em 0 0.2em; color: #22d3ee; }
.dashboard-markdown :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 0.3em 0 0.15em; color: #06b6d4; }
.dashboard-markdown :deep(strong), .dashboard-markdown :deep(b) { color: #67e8f9; font-weight: 700; }
.dashboard-markdown :deep(p) { margin: 0.2em 0; color: rgba(229, 231, 235, 0.9); }
.dashboard-markdown :deep(ul), .dashboard-markdown :deep(ol) { padding-left: 1.2em; margin: 0.2em 0; }
.dashboard-markdown :deep(li) { margin: 0.1em 0; color: rgba(229, 231, 235, 0.85); }
.dashboard-markdown :deep(li)::marker { color: #06b6d4; }
.dashboard-markdown :deep(blockquote) { border-left: 3px solid rgba(6, 182, 212, 0.35); padding: 0.2em 0.6em; margin: 0.3em 0; background: rgba(6, 182, 212, 0.04); border-radius: 0 6px 6px 0; color: rgba(229, 231, 235, 0.7); }
.dashboard-markdown :deep(code) { background: rgba(6, 182, 212, 0.1); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.88em; color: #67e8f9; font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.dashboard-markdown :deep(pre) { background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(6, 182, 212, 0.12); border-radius: 8px; padding: 0.6em; overflow-x: auto; margin: 0.3em 0; }
.dashboard-markdown :deep(pre code) { background: none; padding: 0; border-radius: 0; color: rgba(229, 231, 235, 0.85); }

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

.system-knowledge-tag-sidebar {
  border: 1px solid rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.06);
  animation: breatheGlow 3s ease-in-out infinite;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.08), inset 0 0 6px rgba(16, 185, 129, 0.04);
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

.feature-card {
  will-change: transform, opacity, filter;
}
.feature-active {
  filter: blur(0);
}
.feature-inactive {
  filter: blur(1px);
}
.feature-inactive:hover {
  filter: blur(0);
}

/* Dashboard 专属极光沉浮动画 */
@keyframes ambient-drift-1 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.7; }
  50% { transform: translate(3vw, 5vh) scale(1.1); opacity: 1; }
}

@keyframes ambient-drift-2 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.6; }
  50% { transform: translate(-4vw, -4vh) scale(1.15); opacity: 1; }
}

@keyframes ambient-center-pulse {
  0%, 100% { opacity: 0.4; transform: translate(-50%, -50%) scale(0.95); }
  50% { opacity: 0.9; transform: translate(-50%, -50%) scale(1.05); }
}

.animate-ambient-1 {
  animation: ambient-drift-1 12s ease-in-out infinite;
}

.animate-ambient-2 {
  animation: ambient-drift-2 15s ease-in-out infinite;
}

.animate-ambient-center {
  animation: ambient-center-pulse 8s ease-in-out infinite;
}

.left-sidebar::-webkit-scrollbar,
.main-content::-webkit-scrollbar,
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.left-sidebar::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track,
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.left-sidebar::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb,
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}
.left-sidebar::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover,
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(168, 85, 247, 0.5);
}

@keyframes boot-up-bar {
  0% { transform: scaleX(0); transform-origin: left; }
  100% { transform: scaleX(1); transform-origin: left; }
}
.animate-boot-bar {
  animation: boot-up-bar 1.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.cyber-border-wrapper {
  position: absolute;
  inset: 0;
  border-radius: 1.5rem;
  padding: 2px;
  pointer-events: none;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  overflow: hidden;
  z-index: 0;
}
.cyber-border-inner {
  position: absolute;
  inset: -50%;
  background: conic-gradient(from 0deg, transparent 75%, var(--glow-color) 100%);
  animation: cyber-spin 3s linear infinite;
}
@keyframes cyber-spin {
  to { transform: rotate(360deg); }
}

.widget-fade-enter-active,
.widget-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.widget-fade-enter-from {
  opacity: 0;
  transform: translateX(10px) scale(0.98);
}
.widget-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px) scale(0.98);
}

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

/* 顶部高亮分隔线：与 Bento 卡片视觉层级关联 */
.chat-dock-accent {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(168, 85, 247, 0.0) 8%,
    rgba(168, 85, 247, 0.45) 30%,
    rgba(34, 211, 238, 0.55) 50%,
    rgba(168, 85, 247, 0.45) 70%,
    rgba(168, 85, 247, 0.0) 92%,
    transparent 100%
  );
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.18);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}

/* 折叠态最小标题栏：维持赛博毛玻璃质感，升级为紫青双层描边 */
.chat-dock-collapsed {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.38), 0 0 14px rgba(168, 85, 247, 0.18);
  /* 慢呼吸动效：让用户知道它"活着" */
  animation: chat-dock-pill-breathe 3.2s ease-in-out infinite;
}

@keyframes chat-dock-pill-breathe {
  0%, 100% { box-shadow: 0 8px 24px rgba(0,0,0,0.38), 0 0 10px rgba(168,85,247,0.14); }
  50%      { box-shadow: 0 8px 28px rgba(0,0,0,0.42), 0 0 20px rgba(34,211,238,0.22); }
}

@media (prefers-reduced-motion: reduce) {
  .chat-dock-collapsed { animation: none; }
}

/* 折叠按钮的包裹容器（用于 tooltip 定位） */
.chat-dock-fold-wrap {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

/* 折叠按钮 hover 反馈 */
.chat-dock-fold-btn:hover {
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.22);
  transform: scale(1.08);
}
.chat-dock-fold-btn:active {
  transform: scale(0.96);
}

/* 内联 tooltip：折叠按钮 hover 时从上方滑入 */
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

/* 减少动效偏好用户：去除位移过渡，仅保留淡入淡出 */
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
