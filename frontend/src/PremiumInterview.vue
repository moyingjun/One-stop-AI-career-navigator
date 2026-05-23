<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Send, UserCircle, Cpu, Loader2, AlertTriangle, Sprout, Briefcase, Flame } from 'lucide-vue-next'
import { marked } from 'marked'
import FeaturePageShell from './components/FeaturePageShell.vue'
import ActionDock from './components/ActionDock.vue'
import MetricCard from './components/MetricCard.vue'
import SidebarEducationPlaceholder from './components/SidebarEducationPlaceholder.vue'
import BaseModal from './components/BaseModal.vue'
import CyberRadarChart from './components/CyberRadarChart.vue'
import GlobalProviderSwitcher from './components/GlobalProviderSwitcher.vue'
import { streamInterviewChat } from '@/services/llm_service.js'
import { getAuthHeaders } from '@/services/authService.js'
import { showToast, resolveLoader } from '@/utils/uiFallbacks'
import { upsertSession } from '@/services/historyClient.js'
import { useUserStore } from '@/stores/userStore'
import { useLlmProviderStore } from '@/stores/llmProviderStore'

const userStore = useUserStore()
const llmProviderStore = useLlmProviderStore()

const generateUUID = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return Date.now().toString(36) + Math.random().toString(36).substring(2)
}

const API_BASE_URL = (() => {
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000/api';
  }
  return `${window.location.protocol}//${hostname}/api`;
})();

const CHAT_API_URL = `${API_BASE_URL}/interview/chat`;
const router = useRouter()
const route = useRoute()

const isRestoring = ref(false)

const currentSessionId = ref(generateUUID())

const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const isAiSpeaking = ref(false)
const isInterviewEnded = ref(false)
const isEvaluationDone = ref(false)
const isEvaluating = ref(false)
const evaluateError = ref('')
const candidateName = ref('')
const targetRole = ref('')
const resumeText = ref('')
const interviewJd = ref('')
const strikeCount = ref(0)
const strikeTerminated = ref(false)
const interviewDifficulty = ref('standard')
const showDifficultyModal = ref(false)

const themeConfig = computed(() => {
  if (interviewDifficulty.value === 'beginner') {
    return {
      primary: 'emerald',
      gradient: 'from-emerald-500 to-green-500',
      text: 'text-emerald-400',
      border: 'border-emerald-500',
      borderLight: 'border-emerald-500/20',
      bg: 'bg-emerald-500/20',
      shadow: 'shadow-emerald-500/30',
      color: '#34d399',
      colorRgba: 'rgba(52, 211, 153, 0.6)'
    }
  } else if (interviewDifficulty.value === 'standard') {
    return {
      primary: 'blue',
      gradient: 'from-blue-500 to-cyan-500',
      text: 'text-blue-400',
      border: 'border-blue-500',
      borderLight: 'border-blue-500/20',
      bg: 'bg-blue-500/20',
      shadow: 'shadow-blue-500/30',
      color: '#60a5fa',
      colorRgba: 'rgba(96, 165, 250, 0.6)'
    }
  } else {
    return {
      primary: 'fuchsia',
      gradient: 'from-fuchsia-500 to-pink-500',
      text: 'text-fuchsia-400',
      border: 'border-fuchsia-500',
      borderLight: 'border-fuchsia-500/20',
      bg: 'bg-fuchsia-500/20',
      shadow: 'shadow-fuchsia-500/30',
      color: '#e879f9',
      colorRgba: 'rgba(232, 121, 249, 0.6)'
    }
  }
})

const themeIcon = computed(() => {
  if (interviewDifficulty.value === 'beginner') return Sprout
  if (interviewDifficulty.value === 'standard') return Briefcase
  return Flame
})

// FeaturePageShell variant 与 stage badges：随难度切换主色调
const themeVariant = computed(() => {
  if (interviewDifficulty.value === 'beginner') return 'emerald'
  if (interviewDifficulty.value === 'p8') return 'pink'
  return 'cyan'
})

const stageBadges = computed(() => {
  const tone = themeVariant.value
  return [
    { label: '训练舱', tone },
    { label: '实时评分', tone },
    { label: '复盘', tone }
  ]
})

// 异步解析 StreamingLoader（缺失时降级到 InlineLoaderFallback）
const StreamingLoaderComp = ref(null)
resolveLoader().then((c) => { StreamingLoaderComp.value = c }).catch(() => {})

const pressureScore = ref(50)
const pressureColor = computed(() => {
  if (pressureScore.value >= 70) return 'from-green-500 to-emerald-400'
  if (pressureScore.value >= 40) return 'from-yellow-500 to-amber-400'
  return 'from-red-500 to-rose-400'
})
const pressureLabel = computed(() => {
  if (pressureScore.value >= 70) return '表现优秀'
  if (pressureScore.value >= 40) return '表现一般'
  return '需要努力'
})

const radarScores = ref({
  professional: 2,
  logic: 2,
  communication: 2,
  problemSolving: 2,
  potential: 2,
  resilience: 2
})

const mentorComment = ref('')

const RADAR_LABELS = ['professional', 'logic', 'communication', 'problemSolving', 'potential', 'resilience']
const RADAR_CENTER = 130
const RADAR_MAX_RADIUS = 80

// 压力分趋势 / 色调：>= 60 上升、<= 40 下降、其它持平；色调随分数切换
const pressureTrend = computed(() => {
  if (pressureScore.value >= 60) return 'up'
  if (pressureScore.value <= 40) return 'down'
  return 'flat'
})

const pressureTone = computed(() => {
  if (pressureScore.value >= 70) return 'emerald'
  if (pressureScore.value >= 40) return 'cyan'
  return 'pink'
})

// 复盘弹窗用的雷达图数据（喂给 CyberRadarChart）
const radarChartData = computed(() => ({
  indicators: [
    { name: '专业技能', max: 100 },
    { name: '逻辑分析', max: 100 },
    { name: '沟通表达', max: 100 },
    { name: '问题解决', max: 100 },
    { name: '综合潜力', max: 100 },
    { name: '抗压韧性', max: 100 }
  ],
  values: [
    radarScores.value.professional,
    radarScores.value.logic,
    radarScores.value.communication,
    radarScores.value.problemSolving,
    radarScores.value.potential,
    radarScores.value.resilience
  ]
}))

const radarPoints = computed(() => {
  const angles = RADAR_LABELS.map((_, i) => (i * 60 - 90) * Math.PI / 180)
  return angles.map((angle, i) => {
    const score = radarScores.value[RADAR_LABELS[i]]
    const r = (score / 100) * RADAR_MAX_RADIUS
    return `${RADAR_CENTER + r * Math.cos(angle)},${RADAR_CENTER + r * Math.sin(angle)}`
  }).join(' ')
})

