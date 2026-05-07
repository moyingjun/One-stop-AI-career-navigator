<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { llmService } from '@/services/llm_service.js'
import { useRouter } from 'vue-router'
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import QrcodeVue from 'qrcode.vue'
import { parseFile } from '@/utils/ocrHelper.js'
import { marked } from 'marked'

import { Bot, FileText, MessageSquare, Folder, Settings, Clock, Puzzle, Plus, Search, Paperclip, MoreHorizontal, ChevronDown, ChevronRight, Upload, CheckCircle, X, Loader2, History, Send, Sparkles, Mic }
  from 'lucide-vue-next'

const router = useRouter()

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const historyRecords = ref([])

const loadHistory = async () => {
  try {
    const res = await fetch(`${API_BASE_URL.replace('/api', '')}/api/history?limit=2`)
    if (res.ok) {
      const data = await res.json()
      historyRecords.value = data.records || []
    }
  } catch {}
}

const getCategoryLabel = (cat) => {
  if (cat === 'resume_diagnosis') return '简历诊断'
  if (cat === 'interview_beginner') return '温和面试'
  if (cat === 'interview_standard') return '标准面试'
  if (cat === 'interview_p8') return 'P8压力面'
  if (cat.startsWith('interview')) return '面试评估'
  if (cat === 'career_planning') return '职业规划'
  if (cat === 'general_chat') return '职业助手'
  return cat
}

const getCategoryColor = (cat) => {
  if (cat === 'resume_diagnosis') return 'text-purple-400 border-purple-500/30 bg-purple-500/5'
  if (cat === 'interview_beginner') return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5'
  if (cat === 'interview_standard') return 'text-blue-400 border-blue-500/30 bg-blue-500/5'
  if (cat === 'interview_p8') return 'text-pink-400 border-pink-500/30 bg-pink-500/5'
  if (cat.startsWith('interview')) return 'text-pink-400 border-pink-500/30 bg-pink-500/5'
  if (cat === 'career_planning') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5'
  if (cat === 'general_chat') return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5'
  return 'text-gray-400 border-gray-500/30 bg-gray-500/5'
}

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

const goToHistory = (record) => {
  if (record.category === 'resume_diagnosis') router.push(`/resume-diagnosis?id=${record.id}`)
  else if (record.category === 'interview_evaluate') router.push(`/interview?id=${record.id}`)
  else if (record.category === 'career_planning') router.push(`/career-planning?id=${record.id}`)
}

// 本地存储用户名
const userName = ref(localStorage.getItem('candidate_name') || '')

// 全局简历状态
const globalResumeStatus = ref(localStorage.getItem('resume_text') ? 'ready' : 'missing')
const showResumeDialog = ref(false)
const pendingResumeText = ref('')
const pendingFileName = ref('')
const isGlobalDragging = ref(false)

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

// 全局简历拖拽处理
const handleGlobalFileDrop = (event) => {
  event.preventDefault()
  isGlobalDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processGlobalResume(files[0])
}

const handleGlobalFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) processGlobalResume(files[0])
}

