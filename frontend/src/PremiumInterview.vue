<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Send, UserCircle, Cpu, Loader2, Shield, AlertTriangle } from 'lucide-vue-next'
import { marked } from 'marked'

const router = useRouter()

const currentSessionId = ref(crypto.randomUUID())

const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const isInterviewEnded = ref(false)
const isEvaluationDone = ref(false)
const candidateName = ref('')
const targetRole = ref('')
const resumeText = ref('')
const interviewJd = ref('')

const radarScores = ref({
  professional: 2,
  logic: 2,
  communication: 2,
  problemSolving: 2,
  potential: 2
})

const RADAR_LABELS = ['professional', 'logic', 'communication', 'problemSolving', 'potential']
const RADAR_CENTER = 100
const RADAR_MAX_RADIUS = 70

const radarPoints = computed(() => {
  const angles = RADAR_LABELS.map((_, i) => (i * 72 - 90) * Math.PI / 180)
  return angles.map((angle, i) => {
    const score = radarScores.value[RADAR_LABELS[i]]
    const r = (score / 100) * RADAR_MAX_RADIUS
    return `${RADAR_CENTER + r * Math.cos(angle)},${RADAR_CENTER + r * Math.sin(angle)}`
  }).join(' ')
})

const isResumeValid = computed(() => {
  return resumeText.value && resumeText.value.trim().length >= 20
})

const CHAT_API_URL = 'http://127.0.0.1:8000/api/interview/chat'

const messagesContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const addMessage = (role, content) => {
  messages.value.push({
    role,
    content,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  scrollToBottom()
}

const initInterview = async () => {
  const name = localStorage.getItem('candidate_name') || ''
  const role = localStorage.getItem('target_role') || ''
  const resume = localStorage.getItem('resume_text') || ''
  const jd = localStorage.getItem('current_interview_jd') || ''

  candidateName.value = name
  targetRole.value = role
  resumeText.value = resume
  interviewJd.value = jd

  isLoading.value = true
  try {
    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        // 核心改动：剥离冗长的提示词，只发送这句极简的开场白
        user_query: `面试官您好，我是候选人${name || '未知'}，应聘岗位是${role || '未指定'}。请您直接根据我的简历开始向我提问。`,
        history: [],
        resume_text: resume,
        jd_text: jd,
        session_id: currentSessionId.value
      })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    const reply = data.reply || `${name || '候选人'}你好，请直接开始1分钟的自我介绍。`
    addMessage('ai', reply)
  } catch (error) {
    console.error('初始化面试失败:', error)
    addMessage('ai', `${name || '候选人'}你好，请直接开始1分钟的自我介绍。`)
  } finally {
    isLoading.value = false
  }
}

const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value || isInterviewEnded.value) return

  const userMessage = userInput.value.trim()
  addMessage('user', userMessage)
  userInput.value = ''
  isLoading.value = true

  try {
    const history = messages.value.map(msg => ({ role: msg.role, content: msg.content }))

    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: userMessage, // 剥掉马甲，恢复裸奔！
        history,
        resume_text: resumeText.value,
        jd_text: interviewJd.value,
        session_id: currentSessionId.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const reply = data.reply || '请继续。'
    addMessage('ai', reply)
  } catch (error) {
    console.error('发送消息失败:', error)
    addMessage('ai', '系统异常，请重试。')
  } finally {
    isLoading.value = false
  }
}