const TECH_KEYWORDS = [
  'Java', 'SQL', 'Spring', 'SpringBoot', 'SpringMVC', 'MyBatis', 'MyBatisPlus',
  'Linux', 'Markdown', 'Python', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Vue3',
  'Node\\.js', 'Nodejs', 'Docker', 'Kubernetes', 'K8s', 'MySQL', 'Redis', 'MongoDB',
  'Git', 'HTML', 'CSS', 'C\\+\\+', 'C#', 'Go', 'Golang', 'Rust', 'Swift', 'Kotlin',
  'PHP', 'Ruby', 'AWS', 'Azure', 'GCP', 'Nginx', 'Tomcat', 'Maven', 'Gradle',
  'Jenkins', 'GitLab', 'GitHub', 'RabbitMQ', 'Kafka', 'Zookeeper', 'Elasticsearch',
  'ES', 'Hadoop', 'Spark', 'Flink', 'Hive', 'HBase', 'ClickHouse', 'PostgreSQL',
  'Oracle', 'SQLite', 'Neo4j', 'GraphQL', 'RESTful', 'WebSocket', 'gRPC',
  'Microservices', 'DDD', 'TDD', 'BDD', 'CI\\/CD', 'DevOps', 'Agile', 'Scrum',
  'JPA', 'Hibernate', 'Shiro', 'SpringSecurity', 'OAuth', 'JWT', 'SaaS', 'PaaS',
  'IaaS', 'LaTeX', 'Matlab', 'R语言', 'Tableau', 'PowerBI', 'Excel', 'VBA',
  'Android', 'iOS', 'Flutter', 'ReactNative', 'UniApp', 'WeChat', '小程序',
  'Webpack', 'Vite', 'Babel', 'ESLint', 'Prettier', 'Tailwind', 'ElementUI',
  'AntDesign', 'Bootstrap', 'jQuery', 'Axios', 'Vuex', 'Pinia', 'Redux',
  'Sass', 'Less', 'Stylus', 'Shell', 'Bash', 'PowerShell', 'Ansible',
  'Terraform', 'Prometheus', 'Grafana', 'SkyWalking', 'CAT', 'Arthas',
  'Netty', 'MINA', 'Tio', 'XXL-Job', 'EasyExcel', 'Hutool', 'Lombok',
  'Swagger', 'Postman', 'JMeter', 'Selenium', 'Appium', 'Charles', 'Fiddler'
]

const formattedResumeHtml = computed(() => {
  if (!resumeText.value || !resumeText.value.trim()) return ''
  const escaped = resumeText.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  const lines = escaped.split('\n')
  const techRegex = new RegExp('\\b(' + TECH_KEYWORDS.join('|') + ')\\b', 'gi')
  return lines.map(line => {
    const labelMatch = line.match(/^([^：:]{1,20})([：:])/)
    let processed = ''
    if (labelMatch) {
      const label = labelMatch[1]
      const colon = labelMatch[2]
      const rest = line.substring(label.length + colon.length)
      const highlightedRest = rest.replace(techRegex, '<span class="px-1.5 py-0.5 bg-white/10 text-cyan-300 rounded text-xs font-mono border border-white/5">$1</span>')
      processed = `<span class="text-white font-semibold tracking-wide">${label}${colon}</span>${highlightedRest}`
    } else {
      processed = line.replace(techRegex, '<span class="px-1.5 py-0.5 bg-white/10 text-cyan-300 rounded text-xs font-mono border border-white/5">$1</span>')
    }
    return processed
  }).join('<br/>')
})

const isResumeValid = computed(() => {
  return resumeText.value && resumeText.value.trim().length >= 20
})

const ambientMood = computed(() => {
  const aiMsgs = messages.value.filter(m => m.role === 'ai')
  if (aiMsgs.length === 0) return 'neutral'
  const lastAiContent = aiMsgs[aiMsgs.length - 1].content
  if (lastAiContent.startsWith('[点头]') || lastAiContent.startsWith('[鼓励]')) return 'positive'
  if (lastAiContent.startsWith('[皱眉]') || lastAiContent.startsWith('[质疑]') || lastAiContent.startsWith('[嘲讽]') || lastAiContent.startsWith('[冷哼]') || lastAiContent.startsWith('[挑眉]')) return 'negative'
  if (lastAiContent.startsWith('[思考]') || lastAiContent.startsWith('[提示]')) return 'neutral'
  return 'neutral'
})

const messagesContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const calculatePressure = () => {
  const userMsgs = messages.value.filter(m => m.role === 'user')
  if (userMsgs.length === 0) {
    pressureScore.value = 50
    return
  }
  
  const totalChars = userMsgs.reduce((sum, m) => sum + m.content.length, 0)
  const avgChars = totalChars / userMsgs.length
  
  let score = 50
  
  if (avgChars > 100) score += 15
  else if (avgChars > 50) score += 8
  else if (avgChars < 20) score -= 15
  else if (avgChars < 30) score -= 8
  
  const aiMsgs = messages.value.filter(m => m.role === 'ai')
  const lastAiMsg = aiMsgs[aiMsgs.length - 1]
  if (lastAiMsg) {
    const content = lastAiMsg.content.toLowerCase()
    if (content.includes('[点头]') || content.includes('很好') || content.includes('优秀')) {
      score += 15
    }
    if (content.includes('[皱眉]') || content.includes('[质疑]') || content.includes('敷衍')) {
      score -= 15
    }
  }
  
  pressureScore.value = Math.max(10, Math.min(95, score))
}

const cleanMessage = (text) => {
  if (!text) return ''
  let cleaned = text.replace(/\[SCORE_UPDATE\][\s\S]*?\[\/SCORE_UPDATE\]/g, '')
  cleaned = cleaned.replace(/\[SCORE_UPDATE\][\s\S]*$/, '')
  return cleaned.trim()
}

const getEmotionClass = (content) => {
  const cleaned = cleanMessage(content)
  if (cleaned.startsWith('[点头]') || cleaned.startsWith('[鼓励]')) return 'emotion-approve'
  if (cleaned.startsWith('[思考]') || cleaned.startsWith('[提示]')) return 'emotion-think'
  if (cleaned.startsWith('[皱眉]') || cleaned.startsWith('[挑眉]')) return 'emotion-frown'
  if (cleaned.startsWith('[质疑]') || cleaned.startsWith('[嘲讽]') || cleaned.startsWith('[冷哼]')) return 'emotion-doubt'
  return ''
}

const getEmotionIcon = (content) => {
  const cleaned = cleanMessage(content)
  if (cleaned.startsWith('[点头]')) return '👍'
  if (cleaned.startsWith('[思考]')) return '🤔'
  if (cleaned.startsWith('[皱眉]')) return '😐'
  if (cleaned.startsWith('[质疑]')) return '❓'
  if (cleaned.startsWith('[提示]')) return '💡'
  if (cleaned.startsWith('[鼓励]')) return '💪'
  if (cleaned.startsWith('[冷哼]')) return '😤'
  if (cleaned.startsWith('[挑眉]')) return '🧐'
  if (cleaned.startsWith('[嘲讽]')) return '😈'
  return ''
}

const addMessage = (role, content) => {
  messages.value.push({
    role,
    content,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    isNew: false
  })
  scrollToBottom()
  if (role === 'user' || role === 'ai') {
    nextTick(() => calculatePressure())
  }
}

