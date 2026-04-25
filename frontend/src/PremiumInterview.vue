<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Send, UserCircle, Cpu, Loader2, Shield, AlertTriangle } from 'lucide-vue-next'

const router = useRouter()

const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const candidateName = ref('')
const targetRole = ref('')
const resumeText = ref('')
const interviewJd = ref('')

const radarScores = ref({
  technical: 15,
  architecture: 12,
  communication: 18,
  problemSolving: 10,
  leadership: 8
})

const RADAR_LABELS = ['technical', 'architecture', 'communication', 'problemSolving', 'leadership']
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

  const systemPrompt = `【系统指令】：候选人姓名是 ${name || '未知'}，应聘岗位是 ${role || '未指定'}。目标岗位描述（JD）：${jd || '暂无'}。这是他的简历：${resume || '暂无简历内容'}。现在请你以面试官身份打招呼，并要求他做自我介绍。`

  try {
    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: systemPrompt,
        history: [],
        is_first_message: true,
        resume_text: resume,
        jd_text: jd
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const reply = data.reply || data.content || data.message || `${name || '候选人'}你好，欢迎参加本次技术面试。我是你的面试官。在开始之前，请先简单介绍一下你自己。`
    addMessage('ai', reply)
  } catch (error) {
    console.error('初始化面试失败，使用降级方案:', error)
    addMessage('ai', `${name || '候选人'}你好，欢迎参加本次技术面试。我是你的面试官。在开始之前，请先简单介绍一下你自己。`)
  }
}

const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return

  const userMessage = userInput.value.trim()
  addMessage('user', userMessage)
  userInput.value = ''
  isLoading.value = true

  try {
    const history = messages.value
      .map(msg => ({ role: msg.role, content: msg.content }))

    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: userMessage,
        history,
        is_first_message: false,
        resume_text: resumeText.value,
        jd_text: interviewJd.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const reply = data.reply || data.content || data.message || '你的回答需要更深入。让我们继续下一道题。'
    addMessage('ai', reply)
  } catch (error) {
    console.error('发送消息失败:', error)
    addMessage('ai', '系统异常，请重试。')
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
              <text x="100" y="15" text-anchor="middle" fill="#e879f9" font-size="10">技术深度</text>
              <text x="180" y="100" text-anchor="middle" fill="#e879f9" font-size="10">架构设计</text>
              <text x="150" y="185" text-anchor="middle" fill="#e879f9" font-size="10">沟通能力</text>
              <text x="50" y="185" text-anchor="middle" fill="#e879f9" font-size="10">问题解决</text>
              <text x="20" y="100" text-anchor="middle" fill="#e879f9" font-size="10">领导力</text>
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
              <p class="text-sm leading-relaxed whitespace-pre-wrap" :class="msg.role === 'ai' ? 'pl-3' : ''">{{ msg.content }}</p>
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
              class="flex-1 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-300 bg-black/60 border border-fuchsia-500/20 text-fuchsia-100 placeholder-pink-400/30 focus:border-fuchsia-500/50 focus:ring-2 focus:ring-fuchsia-500/20"
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
</style>