// 接入真实打分，附带【防刷分机制】
const endInterview = async () => {
  const userMessages = messages.value.filter(m => m.role === 'user')
  const userMessageCount = userMessages.length
  
  // 【核心防刷】：计算用户发过的所有字数总和
  const totalUserCharCount = userMessages.reduce((sum, m) => sum + m.content.length, 0)
  
  // 如果一句没说，或者总字数少于 20 个字，直接判定作弊零分！
  if (userMessageCount === 0 || totalUserCharCount < 20) {
    addMessage('ai', '【系统警告】检测到您的有效作答字数过少或涉嫌敷衍，系统拒绝生成能力图谱。本次面试已强行终止！')
    radarScores.value = { professional: 0, logic: 0, communication: 0, problemSolving: 0, potential: 0 }
    isInterviewEnded.value = true // 锁定输入框
    return
  }

  isInterviewEnded.value = true // 锁定输入框
  addMessage('ai', '面试已结束。系统正在深度提取您的历史对话数据，生成多维度能力评估图谱，请稍候...')
  isLoading.value = true

  try {
    // 调用后端的真实打分接口
    const response = await fetch('http://127.0.0.1:8000/api/interview/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: "请根据对话记录生成 JSON 评估报告", 
        history: messages.value,
        session_id: currentSessionId.value
      })
    })

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    
    const resData = await response.json()
    
    if (resData.success && resData.data) {
      radarScores.value = {
        professional: resData.data.professional || 10,
        logic: resData.data.logic || 10,
        communication: resData.data.communication || 10,
        problemSolving: resData.data.problemSolving || 10,
        potential: resData.data.potential || 10
      }
      addMessage('ai', `【终极评估】\n${resData.data.comment || '无评价。'}`)
      isEvaluationDone.value = true
    } else {
      throw new Error(resData.msg || "打分数据解析失败")
    }
  } catch (error) {
    console.error("生成评估失败:", error)
    radarScores.value = { professional: 0, logic: 0, communication: 0, problemSolving: 0, potential: 0 }
    addMessage('ai', '系统打分引擎异常，生成评估失败。')
  } finally {
    isLoading.value = false
  }
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

    <!-- CRT 扫描线覆盖层 -->
    <div class="crt-overlay absolute inset-0 pointer-events-none z-50"></div>

    <!-- 主内容 -->
    <div class="relative z-10 flex w-full h-screen">
      <!-- 左侧面板 -->
      <div class="left-panel w-[30%] flex flex-col border-r border-white/10 bg-white/[0.02] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
        <!-- 返回按钮 -->
        <div class="p-4 border-b border-white/10">
          <button
            @click="router.push('/dashboard')"
            class="w-full flex items-center gap-2 text-fuchsia-400/70 hover:text-fuchsia-400 transition-all duration-300 group">
            <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-300" />
            <span class="text-sm">返回工作台</span>
          </button>
        </div>

        <!-- 能力评估雷达 -->
        <div class="p-4 border-b border-white/10">
          <div class="flex items-center gap-2 mb-3">
            <Cpu class="w-5 h-5 text-fuchsia-400" />
            <h2 class="text-sm font-bold text-fuchsia-400">能力评估雷达</h2>
          </div>
          <div class="radar-container aspect-square rounded-xl border border-fuchsia-500/20 bg-white/[0.02] backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] p-4 relative overflow-hidden">
            <!-- 声呐扫描扇面 -->
            <div class="sonar-sweep"></div>
            <div class="sonar-sweep sonar-sweep-delay"></div>
            <svg viewBox="0 0 200 200" class="w-full h-full relative z-10">
              <defs>
                <linearGradient id="radarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#e879f9" stop-opacity="0.6" />
                  <stop offset="100%" stop-color="#c026d3" stop-opacity="0.3" />
                </linearGradient>
                <!-- 声呐扫描渐变 -->
                <linearGradient id="sonarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#e879f9" stop-opacity="0.8" />
                  <stop offset="100%" stop-color="#e879f9" stop-opacity="0" />
                </linearGradient>
              </defs>
              <!-- 雷达同心圆 -->
              <circle cx="100" cy="100" r="20" fill="none" stroke="rgba(232,121,249,0.1)" stroke-width="0.5" />
              <circle cx="100" cy="100" r="40" fill="none" stroke="rgba(232,121,249,0.1)" stroke-width="0.5" />
              <circle cx="100" cy="100" r="60" fill="none" stroke="rgba(232,121,249,0.1)" stroke-width="0.5" />
              <!-- 五边形外框 -->
              <polygon
                points="100,20 180,72 150,185 50,185 20,72"
                fill="none"
                stroke="rgba(232,121,249,0.15)"
                stroke-width="1"
              />
              <!-- 雷达数据多边形 -->
              <polygon
                :points="radarPoints"
                fill="url(#radarGrad)"
                stroke="rgba(232,121,249,0.5)"
                stroke-width="1.5"
                class="radar-polygon"
              />
              <!-- 雷达数据点 -->
              <circle v-for="(point, i) in radarPoints.split(' ')" :key="i"
                :cx="point.split(',')[0]" :cy="point.split(',')[1]" r="2"
                fill="#e879f9" class="radar-dot" />
              <!-- 标签 -->
              <text x="100" y="15" text-anchor="middle" fill="#e879f9" font-size="10">专业技能</text>
              <text x="180" y="100" text-anchor="middle" fill="#e879f9" font-size="10">逻辑分析</text>
              <text x="150" y="185" text-anchor="middle" fill="#e879f9" font-size="10">沟通表达</text>
              <text x="50" y="185" text-anchor="middle" fill="#e879f9" font-size="10">问题解决</text>
              <text x="20" y="100" text-anchor="middle" fill="#e879f9" font-size="10">综合潜力</text>
            </svg>
          </div>
        </div>

        <!-- 候选人档案 -->
        <div class="flex-1 p-4 overflow-y-auto">
          <div class="flex items-center gap-2 mb-3">
            <Shield class="w-5 h-5 text-fuchsia-400" />
            <h2 class="text-sm font-bold text-fuchsia-400">候选人档案</h2>
          </div>
          <div class="rounded-xl border p-4 max-h-[calc(100vh-500px)] overflow-y-auto backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300"
            :class="isResumeValid
              ? 'bg-white/[0.02] border-fuchsia-500/20'
              : 'bg-amber-500/5 border-amber-500/20'">
            <template v-if="isResumeValid">
              <p class="text-xs leading-relaxed whitespace-pre-wrap text-fuchsia-100/70">{{ resumeText }}</p>
            </template>
            <template v-else>
              <div class="flex items-start gap-2">
                <AlertTriangle class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="text-xs text-amber-300 font-semibold mb-1">简历数据缺失</p>
                  <p class="text-[11px] text-amber-400/70 leading-relaxed">系统已自动切换至【全栈盲测模式】。面试官将进行无差别跨域打击。如需精准面试，请退回工作台重新导入标准简历。</p>
                </div>
              </div>
            </template>
          </div>

          <!-- 岗位描述 -->
          <div v-if="interviewJd" class="mt-4">
            <div class="flex items-center gap-2 mb-3">
              <svg class="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              <h2 class="text-sm font-bold text-cyan-400">目标岗位 (JD)</h2>
            </div>
            <div class="rounded-xl border border-cyan-500/20 bg-white/[0.02] backdrop-blur-xl p-4 max-h-[200px] overflow-y-auto shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
              <p class="text-xs leading-relaxed whitespace-pre-wrap text-cyan-100/70">{{ interviewJd }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧主对话控制台 -->
      <div class="flex-1 flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-fuchsia-500/20 bg-white/[0.03] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-fuchsia-500 to-pink-500 flex items-center justify-center shadow-lg shadow-fuchsia-500/30">
              <Cpu class="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 class="text-lg font-bold text-fuchsia-400">👑 P8 级 AI 面试官系统</h1>
              <p class="text-xs text-pink-400/50">沉浸式面试模式 · 准备就绪</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></div>
            <span class="text-xs text-green-400 font-mono">System Online</span>
          </div>
        </div>

        <!-- 消息流区 -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex items-start gap-3 message-enter"
            :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'">
            <!-- 头像 -->
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border transition-all duration-300"
              :class="msg.role === 'user'
                ? 'bg-white/10 border-white/20'
                : 'bg-fuchsia-500/20 border-fuchsia-500/30'">
              <component
                :is="msg.role === 'user' ? UserCircle : Cpu"
                class="w-4 h-4"
                :class="msg.role === 'user' ? 'text-gray-300' : 'text-fuchsia-400'" />
            </div>

            <!-- 消息气泡 -->
            <div
              class="max-w-[70%] rounded-2xl px-4 py-3 relative overflow-hidden transition-all duration-300"
              :class="msg.role === 'user'
                ? 'bg-white/10 border border-white/20 text-gray-200 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
                : 'bg-white/[0.03] border border-fuchsia-500/10 text-fuchsia-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'">
              <!-- AI 气泡左侧指示条 -->
              <div
                v-if="msg.role === 'ai'"
                class="absolute left-0 top-3 bottom-3 w-[2px] rounded-full bg-fuchsia-500"></div>
              <div v-if="msg.role === 'ai'" v-html="marked.parse(msg.content)" class="markdown-body chat-markdown pl-3"></div>
              <p v-else class="text-sm leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>
              <p class="text-[10px] text-gray-500 mt-1.5 text-right" :class="msg.role === 'ai' ? 'pl-3' : ''">{{ msg.timestamp }}</p>
            </div>
          </div>

          <!-- Loading 动画 -->
          <div v-if="isLoading" class="flex items-start gap-3 message-enter">
            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border bg-fuchsia-500/20 border-fuchsia-500/30">
              <Loader2 class="w-4 h-4 animate-spin text-fuchsia-400" />
            </div>
            <div class="rounded-2xl px-5 py-3 border bg-white/[0.03] border-fuchsia-500/10 backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
              <div class="flex items-center gap-1.5">
                <div class="w-2 h-2 rounded-full bg-fuchsia-500 animate-bounce" style="animation-delay: 0s;"></div>
                <div class="w-2 h-2 rounded-full bg-fuchsia-500 animate-bounce" style="animation-delay: 0.2s;"></div>
                <div class="w-2 h-2 rounded-full bg-fuchsia-500 animate-bounce" style="animation-delay: 0.4s;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部输入区 -->
        <div class="border-t border-fuchsia-500/20 bg-white/[0.03] backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] p-4">
          <div class="flex items-end gap-3">
            <textarea
              v-model="userInput"
              @keydown="handleEnter"
              placeholder="输入你的回答..."
              rows="2"
              :disabled="isLoading"
              class="flex-1 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 border border-fuchsia-500/20 text-fuchsia-100 placeholder-pink-400/30 focus:border-fuchsia-500/50 focus:ring-2 focus:ring-fuchsia-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            ></textarea>
            <button
              @click="sendMessage"
              :disabled="isLoading || !userInput.trim()"
              class="send-btn px-6 py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2 overflow-hidden relative bg-gradient-to-r from-fuchsia-500 to-pink-500 text-white shadow-fuchsia-500/30 hover:shadow-xl hover:shadow-fuchsia-500/50">
              <span class="send-btn-shimmer"></span>
              <Send class="w-4 h-4 relative z-10" />
              <span class="relative z-10">发送回答</span>
            </button>
          </div>
          <!-- 结束面试按钮 / 跳转职业规划 -->
          <div class="flex justify-center mt-3">
            <button
              v-if="!isEvaluationDone"
              @click="endInterview"
              :disabled="isLoading || messages.length === 0"
              class="ghost-btn px-5 py-2 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed">
              <span class="relative z-10">结束面试并获取评估</span>
            </button>
            <transition name="fade-up">
              <button
                v-if="isEvaluationDone"
                @click="router.push('/career-planning')"
                class="career-nav-btn px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/50 hover:scale-[1.02]">
                <span class="career-nav-shimmer"></span>
                <svg class="w-4 h-4 relative z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <polygon points="16.24 7.76 14.12 7.76 10 11.88 10 14 12.12 14 16.24 9.88 16.24 7.76" />
                </svg>
                <span class="relative z-10">🧭 寻求导师帮助：生成专属职业规划</span>
              </button>
            </transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 极光流体动画 */
.aurora-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  mix-blend-mode: screen;
}