const initInterview = async () => {
  const recordId = route.query.id
  if (recordId) {
    isRestoring.value = true
    try {
      const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history/${recordId}`, {
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }
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
              if (extra.jd_text) interviewJd.value = extra.jd_text
              if (extra.difficulty) interviewDifficulty.value = extra.difficulty
            } catch {}
          }

          if (record.chat_history) {
            try {
              const chatHist = typeof record.chat_history === 'string' ? JSON.parse(record.chat_history) : record.chat_history
              if (Array.isArray(chatHist) && chatHist.length > 0) {
                messages.value = chatHist.map(m => ({
                  role: m.role === 'user' ? 'user' : 'ai',
                  content: m.content || '',
                  timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
                  isNew: false
                }))
              }
            } catch {}
          }

          if (record.scores) {
            try {
              const scores = typeof record.scores === 'string' ? JSON.parse(record.scores) : record.scores
              const required = ['professional', 'logic', 'communication', 'problemSolving', 'potential', 'resilience']
              if (required.every(k => k in scores)) {
                radarScores.value = { ...radarScores.value, ...scores }
                // Phase 1：历史记录恢复时同步更新 Dashboard 雷达图
                userStore.updateRadarFromInterview(scores)
              }
            } catch {}
          }

          mentorComment.value = record.ai_result || ''
          messages.value.push({
            role: 'ai',
            content: `📋 历史面试评估已恢复\n\n**导师结语**：${record.ai_result || '无评价'}`,
            timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
            isNew: false
          })

          isInterviewEnded.value = true
          isEvaluationDone.value = true
          showResultModal.value = true
          // 恢复 session_id，后续再保存时 upsert 到同一条记录
          if (record.session_id) {
            currentSessionId.value = record.session_id
          }
          return
        }
      }
    } catch (err) {
      console.error('恢复历史记录失败:', err)
    } finally {
      isRestoring.value = false
    }
  }

  const name = localStorage.getItem('candidate_name') || ''
  targetRole.value = userStore.targetJob || localStorage.getItem('target_role') || localStorage.getItem('target_job') || ''
  resumeText.value = userStore.resumeText || localStorage.getItem('resume_text') || ''
  interviewJd.value = userStore.jobDescription || localStorage.getItem('job_description') || localStorage.getItem('current_interview_jd') || localStorage.getItem('jd_content') || ''

  candidateName.value = name

  showDifficultyModal.value = true
}

const startInterviewWithDifficulty = async () => {
  showDifficultyModal.value = false

  const name = candidateName.value
  const role = targetRole.value
  const resume = resumeText.value
  const jd = interviewJd.value

  isLoading.value = true
  isAiSpeaking.value = true
  try {
    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        user_query: `面试官您好，我是候选人${name || '未知'}，应聘岗位是${role || '未指定'}。请您直接根据我的简历开始向我提问。`,
        history: [],
        resume_text: resume,
        target_job: role,
        jd_text: jd,
        difficulty: interviewDifficulty.value,
        provider_id: llmProviderStore.getCurrentProviderId() || undefined
      })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    const reply = data.reply || `${name || '候选人'}你好，请直接开始1分钟的自我介绍。`
    addMessage('ai', reply)
  } catch (error) {
    console.error('初始化面试失败:', error)
    addMessage('ai', '面试官已就位，请输入你的第一段回答开始模拟。')
  } finally {
    isLoading.value = false
    isAiSpeaking.value = false
  }
}

const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value || isInterviewEnded.value || strikeTerminated.value) return

  const userMessage = userInput.value.trim()
  addMessage('user', userMessage)
  userInput.value = ''
  isLoading.value = true
  isAiSpeaking.value = true

  // 推入占位 AI 消息，供 onChunk 回调逐步追加内容（打字机效果）
  const aiMsg = { role: 'ai', content: '', timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }), isNew: true }
  messages.value.push(aiMsg)

  try {
    const history = messages.value
      .slice(0, -1)  // 排除刚推入的占位消息
      .map(msg => ({ role: msg.role, content: msg.content }))

    await streamInterviewChat(
      '/interview/chat',
      {
        user_query: userMessage,
        history,
        resume_text: resumeText.value,
        target_job: targetRole.value,
        jd_text: interviewJd.value,
        difficulty: interviewDifficulty.value,
        provider_id: llmProviderStore.getCurrentProviderId() || undefined
      },
      (chunk) => {
        // onChunk: 追加内容片段到占位消息
        aiMsg.content += chunk
        scrollToBottom()
      },
      (errMsg) => {
        // onError: 将错误信息追加到占位消息（内联展示，不弹窗）
        aiMsg.content += errMsg
        scrollToBottom()
      }
    )

    // 流结束后，从完整内容中提取 [SCORE_UPDATE] 标签并更新雷达图
    const scoreMatch = aiMsg.content.match(/\[SCORE_UPDATE\](\{[\s\S]*?\})\[\/SCORE_UPDATE\]/)
    if (scoreMatch) {
      try {
        const liveScores = JSON.parse(scoreMatch[1])
        const required = ['professional', 'logic', 'communication', 'problemSolving', 'potential', 'resilience']
        if (required.every(k => k in liveScores)) {
          radarScores.value = { ...radarScores.value, ...liveScores }
        }
      } catch {}
      // 从显示内容中移除评分标签（用户不可见）
      aiMsg.content = aiMsg.content.replace(/\[SCORE_UPDATE\]\{[\s\S]*?\}\[\/SCORE_UPDATE\]/g, '').trim()
    }

    // 检测 WARNING 标记，累计 strike 计数
    if (aiMsg.content.includes('[WARNING]')) {
      strikeCount.value++
      if (strikeCount.value >= 3) {
        strikeTerminated.value = true
        addMessage('ai', '🚫 检测到多次无效输入，面试被强制终止！')
        setTimeout(() => {
          endInterview()
        }, 1500)
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    aiMsg.content += '😵 导师正在开小差，请重新点击发送哦~'
  } finally {
    isLoading.value = false
    isAiSpeaking.value = false
  }
}

const showMatrixModal = ref(false)
const matrixLines = ref([])
const showResultModal = ref(false)
let matrixIntervalId = null

const extractResumeKeywords = (text) => {
  if (!text || text.trim().length < 10) return []
  const techMatches = text.match(/\b[A-Z][A-Za-z0-9#+.]{1,20}\b/g) || []
  const cnMatches = text.match(/[\u4e00-\u9fa5]{2,6}/g) || []
  const allKeywords = [...new Set([...techMatches, ...cnMatches])]
  const filtered = allKeywords.filter(k => {
    const lower = k.toLowerCase()
    return !['the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'shall', 'into', 'also', 'more', 'than', 'each', 'which', 'their', 'other', 'some', 'such', 'only', 'when', 'what', 'about', 'above', 'after', 'again', 'below', 'between', 'both', 'during', 'before', 'there', 'these', 'those', 'being', 'doing'].includes(lower)
  })
  const shuffled = filtered.sort(() => Math.random() - 0.5)
  return shuffled.slice(0, 5)
}

const generateMatrixLines = (resumeSource = '') => {
  const lines = []
  const phrases = [
    'INITIALIZING NEURAL SCAN...',
    'PARSING RESPONSE PATTERNS...',
    'CALCULATING PROFESSIONAL SCORE...',
    'ANALYZING LOGIC STRUCTURE...',
    'EVALUATING COMMUNICATION...',
    'MEASURING PROBLEM SOLVING...',
    'ASSESSING POTENTIAL MATRIX...',
    'CROSS-REFERENCING JD REQUIREMENTS...',
    'DETECTING EMOTIONAL PATTERNS...',
    'BUILDING COMPETENCY MODEL...',
    'GENERATING MENTOR INSIGHTS...',
    'FINALIZING EVALUATION REPORT...'
  ]
  const keywords = extractResumeKeywords(resumeSource)
  
  for (let i = 0; i < 25; i++) {
    const phrase = phrases[Math.floor(Math.random() * phrases.length)]
    const nums = Array.from({length: 20}, () => Math.floor(Math.random() * 2)).join('')
    if (keywords.length > 0 && Math.random() < 0.35) {
      const kw = keywords[Math.floor(Math.random() * keywords.length)]
      lines.push(`DEEP SCANNING RESUME KEYWORD: [${kw}] >> ${nums}`)
    } else {
      lines.push(`${phrase} [${nums}]`)
    }
  }
  return lines
}

const endInterview = async () => {
  const userMessages = messages.value.filter(m => m.role === 'user')
  const userMessageCount = userMessages.length
  
  const totalUserCharCount = userMessages.reduce((sum, m) => sum + m.content.length, 0)
  
  if (userMessageCount === 0 || totalUserCharCount < 20) {
    addMessage('ai', '【系统警告】检测到您的有效作答字数过少或涉嫌敷衍，系统拒绝生成能力图谱。本次面试已强行终止！')
    radarScores.value = { professional: 0, logic: 0, communication: 0, problemSolving: 0, potential: 0, resilience: 0 }
    isInterviewEnded.value = true
    return
  }

  isInterviewEnded.value = true
  
  showMatrixModal.value = true
  matrixLines.value = generateMatrixLines(resumeText.value)
  
  let lineIndex = 0
  matrixIntervalId = setInterval(() => {
    if (lineIndex < 20) {
      matrixLines.value = [...matrixLines.value.slice(-20), generateMatrixLines(resumeText.value)[0]]
      lineIndex++
    }
  }, 150)

  try {
    const response = await fetch(`${API_BASE_URL}/interview/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        user_query: "请根据对话记录生成 JSON 评估报告",
        history: messages.value,
        difficulty: interviewDifficulty.value,
        provider_id: llmProviderStore.getCurrentProviderId() || undefined
      })
    })

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    
    const resData = await response.json()
    
    if (matrixIntervalId) {
      clearInterval(matrixIntervalId)
      matrixIntervalId = null
    }
    
    if (resData.success && resData.data) {
      radarScores.value = {
        professional: resData.data.professional || 10,
        logic: resData.data.logic || 10,
        communication: resData.data.communication || 10,
        problemSolving: resData.data.problemSolving || 10,
        potential: resData.data.potential || 10,
        resilience: resData.data.resilience || 10
      }
      mentorComment.value = resData.data.comment || '无评价。'
      
      // Phase 1：打通 Dashboard 右侧雷达图 —— 面试评估完成时写入 interview 快照
      userStore.updateRadarFromInterview(radarScores.value)
      
      // 保存历史记录（session upsert，幂等，失败不阻断 UI 流程）
      try {
        await upsertSession(currentSessionId.value, {
          record_type: 'interview_session',
          user_input: `面试候选人：${candidateName.value}，岗位：${targetRole.value}`,
          ai_result: mentorComment.value,
          scores: radarScores.value,
          extra_data: {
            resume_text: resumeText.value.slice(0, 3000),
            target_role: targetRole.value,
            jd_text: interviewJd.value.slice(0, 2000),
            difficulty: interviewDifficulty.value
          },
          chat_history: messages.value.map(m => ({ role: m.role, content: m.content }))
        })
      } catch (saveErr) {
        console.error('保存历史记录失败:', saveErr)
        showToast('保存历史记录失败', { type: 'error' })
      }

      setTimeout(() => {
        showMatrixModal.value = false
        showResultModal.value = true
        isEvaluationDone.value = true
      }, 500)
    } else {
      throw new Error(resData.msg || "打分数据解析失败")
    }
  } catch (error) {
    if (matrixIntervalId) {
      clearInterval(matrixIntervalId)
      matrixIntervalId = null
    }
    console.error("生成评估失败:", error)
    showMatrixModal.value = false
    evaluateError.value = '评估引擎开小差了，请点击重试'
    addMessage('ai', '⚠️ 评估引擎暂时走神了，请点击下方「重新评估」按钮重试~')
  }
}