const processGlobalResume = async (file) => {
  try {
    const text = await parseFile(file)
    if (!text.trim()) {
      alert('文件内容为空，请检查后重试')
      return
    }
    pendingFileName.value = file.name
    pendingResumeText.value = text
    showResumeDialog.value = true
  } catch (e) {
    alert(e.message || '文件解析失败，请重试')
  }
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

// 监听其他页面更新简历
const handleStorageChange = (e) => {
  if (e.key === 'resume_text') {
    globalResumeStatus.value = e.newValue ? 'ready' : 'missing'
  }
}

// 面试舱门逻辑
const openInterviewModal = () => {
  if (globalResumeStatus.value === 'missing') {
    alert('请先在【全局信息录入】或侧边栏上传您的简历')
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
    alert('请先粘贴岗位描述 (JD)')
    return
  }
  localStorage.setItem('current_interview_jd', interviewJd.value.trim())
  showInterviewModal.value = false
  interviewPaymentDone.value = false
  isInterviewUnlocking.value = false
  router.push('/interview')
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
      { icon: 'message-square', label: '保存的对话' },
      { icon: 'folder', label: '文件管理' },
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

const chatMessages = ref([])
const userChatInput = ref('')
const isChatLoading = ref(false)
const uploadedGlobalResume = ref('')
const chatContainerRef = ref(null)

const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

const sendGeneralChatMessage = async () => {
  if (!userChatInput.value.trim() || isChatLoading.value) return

  const userMessage = userChatInput.value.trim()
  chatMessages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  userChatInput.value = ''
  isChatLoading.value = true
  scrollChatToBottom()

  try {
    const response = await fetch(`${API_BASE_URL}/chat/general`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: userMessage,
        resume_text: uploadedGlobalResume.value || localStorage.getItem('resume_text') || ''
      })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    chatMessages.value.push({
      role: 'ai',
      content: data.reply || '抱歉，我没理解你的问题',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      isNew: true
    })
  } catch (error) {
    console.error('发送聊天消息失败:', error)
    chatMessages.value.push({
      role: 'ai',
      content: '😵 职业助手正在开小差，请重新提问哦~',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
  } finally {
    isChatLoading.value = false
    scrollChatToBottom()
  }
}

const handleChatFileUpload = async (event) => {
  const files = event.target.files
  if (files.length > 0) {
    try {
      const text = await parseFile(files[0])
      if (text.trim()) {
        uploadedGlobalResume.value = text
      }
    } catch (e) {
      alert(e.message || '文件解析失败')
    } finally {
      event.target.value = ''
    }
  }
}

const removeUploadedResume = () => {
  uploadedGlobalResume.value = ''
}

const handleChatEnter = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendGeneralChatMessage()
  }
}

const chatPlaceholder = computed(() => {
  if (uploadedGlobalResume.value) return '请输入关于此文件的问题...'
  return placeholderText.value || '向 AI 职场领航员提问...'
})

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

// 生命周期
onMounted(() => {
  typeWriter()
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('storage', handleStorageChange)
  playConsoleAnimation()
  loadHistory()
})

onUnmounted(() => {
  if (placeholderTimer) {
    clearTimeout(placeholderTimer)
  }
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('storage', handleStorageChange)
})
</script>

<template>
  <div class="app-container relative min-h-screen w-full text-gray-300 overflow-hidden">
    <!-- 背景光影效果 -->
    <div class="absolute top-0 left-0 w-full h-full bg-[#050505] z-0 pointer-events-none">
      <!-- 左上角紫色光晕 -->
      <div class="absolute top-0 left-0 w-[50vw] h-[50vh] bg-gradient-to-br from-purple-600/10 via-pink-500/5 to-transparent blur-3xl animate-pulse-slow"></div>
      <!-- 右下角蓝色光晕 -->
      <div class="absolute bottom-0 right-0 w-[50vw] h-[50vh] bg-gradient-to-tl from-cyan-500/10 via-blue-500/5 to-transparent blur-3xl animate-pulse-slower"></div>
    </div>

    <div class="relative z-10 flex flex-col md:flex-row h-[100dvh] w-full overflow-x-hidden">
      <!-- 左侧侧边栏 -->
      <div class="left-sidebar hidden md:flex w-64 fixed h-full z-20">
        <div class="bg-white/5 backdrop-blur-xl border-r border-white/10 rounded-3xl m-4 h-[calc(100vh-2rem)] shadow-xl shadow-purple-500/5 flex flex-col overflow-y-auto">
          <div class="logo p-3 border-b border-white/10 pl-4 cursor-pointer" @click="router.push('/')">
            <div class="flex items-center gap-3 text-left">
              <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/20">
                <span class="text-white text-sm font-bold">AI</span>
              </div>
              <div class="flex flex-col">
                <h1 class="text-xl font-bold text-white leading-tight">AI 职业导航</h1>
                <p class="text-xs text-gray-500 leading-tight mt-0.5">智能助手</p>
              </div>
            </div>
          </div>

          <div class="new-chat p-4">
            <button class="w-full bg-white/10 hover:bg-white/15 hover:shadow-lg hover:shadow-purple-500/20 text-white py-2 px-4 rounded-full transition-all duration-300 flex items-center gap-2 border border-white/10 hover:border-purple-500/50 hover:-translate-y-0.5 group">
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
                  :class="{ 'bg-white/10 text-white': item.label === activeMenu }"
                  @click="item.label === '历史记录' ? router.push('/history-archive') : (activeMenu = item.label)"
                >
                  <component :is="iconMap[item.icon]" class="w-5 h-5 text-gray-400 group-hover:text-purple-400 transition-colors duration-300" />
                  <span class="text-sm">{{ item.label }}</span>
                </div>
              </div>
            </div>

            <div v-if="chatMessages.length > 0" class="history mt-8">
              <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
                最近
              </h2>
              <div class="space-y-1">
                <div
                  v-for="(message, index) in chatMessages"
                  :key="index"
                  class="history-item p-2 rounded-lg hover:bg-white/10 transition-all duration-300 cursor-pointer hover:translate-x-2"
                >
                  <p class="text-sm truncate text-left">AI分析 - {{ new Date().toLocaleDateString() }}</p>
                </div>
              </div>
            </div>

            <div class="add-topic mt-8">
              <button class="w-full flex items-center gap-2 text-gray-500 hover:text-white transition-colors duration-300 hover:translate-x-2">
                <Plus class="w-5 h-5" />
                <span class="text-sm">添加主题</span>
              </button>
            </div>

            <!-- 全局简历状态卡片 -->
            <div class="mt-6">
              <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">
                全局资产
              </h2>
              <div
                class="p-3 rounded-xl border transition-all duration-300 cursor-pointer hover:-translate-y-0.5 hover:shadow-lg group/asset"
                :class="globalResumeStatus === 'ready'
                  ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/40 hover:shadow-green-500/10'
                  : 'bg-red-500/5 border-red-500/20 hover:border-red-500/40 hover:shadow-red-500/10'"
                @click="$refs.globalFileInput?.click()"
                @dragover.prevent="isGlobalDragging = true"
                @dragleave.prevent="isGlobalDragging = false"
                @drop.prevent="handleGlobalFileDrop"
              >
                <div class="flex items-center gap-2 mb-1">
                  <div class="w-2 h-2 rounded-full transition-all duration-300"
                    :class="globalResumeStatus === 'ready'
                      ? 'bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]'
                      : 'bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]'"></div>
                  <span class="text-xs font-medium transition-colors duration-300"
                    :class="globalResumeStatus === 'ready' ? 'text-green-400' : 'text-red-400'">
                    {{ globalResumeStatus === 'ready' ? '全局简历：已就绪' : '简历缺失' }}
                  </span>
                </div>
                <p class="text-[10px] text-gray-600 group-hover/asset:text-gray-400 transition-colors duration-300">
                  {{ globalResumeStatus === 'ready' ? '拖入新文件可更新' : '点击上传简历' }}
                </p>
              </div>

              <!-- 隐藏的全局文件输入 -->
              <input
                ref="globalFileInput"
                type="file"
                class="hidden"
                accept=".txt,.pdf,.docx"
                @change="handleGlobalFileSelect"
              />
            </div>

            <!-- 侧边栏底部署名 -->
            <div class="mt-auto pt-4 border-t border-white/5 pl-2 group/credit">
              <p class="text-xs text-gray-400 font-medium cursor-pointer relative">
                Moyingjun
                <span class="absolute left-0 bottom-full mb-2 px-2 py-1 bg-gray-800/90 backdrop-blur-sm text-[10px] text-gray-300 rounded-md opacity-0 group-hover/credit:opacity-100 transition-opacity duration-300 whitespace-nowrap pointer-events-none border border-white/10 shadow-lg">
                  嘘...按 F12 看看？
                </span>
              </p>
              <p class="text-[10px] text-gray-600 mt-0.5">广东水利电力职业技术学院</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧主工作区 -->
      <div class="right-workspace ml-0 md:ml-64 flex-1 flex flex-col relative h-[100dvh]">
        <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl m-4 flex-1 shadow-xl shadow-purple-500/5 overflow-hidden flex flex-col relative">
          <div class="top-bar p-4 border-b border-white/10 flex items-center justify-between animate-[fadeIn_0.3s_ease-out]">
            <div class="search-container flex items-center gap-2">
              <div class="relative">
                <input
                  type="text"
                  placeholder="搜索..."
                  class="bg-white/10 border border-white/10 rounded-lg py-2 px-4 pl-10 text-base w-full md:w-64 focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                />
                <Search class="absolute left-3 top-2.5 text-gray-500 w-4 h-4" />
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-full px-3 py-1.5 flex items-center gap-2">
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></div>
                <span class="text-xs text-green-400 font-mono">DeepSeek-V3 Active</span>
              </div>
              <button class="bg-white/10 border border-white/10 rounded-lg py-2 px-4 text-sm hover:bg-white/15 hover:border-purple-500/50 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/20">
                邀请
              </button>
            </div>
          </div>

          <div class="main-content flex-1 overflow-y-auto relative flex flex-col pb-40">
            <!-- 鼠标跟随环境光 -->
            <div 
              class="absolute w-[600px] h-[600px] bg-purple-600/15 rounded-full blur-[150px] pointer-events-none z-0 transition-all duration-700 ease-out"
              :style="{ left: `calc(${mouseX}% - 300px)`, top: `calc(${mouseY}% - 300px)` }"
            ></div>
            <div class="absolute bottom-20 right-10 w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[150px] pointer-events-none z-0"></div>
            
            <div class="max-w-5xl mx-auto w-full flex-1 flex flex-col justify-center pb-24 relative z-10">
              <div class="welcome-section mb-6 text-left animate-fade-in-up animation-delay-0">
                <h1 class="text-3xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-gray-200 mb-1 tracking-tighter">{{ greeting }}，{{ userName || '新' }}同学</h1>
                <p class="text-lg md:text-2xl text-purple-200/60 mt-2">今天想探索些什么？</p>
              </div>

              <div class="workspaces mb-8 text-left animate-fade-in-up animation-delay-100">
                <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold pl-1">工作区</h2>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="(workspace, index) in workspaces"
                    :key="workspace"
                    class="px-4 py-1.5 rounded-full text-sm font-medium border transition-all duration-300"
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

              <div class="templates-section mb-8 animate-fade-in-up animation-delay-200">
                <div class="mb-4 flex items-center justify-between">
                  <h2 class="text-lg font-semibold text-gray-200 text-left">核心功能</h2>
                  <div class="flex items-center gap-2">
                    <button class="text-gray-400 hover:text-white hover:scale-110 transition-all duration-300">
                      <Plus class="w-4 h-4" />
                    </button>
                    <button class="text-gray-400 hover:text-white hover:scale-110 transition-all duration-300">
                      <MoreHorizontal class="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
                  <div class="card relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-3xl p-4 md:p-6 cursor-pointer transition-all duration-500 group hover:-translate-y-2 hover:border-purple-500/50 hover:shadow-[0_0_40px_rgba(168,85,247,0.15)] text-left flex flex-col items-start animate-fade-in-up animation-delay-300"
                    @click="router.push('/resume-diagnosis')">
                    <div class="w-14 h-14 flex items-center justify-center bg-purple-500/10 rounded-xl mb-4">
                      <FileText class="w-7 h-7 text-purple-400" />
                    </div>
                    <h3 class="text-xl md:text-2xl font-black tracking-tight mb-2 text-left">简历诊断</h3>
                    <p class="text-base text-gray-400 text-left leading-relaxed">分析简历优缺点，提供优化建议</p>
                  </div>

                  <div class="card relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-3xl p-4 md:p-6 cursor-pointer transition-all duration-500 group hover:-translate-y-2 hover:border-pink-500/50 hover:shadow-[0_0_40px_rgba(236,72,153,0.15)] hover:scale-[1.02] text-left flex flex-col items-start animate-fade-in-up animation-delay-400"
                    @click="openInterviewModal">
                    <div class="w-14 h-14 flex items-center justify-center bg-pink-500/10 rounded-xl mb-4">
                      <Mic class="w-7 h-7 text-pink-400" />
                    </div>
                    <h3 class="text-xl md:text-2xl font-black tracking-tight mb-2 text-left">模拟面试</h3>
                    <p class="text-base text-gray-400 text-left leading-relaxed">AI 模拟面试，提供反馈和建议</p>
                  </div>

                  <div 
                    @click="router.push('/career-planning')" 
                    class="card relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-3xl p-4 md:p-6 cursor-pointer transition-all duration-500 group hover:-translate-y-2 hover:border-cyan-500/50 hover:shadow-[0_0_40px_rgba(6,182,212,0.15)] text-left flex flex-col items-start animate-fade-in-up animation-delay-500">
                    <div class="w-14 h-14 flex items-center justify-center bg-cyan-500/10 rounded-xl mb-4">
                      <MessageSquare class="w-7 h-7 text-cyan-400" />
                    </div>
                    <h3 class="text-xl md:text-2xl font-black tracking-tight mb-2 text-left">职业规划</h3>
                    <p class="text-base text-gray-400 text-left leading-relaxed">基于你的背景，制定职业发展路径</p>
                  </div>
                </div></div>

              <!-- 历史记录区域 -->
              <div v-if="historyRecords.length > 0" class="mb-8 animate-fade-in-up animation-delay-500">
                <div class="mb-4 flex items-center justify-between">
                  <h2 class="text-lg font-semibold text-gray-200 text-left flex items-center gap-2">
                    <History class="w-5 h-5 text-purple-400" />
                    历史记录
                  </h2>
                  <button
                    @click="router.push('/history-archive')"
                    class="text-xs text-purple-400 hover:text-purple-300 transition-colors duration-300 flex items-center gap-1"
                  >
                    查看全部
                    <ChevronRight class="w-4 h-4" />
                  </button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div
                    v-for="record in historyRecords"
                    :key="record.id"
                    class="relative overflow-hidden bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-2xl p-4 cursor-pointer transition-all duration-300 group hover:-translate-y-1 hover:border-purple-500/30 hover:shadow-[0_0_20px_rgba(168,85,247,0.1)] text-left"
                    @click="goToHistory(record)"
                  >
                    <div class="flex items-center justify-between mb-2">
                      <div class="flex items-center gap-2">
                        <span class="text-xs px-2 py-0.5 rounded-full border" :class="getCategoryColor(record.category)">{{ getCategoryLabel(record.category) }}</span>
                        <span v-if="getDifficultyBadge(record) && getDifficultyBadgeConfig(getDifficultyBadge(record))" class="text-[10px] px-1.5 py-0.5 rounded-full border" :class="getDifficultyBadgeConfig(getDifficultyBadge(record)).class">{{ getDifficultyBadgeConfig(getDifficultyBadge(record)).label }}</span>
                      </div>
                      <span class="text-[10px] text-gray-600">{{ record.created_at }}</span>
                    </div>
                    <p class="text-xs text-gray-400 truncate">{{ record.user_input }}</p>
                    <p v-if="record.ai_result" class="text-[11px] text-gray-600 truncate mt-1">{{ record.ai_result.substring(0, 60) }}...</p>
                  </div>
                </div>
              </div>

              <div class="chat-messages mb-6 space-y-4 animate-[fadeInUp_0.5s_ease-out_0.3s_both]" v-if="chatMessages.length > 0" v-auto-animate>
                <div v-for="(message, index) in chatMessages" :key="index" class="chat-message">
                  <div v-if="message.role === 'user'" class="flex justify-end">
                    <div class="max-w-[80%] bg-gradient-to-r from-fuchsia-500/20 to-purple-500/20 border border-fuchsia-500/30 rounded-xl p-3 text-right">
                      <p class="text-sm text-gray-200">{{ message.content }}</p>
                      <p class="text-xs text-gray-500 mt-1">{{ message.timestamp }}</p>
                    </div>
                  </div>
                  <div v-else class="flex gap-3">
                    <div class="w-8 h-8 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
                      <Bot class="w-4 h-4 text-cyan-400" />
                    </div>
                    <div class="max-w-[80%] bg-gradient-to-r from-gray-800/50 to-gray-900/50 border border-white/10 rounded-xl p-3">
                      <div class="text-sm text-gray-200 dashboard-markdown" v-html="marked.parse(message.content)"></div>
                      <p class="text-xs text-gray-500 mt-1">{{ message.timestamp }}</p>
                    </div>
                  </div>
                </div>

                <div v-if="isChatLoading" class="flex gap-3">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
                    <Loader2 class="w-4 h-4 animate-spin text-cyan-400" />
                  </div>
                  <div class="bg-gradient-to-r from-gray-800/50 to-gray-900/50 border border-white/10 rounded-xl px-4 py-3">
                    <div class="flex items-center gap-1.5">
                      <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0s;"></div>
                      <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0.2s;"></div>
                      <div class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce" style="animation-delay: 0.4s;"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="quick-actions-bubbles mb-4 flex flex-wrap gap-2 justify-start animate-[fadeInUp_0.5s_ease-out_0.4s_both]">
                <button
                  v-for="action in quickActions"
                  :key="action"
                  @click="userChatInput = action"
                  class="quick-action px-3 py-1 rounded-full bg-white/10 hover:bg-white/15 hover:scale-105 text-xs text-gray-300 transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/20"
                >
                  {{ action }}
                </button>
              </div>
            </div>
          </div>

          <!-- 底部 Dock 输入框 - 通用职业助手 -->
          <div class="input-container absolute bottom-8 left-0 w-full flex justify-center z-[60] pointer-events-none animate-[fadeInUp_0.5s_ease-out_0.5s_both] pb-[env(safe-area-inset-bottom)]">
            <div
              class="input-wrapper relative pointer-events-auto w-full max-w-4xl bg-black/50 backdrop-blur-md rounded-xl border border-white/10 p-4 transition-all duration-300"
              :class="{ 'border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.2)]': isChatLoading }"
            >
              <!-- 已上传附件提示 -->
              <div v-if="uploadedGlobalResume" class="mb-3 flex items-center gap-2">
                <div class="bg-cyan-500/20 border border-cyan-500/30 rounded-full px-3 py-1 flex items-center gap-2">
                  <CheckCircle class="w-3.5 h-3.5 text-cyan-400" />
                  <span class="text-xs text-cyan-200 truncate max-w-[200px]">已附加文件（仅本轮对话）</span>
                  <button
                    @click="removeUploadedResume"
                    class="text-gray-400 hover:text-white transition-colors"
                  >
                    <X class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div class="flex items-end gap-3">
                <label class="relative flex-shrink-0 mb-0.5">
                  <input type="file" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" @change="handleChatFileUpload" accept=".pdf,.doc,.docx,.txt,.jpg,.png" />
                  <Paperclip class="w-5 h-5 text-gray-400 hover:text-cyan-400 transition-colors cursor-pointer" />
                </label>

                <textarea
                  v-model="userChatInput"
                  @keydown="handleChatEnter"
                  :placeholder="chatPlaceholder"
                  rows="1"
                  class="flex-1 bg-transparent border-none outline-none text-gray-300 placeholder-gray-500 resize-none text-sm leading-relaxed focus:ring-0"
                ></textarea>

                <button
                  @click="sendGeneralChatMessage"
                  :disabled="isChatLoading || !userChatInput.trim()"
                  class="flex-shrink-0 px-4 py-2.5 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 overflow-hidden relative bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50 mb-0.5"
                >
                  <Send class="w-4 h-4" />
                </button>
              </div>

              <div class="flex items-center gap-2 mt-2">
                <Sparkles class="w-3 h-3 text-cyan-500/50" />
                <span class="text-[10px] text-gray-600">AI 职场领航员 · 附件仅作本轮对话上下文</span>
              </div>
            </div>
          </div>
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
  </div>
</template>

<style scoped>
.app-container {
  background-color: #050505;
}

.left-sidebar::-webkit-scrollbar,
.main-content::-webkit-scrollbar {
  width: 6px;
}

.left-sidebar::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.left-sidebar::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}

.left-sidebar::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
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

.history-item {
  transition: all 0.3s ease;
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
</style>