.aurora-blob-1 {
  width: 700px;
  height: 700px;
  background: radial-gradient(circle, rgba(147, 51, 234, 0.2) 0%, transparent 70%);
  top: -15%;
  left: 5%;
  animation: auroraSpin1 30s ease-in-out infinite;
}

.aurora-blob-2 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(236, 72, 153, 0.18) 0%, transparent 70%);
  top: 30%;
  right: -10%;
  animation: auroraSpin2 35s ease-in-out infinite;
}

.aurora-blob-3 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%);
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

/* 网格背景 */
.grid-bg {
  background-image:
    linear-gradient(rgba(236, 72, 153, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(236, 72, 153, 0.06) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* CRT 扫描线 */
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

/* 声呐扫描动画 */
.radar-container {
  position: relative;
}

.sonar-sweep {
  position: absolute;
  inset: 16px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    transparent 300deg,
    rgba(232, 121, 249, 0.25) 330deg,
    rgba(232, 121, 249, 0.4) 345deg,
    rgba(232, 121, 249, 0.1) 360deg
  );
  animation: sonarRotate 4s linear infinite;
  pointer-events: none;
}

.sonar-sweep-delay {
  animation-delay: -2s;
  opacity: 0.5;
  background: conic-gradient(
    from 180deg,
    transparent 0deg,
    transparent 300deg,
    rgba(232, 121, 249, 0.15) 330deg,
    rgba(232, 121, 249, 0.25) 345deg,
    rgba(232, 121, 249, 0.05) 360deg
  );
}

@keyframes sonarRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 雷达多边形动画 */
.radar-polygon {
  transition: all 1s cubic-bezier(0.16, 1, 0.3, 1);
}

.radar-dot {
  animation: radarDotPulse 2s ease-in-out infinite;
}

@keyframes radarDotPulse {
  0%, 100% { opacity: 0.6; r: 2; }
  50% { opacity: 1; r: 3; }
}

/* 消息入场动画 */
.message-enter {
  animation: messageSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 发送按钮流光效果 */
.send-btn {
  position: relative;
  overflow: hidden;
}

.send-btn-shimmer {
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

/* 幽灵按钮 - 结束面试 */
.ghost-btn {
  position: relative;
  overflow: hidden;
  background: transparent;
  border: 1px solid rgba(232, 121, 249, 0.25);
  color: rgba(232, 121, 249, 0.7);
}

.ghost-btn:hover:not(:disabled) {
  border-color: rgba(232, 121, 249, 0.6);
  color: rgba(232, 121, 249, 1);
  box-shadow: 0 0 20px rgba(232, 121, 249, 0.2), inset 0 0 20px rgba(232, 121, 249, 0.05);
}

.ghost-btn:active:not(:disabled) {
  transform: scale(0.98);
}

/* 滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}

textarea::-webkit-scrollbar {
  width: 6px;
}

textarea::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}

textarea::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}

.markdown-body.chat-markdown {
  font-size: 14px;
  line-height: 1.7;
  word-wrap: break-word;
  color: rgba(252, 231, 243, 0.9);
}

.markdown-body.chat-markdown :deep(h1) {
  font-size: 1.3em;
  font-weight: 700;
  margin: 0.6em 0 0.3em;
  padding-bottom: 0.2em;
  background: linear-gradient(135deg, #f472b6, #c084fc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid rgba(236, 72, 153, 0.15);
}

.markdown-body.chat-markdown :deep(h2) {
  font-size: 1.15em;
  font-weight: 600;
  margin: 0.5em 0 0.25em;
  background: linear-gradient(135deg, #ec4899, #a855f7);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body.chat-markdown :deep(h3) {
  font-size: 1.05em;
  font-weight: 600;
  margin: 0.4em 0 0.2em;
  background: linear-gradient(135deg, #f472b6, #d946ef);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.markdown-body.chat-markdown :deep(strong),
.markdown-body.chat-markdown :deep(b) {
  color: #f472b6;
  font-weight: 700;
}

.markdown-body.chat-markdown :deep(p) {
  margin: 0.3em 0;
  color: rgba(252, 231, 243, 0.85);
}

.markdown-body.chat-markdown :deep(ul),
.markdown-body.chat-markdown :deep(ol) {
  padding-left: 1.3em;
  margin: 0.3em 0;
}

.markdown-body.chat-markdown :deep(li) {
  margin: 0.15em 0;
  color: rgba(252, 231, 243, 0.8);
}

.markdown-body.chat-markdown :deep(li)::marker {
  color: #ec4899;
  text-shadow: 0 0 6px rgba(236, 72, 153, 0.5);
}

.markdown-body.chat-markdown :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0.5em 0;
  border: 1px solid rgba(236, 72, 153, 0.2);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
  font-size: 13px;
}

.markdown-body.chat-markdown :deep(thead) {
  background: rgba(236, 72, 153, 0.08);
}

.markdown-body.chat-markdown :deep(th) {
  padding: 7px 10px;
  text-align: left;
  font-weight: 600;
  color: #f472b6;
  font-size: 12px;
  border-bottom: 1px solid rgba(236, 72, 153, 0.2);
}

.markdown-body.chat-markdown :deep(td) {
  padding: 6px 10px;
  font-size: 12px;
  color: rgba(252, 231, 243, 0.8);
  border-bottom: 1px solid rgba(236, 72, 153, 0.06);
}

.markdown-body.chat-markdown :deep(tr:hover td) {
  background: rgba(236, 72, 153, 0.05);
}

.markdown-body.chat-markdown :deep(blockquote) {
  border-left: 3px solid rgba(236, 72, 153, 0.35);
  padding: 0.3em 0.8em;
  margin: 0.4em 0;
  background: rgba(236, 72, 153, 0.04);
  border-radius: 0 6px 6px 0;
  color: rgba(252, 231, 243, 0.7);
}

.markdown-body.chat-markdown :deep(code) {
  background: rgba(236, 72, 153, 0.1);
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.88em;
  color: #f9a8d4;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.markdown-body.chat-markdown :deep(pre) {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(236, 72, 153, 0.12);
  border-radius: 8px;
  padding: 0.8em;
  overflow-x: auto;
  margin: 0.4em 0;
}

.markdown-body.chat-markdown :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  color: rgba(252, 231, 243, 0.85);
}

.markdown-body.chat-markdown :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.25), transparent);
  margin: 0.8em 0;
}

.fade-up-enter-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.fade-up-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(16px);
}

.career-nav-btn {
  position: relative;
  overflow: hidden;
  animation: careerNavBreathe 2.5s ease-in-out infinite;
}

@keyframes careerNavBreathe {
  0%, 100% { box-shadow: 0 0 15px rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 0 30px rgba(6, 182, 212, 0.6), 0 0 60px rgba(59, 130, 246, 0.2); }
}

.career-nav-shimmer {
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
</style>