const retryEvaluate = () => {
  evaluateError.value = ''
  isInterviewEnded.value = false
  nextTick(() => {
    endInterview()
  })
}

const closeResultModal = () => {
  showResultModal.value = false
}

const goToCareerPlanning = () => {
  showResultModal.value = false
  router.push('/career-planning')
}

const handleEnter = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

onMounted(() => {
  initInterview()
})

onUnmounted(() => {
  if (matrixIntervalId) {
    clearInterval(matrixIntervalId)
    matrixIntervalId = null
  }
})
</script>

<template>
  <div class="min-h-[100dvh] relative overflow-hidden bg-[#020205] transition-all duration-1000" :class="{
    'ambient-negative': ambientMood === 'negative',
    'ambient-positive': ambientMood === 'positive',
    'ambient-neutral': ambientMood === 'neutral'
  }">
    <!-- 统一紫/青 blur 背景层 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vw] bg-purple-600/20 blur-[150px] rounded-full"></div>
      <div class="absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-cyan-600/15 blur-[150px] rounded-full"></div>
    </div>

    <!-- 动态网格 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute inset-0 grid-bg"></div>
      <div class="absolute inset-0" style="background: radial-gradient(ellipse at center, transparent 0%, #020205 75%);"></div>
    </div>

    <!-- CRT 扫描线覆盖层 -->
    <div class="crt-overlay absolute inset-0 pointer-events-none z-50"></div>

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

    <!-- 主内容：FeaturePageShell 三段骨架 -->
    <div class="relative z-10 w-full max-w-[1280px] mx-auto px-3 md:px-6 pt-14 pb-6">
      <!-- 升学占位项（三页共享） -->
      <div class="mb-3">
        <SidebarEducationPlaceholder />
      </div>

      <FeaturePageShell
        title="模拟面试"
        subtitle="沉浸式 AI 面试官 · 实时表现评估 · 六维复盘"
        :stage-badges="stageBadges"
        :variant="themeVariant"
        max-width="1280px"
      >
        <!-- ============ #control：难度选择 + 消息输入 ============ -->
        <template #control>
          <div class="interview-control space-y-4">
            <!-- 难度选择（模式切换条） -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-gray-200">训练舱模式</span>
                  <span class="text-[10px] text-gray-500 font-mono uppercase tracking-wider">SELECT DIFFICULTY</span>
                </div>
                <span class="text-[10px] text-gray-400 px-2 py-0.5 rounded-full border border-white/10 bg-white/[0.03]" data-test="stage-badge">
                  当前：{{ interviewDifficulty === 'p8' ? 'P8 压力面试' : interviewDifficulty === 'beginner' ? '温和鼓励' : '标准专业' }}
                </span>
              </div>
              <div class="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  @click="interviewDifficulty = 'beginner'"
                  :disabled="messages.length > 0 && !isInterviewEnded"
                  class="difficulty-btn px-3 py-2 rounded-lg text-xs font-semibold border-2 transition-all duration-200 flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                  :class="interviewDifficulty === 'beginner'
                    ? 'difficulty-btn--selected border-emerald-400 bg-emerald-500/15 text-emerald-200 ring-2 ring-emerald-500/30 shadow-[0_0_18px_rgba(16,185,129,0.25)]'
                    : 'border-white/10 hover:border-white/20 text-gray-400 hover:text-gray-200'"
                  data-test="difficulty-beginner"
                >
                  <Sprout class="w-3.5 h-3.5" />
                  <span>温和</span>
                </button>
                <button
                  type="button"
                  @click="interviewDifficulty = 'standard'"
                  :disabled="messages.length > 0 && !isInterviewEnded"
                  class="difficulty-btn px-3 py-2 rounded-lg text-xs font-semibold border-2 transition-all duration-200 flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                  :class="interviewDifficulty === 'standard'
                    ? 'difficulty-btn--selected border-cyan-400 bg-cyan-500/15 text-cyan-200 ring-2 ring-cyan-500/30 shadow-[0_0_18px_rgba(34,211,238,0.25)]'
                    : 'border-white/10 hover:border-white/20 text-gray-400 hover:text-gray-200'"
                  data-test="difficulty-standard"
                >
                  <Briefcase class="w-3.5 h-3.5" />
                  <span>标准</span>
                </button>
                <button
                  type="button"
                  @click="interviewDifficulty = 'p8'"
                  :disabled="messages.length > 0 && !isInterviewEnded"
                  class="difficulty-btn px-3 py-2 rounded-lg text-xs font-semibold border-2 transition-all duration-200 flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                  :class="interviewDifficulty === 'p8'
                    ? 'difficulty-btn--selected border-pink-400 bg-pink-500/15 text-pink-200 ring-2 ring-pink-500/30 shadow-[0_0_18px_rgba(236,72,153,0.25)]'
                    : 'border-white/10 hover:border-white/20 text-gray-400 hover:text-gray-200'"
                  data-test="difficulty-p8"
                >
                  <Flame class="w-3.5 h-3.5" />
                  <span>P8</span>
                </button>
              </div>
            </div>

            <!-- 消息输入 -->
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-2">你的回答</label>
              <textarea
                v-model="userInput"
                @keydown="handleEnter"
                placeholder="输入你的回答...（Enter 发送，Shift+Enter 换行）"
                rows="3"
                :disabled="isLoading || strikeTerminated"
                class="interview-textarea w-full rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 text-gray-200 placeholder-gray-500 focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed border"
                :class="[themeConfig.borderLight, 'focus:' + themeConfig.border, 'focus:ring-' + themeConfig.primary + '/20']"
                data-test="message-input"
              ></textarea>

              <!-- Strike 警告 -->
              <div v-if="strikeTerminated" class="mt-2 text-center">
                <p class="text-red-400 font-semibold text-xs">🚫 检测到多次无效输入，面试已被强制终止！</p>
              </div>
              <div v-else-if="strikeCount > 0 && strikeCount < 3" class="mt-2 text-center">
                <p class="text-amber-400 text-xs">⚠️ 警告 {{ strikeCount }}/3：检测到无效输入，再犯 {{ 3 - strikeCount }} 次将强制终止面试！</p>
              </div>
            </div>
          </div>
        </template>

        <!-- ============ #result：对话流 + 压力分 MetricCard ============ -->
        <template #result>
          <div class="interview-result relative">
            <!-- 专注模式脉冲光晕 -->
            <div v-if="isAiSpeaking" class="absolute inset-0 pointer-events-none z-0">
              <div class="focus-glow focus-glow-1"></div>
              <div class="focus-glow focus-glow-2"></div>
              <div class="focus-glow focus-glow-3"></div>
            </div>

            <div class="relative z-10 flex flex-col gap-3">
              <!-- 顶部 Header：面试官身份 + 在线状态（独立面板，避免与 MetricCard 混淆） -->
              <div class="interviewer-header rounded-xl border bg-black/35 backdrop-blur-xl px-3 py-2.5 md:px-4 md:py-3 flex items-center justify-between flex-wrap gap-2"
                :class="themeConfig.borderLight">
                <div class="flex items-center gap-2 md:gap-3">
                  <div class="w-9 h-9 rounded-full flex items-center justify-center shadow-lg relative" :class="['bg-gradient-to-br', themeConfig.gradient, themeConfig.shadow]">
                    <component :is="themeIcon" class="w-4 h-4 text-white" />
                    <div v-if="isAiSpeaking" class="absolute -right-1 -top-1 flex items-center gap-0.5">
                      <div class="voice-bar voice-bar-1"></div>
                      <div class="voice-bar voice-bar-2"></div>
                      <div class="voice-bar voice-bar-3"></div>
                      <div class="voice-bar voice-bar-4"></div>
                    </div>
                  </div>
                  <div>
                    <h2 class="text-sm md:text-base font-bold text-white">{{ interviewDifficulty === 'p8' ? 'P8 级' : interviewDifficulty === 'beginner' ? '温和鼓励' : '标准专业' }} AI 面试官</h2>
                    <p class="text-[10px] text-gray-400">{{ isAiSpeaking ? 'AI 正在审视你的回答…' : '沉浸式面试模式' }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <GlobalProviderSwitcher
                    :compact="true"
                    placement="bottom-right"
                    :status-override="isAiSpeaking ? 'Thinking...' : ''"
                  />
                </div>
              </div>

              <!-- 压力分 MetricCard（仪表盘 + 三卡同高） -->
              <div class="metrics-rail" data-test="pressure-score-card">
                <div class="metrics-rail__head">
                  <div class="flex items-center gap-2">
                    <span class="metrics-rail__dot" aria-hidden="true"></span>
                    <span class="text-[11px] font-mono uppercase tracking-wider text-gray-400">DASHBOARD · 实时仪表</span>
                  </div>
                  <span class="text-[10px] text-gray-500 font-mono">每轮自动刷新</span>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <MetricCard
                    :label="'实时表现评估'"
                    :value="pressureScore"
                    unit="/100"
                    :trend="pressureTrend"
                    :tone="pressureTone"
                  >
                    <span class="text-[11px]" :class="pressureScore >= 70 ? 'text-emerald-300' : pressureScore >= 40 ? 'text-cyan-300' : 'text-pink-300'">{{ pressureLabel }}</span>
                  </MetricCard>
                  <MetricCard
                    :label="'已交互轮次'"
                    :value="messages.filter(m => m.role === 'user').length"
                    unit="轮"
                    :tone="themeVariant"
                  />
                  <MetricCard
                    :label="'警告 / 状态'"
                    :value="strikeTerminated ? '已终止' : (strikeCount > 0 ? `${strikeCount}/3` : '正常')"
                    :tone="strikeTerminated ? 'pink' : (strikeCount > 0 ? 'pink' : 'emerald')"
                  />
                </div>
              </div>

              <!-- 对话气泡流（独立滚动容器：bounded height + overscroll-contain，避免冒泡到外层） -->
              <div ref="messagesContainer" class="messages-stream rounded-xl border bg-black/30 backdrop-blur-xl p-3 md:p-4" :class="themeConfig.borderLight">
                <!-- 训练舱待命空态：仅在还没消息时短暂出现，提升"训练舱"叙事 -->
                <div v-if="messages.length === 0 && !isLoading" class="py-8 text-center">
                  <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.03] text-[11px] text-gray-400 font-mono uppercase tracking-wider">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Training Pod · STANDBY
                  </div>
                  <p class="mt-3 text-sm text-gray-300">面试官已就位，请选择难度后进入训练舱。</p>
                </div>

                <div
                  v-for="(msg, index) in messages"
                  :key="index"
                  class="msg-row flex items-start gap-2.5 message-enter"
                  :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
                  data-test="chat-bubble"
                >
                  <!-- 头像（紧凑尺寸，避免大块空白） -->
                  <div class="msg-avatar w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border transition-all duration-300 relative" :class="msg.role === 'user' ? 'bg-white/10 border-white/20' : [themeConfig.bg, themeConfig.border + '/30']">
                    <component :is="msg.role === 'user' ? UserCircle : Cpu" class="w-3.5 h-3.5" :class="msg.role === 'user' ? 'text-gray-300' : themeConfig.text" />
                    <div v-if="msg.role === 'ai' && index === messages.length - 1 && isAiSpeaking" class="absolute -right-1 -top-1 flex items-center gap-0.5">
                      <div class="voice-bar-mini voice-bar-1"></div>
                      <div class="voice-bar-mini voice-bar-2"></div>
                      <div class="voice-bar-mini voice-bar-3"></div>
                    </div>
                  </div>

                  <!-- 消息气泡（紧凑内边距） -->
                  <div
                    class="msg-bubble max-w-[90%] md:max-w-[72%] rounded-2xl px-3.5 py-2 relative overflow-hidden transition-all duration-300"
                    :class="[
                      msg.role === 'user' ? 'bg-white/10 border border-white/20 text-gray-200 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]' : 'bg-white/[0.03] border text-gray-200 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]',
                      msg.role === 'ai' ? themeConfig.borderLight : '',
                      getEmotionClass(msg.content)
                    ]"
                  >
                    <div v-if="msg.role === 'ai'" class="absolute left-0 top-2 bottom-2 w-[2px] rounded-full" :class="themeConfig.bg.replace('/20', '')"></div>

                    <!-- 情绪图标 -->
                    <div v-if="msg.role === 'ai' && getEmotionIcon(msg.content)" class="pl-3 mb-0.5 text-base">{{ getEmotionIcon(msg.content) }}</div>

                    <div v-if="msg.role === 'ai'" class="markdown-body chat-markdown pl-3 inline" :class="{ 'typewriter-effect': msg.isNew }">
                      <span v-html="marked.parse(cleanMessage(msg.content))"></span>
                      <span v-if="index === messages.length - 1 && isAiSpeaking" class="geek-cursor">█</span>
                    </div>
                    <p v-else class="text-sm leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>
                    <p class="text-[10px] text-gray-500 mt-1 text-right" :class="msg.role === 'ai' ? 'pl-3' : ''">{{ msg.timestamp }}</p>
                  </div>
                </div>

                <!-- Loading 动画（收紧高度，避免巨大空白） -->
                <div v-if="isLoading" class="msg-row flex items-start gap-2.5 message-enter" data-test="loading-indicator">
                  <div class="msg-avatar w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border relative" :class="[themeConfig.bg, themeConfig.border + '/30']">
                    <Loader2 class="w-3.5 h-3.5 animate-spin" :class="themeConfig.text" />
                    <div class="absolute -right-1 -top-1 flex items-center gap-0.5">
                      <div class="voice-bar voice-bar-1"></div>
                      <div class="voice-bar voice-bar-2"></div>
                      <div class="voice-bar voice-bar-3"></div>
                      <div class="voice-bar voice-bar-4"></div>
                    </div>
                  </div>
                  <div class="rounded-2xl px-3.5 py-1.5 border backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] inline-flex items-center" :class="['bg-white/[0.03]', themeConfig.borderLight]">
                    <component v-if="StreamingLoaderComp" :is="StreamingLoaderComp" />
                    <div v-else class="flex items-center gap-1.5">
                      <div class="w-1.5 h-1.5 rounded-full animate-bounce" :class="themeConfig.bg.replace('/20', '')" style="animation-delay: 0s;"></div>
                      <div class="w-1.5 h-1.5 rounded-full animate-bounce" :class="themeConfig.bg.replace('/20', '')" style="animation-delay: 0.2s;"></div>
                      <div class="w-1.5 h-1.5 rounded-full animate-bounce" :class="themeConfig.bg.replace('/20', '')" style="animation-delay: 0.4s;"></div>
                    </div>
                  </div>
                </div>

                <!-- 错误透传区（onError 收到的 message 直接渲染，不做包装） -->
                <div v-if="evaluateError" class="msg-row flex items-start gap-2.5 message-enter" data-test="error-display">
                  <div class="msg-avatar w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border bg-amber-500/15 border-amber-500/40">
                    <AlertTriangle class="w-3.5 h-3.5 text-amber-400" />
                  </div>
                  <div class="rounded-2xl px-3.5 py-2 border border-amber-500/30 bg-amber-500/5 text-sm text-amber-200 leading-relaxed">{{ evaluateError }}</div>
                </div>
              </div>

              <!-- ActionDock：Send 主操作 + End / Retry 次操作 -->
              <ActionDock align="right">
                <template #secondary>
                  <button
                    v-if="evaluateError"
                    @click="retryEvaluate"
                    class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 hover:border-amber-500/50"
                    data-test="retry-button"
                  >
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                    重新评估
                  </button>

                  <button
                    v-else-if="!isEvaluationDone"
                    @click="endInterview"
                    :disabled="isLoading || messages.filter(m => m.role === 'user').length < 1"
                    :title="messages.filter(m => m.role === 'user').length < 1 ? '至少完成一轮回答后才能结束面试并生成复盘' : '结束面试并生成复盘'"
                    class="px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 disabled:bg-none disabled:bg-gray-600/30 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed bg-gradient-to-r from-red-500 to-orange-500 text-white shadow-lg shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/50 hover:scale-[1.02] active:scale-[0.98]"
                    data-test="end-interview-button"
                  >
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    <span>结束面试</span>
                  </button>

                  <button
                    v-if="isEvaluationDone"
                    @click="showResultModal = true"
                    class="px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50"
                    data-test="replay-button"
                  >
                    查看复盘报告
                  </button>
                </template>

                <template #primary>
                  <button
                    @click="sendMessage"
                    :disabled="isLoading || !userInput.trim() || strikeTerminated || isInterviewEnded"
                    class="send-btn px-5 py-2.5 md:px-6 md:py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] disabled:bg-none disabled:bg-gray-600/30 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2 overflow-hidden relative text-white"
                    :class="['bg-gradient-to-r', themeConfig.gradient, themeConfig.shadow, 'hover:shadow-xl']"
                    data-test="send-button"
                  >
                    <span class="send-btn-shimmer"></span>
                    <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin relative z-10" />
                    <Send v-else class="w-4 h-4 relative z-10" />
                    <span class="relative z-10">{{ isLoading ? '生成追问中...' : '发送' }}</span>
                  </button>
                </template>
              </ActionDock>
            </div>
          </div>
        </template>
      </FeaturePageShell>
    </div>
    <!-- 难度选择 Modal -->
    <Teleport to="body">
      <transition name="result-pop">
        <div v-if="showDifficultyModal" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-xl flex items-center justify-center p-4">
          <div class="bg-gradient-to-br from-[#151520] to-[#0f0f1a] border rounded-3xl p-6 md:p-8 max-w-md w-full shadow-2xl" :class="themeConfig.border + '/30', themeConfig.shadow">
            <h2 class="text-2xl font-bold text-white mb-2 text-center">选择面试难度</h2>
            <p class="text-sm text-gray-500 mb-6 text-center">不同难度将影响面试官的提问风格和追问深度</p>

            <div class="space-y-3">
              <button
                @click="interviewDifficulty = 'beginner'"
                class="w-full p-4 rounded-xl border-2 transition-all duration-300 flex items-start gap-3 text-left"
                :class="interviewDifficulty === 'beginner' ? 'border-green-500 bg-green-500/10 shadow-lg shadow-green-500/10' : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'"
              >
                <div class="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span class="text-green-400 font-bold text-lg">🌱</span>
                </div>
                <div>
                  <h3 class="text-base font-semibold text-white mb-1">温和鼓励</h3>
                  <p class="text-xs text-gray-400 leading-relaxed">适合应届生 / 新人。基础概念为主，提供提示和鼓励，像学长学姐帮忙模拟</p>
                </div>
              </button>

              <button
                @click="interviewDifficulty = 'standard'"
                class="w-full p-4 rounded-xl border-2 transition-all duration-300 flex items-start gap-3 text-left"
                :class="interviewDifficulty === 'standard' ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/10' : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'"
              >
                <div class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span class="text-blue-400 font-bold text-lg">💼</span>
                </div>
                <div>
                  <h3 class="text-base font-semibold text-white mb-1">标准专业</h3>
                  <p class="text-xs text-gray-400 leading-relaxed">适合有经验开发者。注重实用性和逻辑性，适度追问，像真正的技术面试</p>
                </div>
              </button>

              <button
                @click="interviewDifficulty = 'p8'"
                class="w-full p-4 rounded-xl border-2 transition-all duration-300 flex items-start gap-3 text-left"
                :class="interviewDifficulty === 'p8' ? 'border-purple-500 bg-purple-500/10 shadow-lg shadow-purple-500/10' : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'"
              >
                <div class="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span class="text-purple-400 font-bold text-lg">🔥</span>
                </div>
                <div>
                  <h3 class="text-base font-semibold text-white mb-1">P8 压力面试</h3>
                  <p class="text-xs text-gray-400 leading-relaxed">适合高级开发者。高难度问题 + 压力测试，犀利追问，P8 大佬审视体验</p>
                </div>
              </button>
            </div>

            <div class="mt-6">
              <button
                @click="startInterviewWithDifficulty"
                class="w-full py-3.5 rounded-xl text-base font-semibold text-white shadow-lg hover:scale-[1.02] transition-all duration-300"
                :class="['bg-gradient-to-r', themeConfig.gradient, themeConfig.shadow, 'hover:shadow-xl']"
              >
                开始面试
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 黑客帝国 Matrix Modal -->
    <Teleport to="body">
      <transition name="matrix-fade">
        <div v-if="showMatrixModal" class="fixed inset-0 z-[9999] bg-black flex items-center justify-center">
          <div class="matrix-container w-full max-w-2xl p-8">
            <div class="text-center mb-6">
              <h2 class="text-green-500 font-mono text-xl mb-2 animate-pulse">NEURAL EVALUATION IN PROGRESS</h2>
              <p class="text-green-700 text-sm font-mono">Analyzing response patterns...</p>
            </div>
            <div class="matrix-lines font-mono text-xs text-green-500 leading-relaxed h-[300px] overflow-hidden">
              <div v-for="(line, i) in matrixLines" :key="i" class="matrix-line opacity-0" :style="{ animationDelay: `${i * 50}ms` }">{{ line }}</div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 评估结果 / 复盘 Modal（基于 BaseModal 扩展，复用既有 CyberRadarChart） -->
    <BaseModal
      :model-value="showResultModal"
      max-width="max-w-lg"
      @update:model-value="(v) => { if (!v) closeResultModal() }"
      @close="closeResultModal"
    >
      <div class="result-modal p-6 md:p-8 relative overflow-hidden" :class="themeConfig.shadow">
        <!-- 标题 -->
        <div class="text-center mb-6">
          <h2 class="text-2xl font-bold mb-2" :class="themeConfig.text">能力评估报告</h2>
          <p class="text-gray-500 text-sm">AI 面试官已生成您的专属评估</p>
        </div>

        <!-- 雷达图：复用既有 CyberRadarChart.vue，不修改该文件 -->
        <div
          class="rounded-xl border backdrop-blur-xl p-4 mb-6 relative overflow-hidden"
          :class="[themeConfig.borderLight, 'bg-white/[0.02]']"
          data-test="replay-radar-container"
        >
          <CyberRadarChart :chart-data="radarChartData" />
        </div>

        <!-- 分数展示 -->
        <div class="grid grid-cols-6 gap-1 mb-6">
          <div v-for="(label, i) in ['专业技能', '逻辑分析', '沟通表达', '问题解决', '综合潜力', '抗压韧性']" :key="i" class="text-center">
            <div class="text-base font-bold" :class="themeConfig.text">{{ radarScores[RADAR_LABELS[i]] }}</div>
            <div class="text-[9px] text-gray-500">{{ label }}</div>
          </div>
        </div>

        <!-- 导师结语 -->
        <div class="rounded-xl p-4 mb-6" :class="[themeConfig.bg.replace('/20', '/10'), themeConfig.borderLight]">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-lg">👑</span>
            <span class="text-sm font-semibold" :class="themeConfig.text">导师结语</span>
          </div>
          <p class="text-sm text-gray-300 leading-relaxed">{{ mentorComment }}</p>
        </div>

        <!-- 操作按钮 -->
        <div class="flex gap-3">
          <button @click="closeResultModal" class="flex-1 py-3 rounded-xl text-sm font-medium border border-white/10 text-gray-400 hover:bg-white/5 transition-all">
            关闭
          </button>
          <button @click="goToCareerPlanning" class="flex-1 py-3 rounded-xl text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/30 hover:shadow-xl transition-all">
            生成职业规划
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.grid-bg { background-image: linear-gradient(rgba(236, 72, 153, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(236, 72, 153, 0.06) 1px, transparent 1px); background-size: 40px 40px; }

/* CRT 扫描线 - 降频优化：移除高频闪烁动画 + GPU加速 + 防遮挡 */
.crt-overlay {
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255, 255, 255, 0.02) 2px, rgba(255, 255, 255, 0.02) 4px);
  pointer-events: none;
  transform: translateZ(0);
  will-change: transform, opacity;
}

/* 专注模式脉冲光晕 - GPU 加速优化 */
.focus-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  animation: focusPulse 3s ease-in-out infinite;
  will-change: transform, opacity;
  transform: translateZ(0);
}
.focus-glow-1 { width: 250px; height: 250px; background: radial-gradient(circle, rgba(217, 70, 239, 0.25) 0%, transparent 70%); top: 10%; right: 5%; animation-delay: 0s; }
.focus-glow-2 { width: 300px; height: 300px; background: radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%); bottom: 20%; right: 15%; animation-delay: 0.5s; }
.focus-glow-3 { width: 200px; height: 200px; background: radial-gradient(circle, rgba(236, 72, 153, 0.18) 0%, transparent 70%); top: 50%; right: 30%; animation-delay: 1s; }
@keyframes focusPulse { 0%, 100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 0.7; transform: scale(1.08); } }

/* 声纹波动动画 */
.voice-bar { width: 2px; background: linear-gradient(to top, #e879f9, #f472b6); border-radius: 1px; animation: voiceWave 0.5s ease-in-out infinite; }
.voice-bar-1 { height: 8px; animation-delay: 0s; }
.voice-bar-2 { height: 12px; animation-delay: 0.1s; }
.voice-bar-3 { height: 6px; animation-delay: 0.2s; }
.voice-bar-4 { height: 10px; animation-delay: 0.3s; }
.voice-bar-mini { width: 1.5px; background: linear-gradient(to top, #e879f9, #f472b6); border-radius: 1px; animation: voiceWave 0.5s ease-in-out infinite; }
@keyframes voiceWave { 0%, 100% { transform: scaleY(0.5); opacity: 0.6; } 50% { transform: scaleY(1); opacity: 1; } }

/* 声呐扫描动画 - GPU 加速优化 */
.radar-container { position: relative; }
.radar-polygon { transition: all 0.5s ease-in-out; }
.sonar-sweep {
  position: absolute;
  inset: 16px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, transparent 0deg, transparent 300deg, rgba(232, 121, 249, 0.25) 330deg, rgba(232, 121, 249, 0.4) 345deg, rgba(232, 121, 249, 0.1) 360deg);
  animation: sonarRotate 4s linear infinite;
  pointer-events: none;
  will-change: transform;
  transform: translateZ(0);
}
.sonar-sweep-delay {
  animation-delay: -2s;
  opacity: 0.5;
  background: conic-gradient(from 180deg, transparent 0deg, transparent 300deg, rgba(232, 121, 249, 0.15) 330deg, rgba(232, 121, 249, 0.25) 345deg, rgba(232, 121, 249, 0.05) 360deg);
  will-change: transform;
  transform: translateZ(0);
}
@keyframes sonarRotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.radar-polygon { transition: all 1s cubic-bezier(0.16, 1, 0.3, 1); }
.radar-dot { animation: radarDotPulse 2s ease-in-out infinite; }
@keyframes radarDotPulse { 0%, 100% { opacity: 0.6; r: 2; } 50% { opacity: 1; r: 3; } }

/* 消息入场动画 */
.message-enter { animation: messageSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes messageSlideIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

/* 打字机效果 */
.typewriter-effect { animation: typewriterFade 0.3s ease-out; }
@keyframes typewriterFade { from { opacity: 0; filter: blur(4px); } to { opacity: 1; filter: blur(0); } }

/* 情绪样式 */
.emotion-approve { border-left: 3px solid #22c55e !important; }
.emotion-think { border-left: 3px solid #eab308 !important; }
.emotion-frown { border-left: 3px solid #f97316 !important; }
.emotion-doubt { border-left: 3px solid #ef4444 !important; }

/* 环境光情绪映射 */
.ambient-negative { box-shadow: inset 0 0 120px 40px rgba(239, 68, 68, 0.08), inset 0 0 60px 20px rgba(239, 68, 68, 0.05); }
.ambient-positive { box-shadow: inset 0 0 120px 40px rgba(6, 182, 212, 0.08), inset 0 0 60px 20px rgba(6, 182, 212, 0.05); }
.ambient-neutral { box-shadow: inset 0 0 120px 40px rgba(168, 85, 247, 0.06), inset 0 0 60px 20px rgba(236, 72, 153, 0.04); }

/* 极客光标闪烁 */
.geek-cursor {
  display: inline;
  color: #e879f9;
  font-weight: bold;
  animation: geekCursorBlink 0.5s step-end infinite;
  text-shadow: 0 0 8px rgba(232, 121, 249, 0.6);
}
@keyframes geekCursorBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* 发送按钮流光效果 */
.send-btn { position: relative; overflow: hidden; }
.send-btn-shimmer { position: absolute; inset: 0; background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.15) 40%, rgba(255, 255, 255, 0.3) 50%, rgba(255, 255, 255, 0.15) 60%, transparent 100%); animation: shimmer 3s infinite; width: 200%; top: 0; left: -100%; pointer-events: none; }
@keyframes shimmer { 0% { transform: translateX(0); } 100% { transform: translateX(100%); } }

/* 幽灵按钮 */
.ghost-btn { position: relative; overflow: hidden; background: transparent; border: 1px solid rgba(232, 121, 249, 0.25); color: rgba(232, 121, 249, 0.7); }
.ghost-btn:hover:not(:disabled) { border-color: rgba(232, 121, 249, 0.6); color: rgba(232, 121, 249, 1); box-shadow: 0 0 20px rgba(232, 121, 249, 0.2), inset 0 0 20px rgba(232, 121, 249, 0.05); }
.ghost-btn:active:not(:disabled) { transform: scale(0.98); }

/* 滚动条 */
.overflow-y-auto::-webkit-scrollbar, textarea::-webkit-scrollbar { width: 6px; }
.overflow-y-auto::-webkit-scrollbar-track, textarea::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); border-radius: 3px; }
.overflow-y-auto::-webkit-scrollbar-thumb, textarea::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
.overflow-y-auto::-webkit-scrollbar-thumb:hover, textarea::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }

/* Markdown 样式 */
.markdown-body.chat-markdown { font-size: 14px; line-height: 1.7; word-wrap: break-word; color: rgba(252, 231, 243, 0.9); }
.markdown-body.chat-markdown :deep(h1) { font-size: 1.3em; font-weight: 700; margin: 0.6em 0 0.3em; padding-bottom: 0.2em; background: linear-gradient(135deg, #f472b6, #c084fc); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; border-bottom: 1px solid rgba(236, 72, 153, 0.15); }
.markdown-body.chat-markdown :deep(h2) { font-size: 1.15em; font-weight: 600; margin: 0.5em 0 0.25em; background: linear-gradient(135deg, #ec4899, #a855f7); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.markdown-body.chat-markdown :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 0.4em 0 0.2em; background: linear-gradient(135deg, #f472b6, #d946ef); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.markdown-body.chat-markdown :deep(strong), .markdown-body.chat-markdown :deep(b) { color: #f472b6; font-weight: 700; }
.markdown-body.chat-markdown :deep(p) { margin: 0.3em 0; color: rgba(252, 231, 243, 0.85); }
.markdown-body.chat-markdown :deep(ul), .markdown-body.chat-markdown :deep(ol) { padding-left: 1.3em; margin: 0.3em 0; }
.markdown-body.chat-markdown :deep(li) { margin: 0.15em 0; color: rgba(252, 231, 243, 0.8); }
.markdown-body.chat-markdown :deep(li)::marker { color: #ec4899; text-shadow: 0 0 6px rgba(236, 72, 153, 0.5); }
.markdown-body.chat-markdown :deep(blockquote) { border-left: 3px solid rgba(236, 72, 153, 0.35); padding: 0.3em 0.8em; margin: 0.4em 0; background: rgba(236, 72, 153, 0.04); border-radius: 0 6px 6px 0; color: rgba(252, 231, 243, 0.7); }
.markdown-body.chat-markdown :deep(code) { background: rgba(236, 72, 153, 0.1); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.88em; color: #f9a8d4; font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.markdown-body.chat-markdown :deep(pre) { background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(236, 72, 153, 0.12); border-radius: 8px; padding: 0.8em; overflow-x: auto; margin: 0.4em 0; }
.markdown-body.chat-markdown :deep(pre code) { background: none; padding: 0; border-radius: 0; color: rgba(252, 231, 243, 0.85); }

/* Matrix Modal 动画 */
.matrix-fade-enter-active { animation: matrixFadeIn 0.5s ease-out; }
.matrix-fade-leave-active { animation: matrixFadeOut 0.3s ease-in; }
@keyframes matrixFadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes matrixFadeOut { from { opacity: 1; } to { opacity: 0; } }

.matrix-line { animation: matrixLineAppear 0.1s ease-out forwards; }
@keyframes matrixLineAppear { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

/* Result Modal 动画 */
.result-pop-enter-active { animation: resultPopIn 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.result-pop-leave-active { animation: resultPopOut 0.3s ease-in; }
@keyframes resultPopIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
@keyframes resultPopOut { from { opacity: 1; transform: scale(1); } to { opacity: 0; transform: scale(0.9); } }

/* 赛博扫描线动画 */
@keyframes scanline {
  0% { transform: translateY(-100%); opacity: 0; }
  50% { opacity: 0.5; }
  100% { transform: translateY(100%); opacity: 0; }
}
.animate-scan {
  position: relative;
  overflow: hidden;
}
.animate-scan::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(to right, transparent, currentColor, transparent);
  animation: scanline 3s linear infinite;
  pointer-events: none;
}

/* ── 训练舱仪表盘 metrics-rail ────────────────────────────── */
.metrics-rail {
  position: relative;
  border-radius: 12px;
  padding: 8px 10px 10px;
  background: linear-gradient(180deg, rgba(255,255,255,0.018), rgba(255,255,255,0));
  border: 1px solid rgba(255,255,255,0.05);
}
.metrics-rail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px 8px;
  border-bottom: 1px dashed rgba(255,255,255,0.06);
  margin-bottom: 8px;
}
.metrics-rail__dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34,211,238,0.65);
  animation: metrics-rail-pulse 2.4s ease-in-out infinite;
}
@keyframes metrics-rail-pulse {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50%      { opacity: 1;    transform: scale(1.18); }
}
@media (prefers-reduced-motion: reduce) {
  .metrics-rail__dot { animation: none; }
}

/* 移动端响应式：隐藏左侧面板，仅显示对话区 */
@media (max-width: 767px) {
  .left-panel {
    display: none;
  }
}

/* ── 难度选择「模式切换」当前选中态强化 ────────────────── */
.difficulty-btn {
  position: relative;
  transition: transform 0.18s ease-out, border-color 0.2s, background-color 0.2s, box-shadow 0.2s, color 0.2s;
}
.difficulty-btn:not(:disabled):hover {
  transform: translateY(-1px);
}
.difficulty-btn:not(:disabled):active {
  transform: translateY(0) scale(0.98);
}
.difficulty-btn--selected::after {
  /* 选中态左侧短色条：让 "当前模式" 一眼可识别 */
  content: '';
  position: absolute;
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: currentColor;
  opacity: 0.8;
}

/* ── 面试官身份卡：与 MetricCard 保持视觉差异 ────────────── */
.interviewer-header {
  position: relative;
  background-image:
    linear-gradient(135deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)),
    radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.06), transparent 60%);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.04);
}
.interviewer-header::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.45), transparent);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  pointer-events: none;
}

/* ── 对话流：独立滚动容器 ─────────────────────────────────
   1080p 同屏目标：消息流约占 38–44vh，输入框、发送、结束按钮同屏可见。
   - 容器自身设定 max-height，超出时只在容器内滚动；
   - overscroll-behavior: contain 阻止滚轮冒泡到外层页面；
   - 行间距压缩约 25%（原 space-y-4 → 0.625rem）。
*/
.messages-stream {
  /* 紧凑滚动容器：bounded height + 内部独立滚动 */
  max-height: clamp(260px, 42vh, 460px);
  min-height: 220px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}
/* 用 CSS 间距替代 Tailwind 的 space-y-4，降低 25%~30% */
.messages-stream > .msg-row + .msg-row,
.messages-stream > * + .msg-row,
.messages-stream > .msg-row + * {
  margin-top: 0.625rem;
}

/* 消息气泡：行高与段落 margin 一并收紧，避免纵向占用过大 */
.msg-bubble {
  line-height: 1.55;
}
.msg-bubble :deep(p) {
  margin: 0.2em 0;
}
.msg-bubble :deep(ul),
.msg-bubble :deep(ol) {
  margin: 0.25em 0;
}

/* AI 头像缩小后的居中保护，避免与首段文字基线错位 */
.msg-avatar {
  margin-top: 2px;
}

/* 输入框：保持单屏布局优先，软上限避免被用户拖得过高 */
.interview-textarea {
  min-height: 84px;
  max-height: 160px;
}
</style>
