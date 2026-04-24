<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Send, UserCircle, Cpu, Loader2, CreditCard, Shield, CheckCircle, AlertTriangle } from 'lucide-vue-next'

const router = useRouter()

const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const candidateName = ref('')
const targetRole = ref('')
const resumeText = ref('')
const isPaymentDone = ref(false)
const isPaymentChecking = ref(false)
const isPremiumMode = ref(false)

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

const updateRadar = (newScores) => {
  RADAR_LABELS.forEach(key => {
    if (newScores[key] !== undefined) {
      radarScores.value[key] = newScores[key]
    }
  })
}

const isResumeValid = computed(() => {
  return resumeText.value && resumeText.value.trim().length >= 20
})

const CHAT_API_URL = 'http://127.0.0.1:8000/api/interview/chat'
const CHECK_ORDER_URL = 'http://127.0.0.1:8000/api/interview/check-order'
const QR_SERVER_URL = 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data='

const messagesContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const generateQrCodeUrl = (rawData) => {
  if (!rawData) return `${QR_SERVER_URL}PremiumInterviewUnlock&margin=10`
  const encoded = encodeURIComponent(rawData)
  return `${QR_SERVER_URL}${encoded}&margin=10`
}

const addMessage = (role, content, type = 'text', paymentData = null) => {
  messages.value.push({
    role,
    content,
    type,
    paymentData,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  scrollToBottom()
}

const initInterview = async () => {
  const name = localStorage.getItem('candidate_name') || ''
  const role = localStorage.getItem('target_role') || ''
  const resume = localStorage.getItem('resume_text') || ''

  candidateName.value = name
  targetRole.value = role
  resumeText.value = resume

  const systemPrompt = `【系统指令】：候选人姓名是 ${name || '未知'}，应聘岗位是 ${role || '未指定'}。这是他的简历：${resume || '暂无简历内容'}。现在请你以面试官身份打招呼，并要求他做自我介绍。`

  try {
    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: systemPrompt,
        history: [],
        is_first_message: true,
        resume_text: resume
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const reply = data.reply || data.content || data.message || `${name || '候选人'}你好，欢迎参加本次技术面试。我是你的面试官。在开始之前，请先简单介绍一下你自己。`
    const weixinLink = data.weixin_url || data.payment_url || data.qr_data || ''
    const isPaymentRequired = data.is_payment_required === true && !!weixinLink

    if (isPaymentRequired) {
      addMessage('ai', reply, 'payment', { amount: '0.01', qrCode: generateQrCodeUrl(weixinLink), weixinLink })
    } else {
      addMessage('ai', reply, 'text')
    }
  } catch (error) {
    console.error('初始化面试失败，使用降级方案:', error)
    addMessage('ai', `${name || '候选人'}你好，欢迎参加本次技术面试。我是你的面试官。在开始之前，请先简单介绍一下你自己。`, 'text')
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
      .filter(msg => msg.role !== 'payment')
      .map(msg => ({ role: msg.role, content: msg.content }))

    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_query: userMessage,
        history,
        is_first_message: false,
        resume_text: resumeText.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const reply = data.reply || data.content || data.message || '你的回答需要更深入。让我们继续下一道题。'
    const weixinLink = data.weixin_url || data.payment_url || data.qr_data || ''
    const isPaymentRequired = (data.is_payment_required === true) && !!weixinLink && !isPaymentDone.value

    if (isPaymentRequired) {
      addMessage('ai', '', 'payment', { amount: '0.01', qrCode: generateQrCodeUrl(weixinLink), weixinLink })
    } else {
      addMessage('ai', reply, 'text')
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    addMessage('ai', '系统异常，请重试。', 'text')
  } finally {
    isLoading.value = false
  }
}

const handlePayment = async () => {
  if (isPaymentChecking.value) return
  isPaymentChecking.value = true

  try {
    const response = await fetch(CHECK_ORDER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: '0.01', status: 'check' })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    if (data.success || data.paid || data.status === 'completed') {
      isPaymentDone.value = true
      isPremiumMode.value = true
      addMessage('ai', '诚意已核实。现在，第一道高压题来了...', 'text')

      updateRadar({
        technical: 45,
        architecture: 38,
        communication: 52,
        problemSolving: 40,
        leadership: 30
      })

      setTimeout(async () => {
        try {
          const history = messages.value
            .filter(msg => msg.role !== 'payment')
            .map(msg => ({ role: msg.role, content: msg.content }))

          const response = await fetch(CHAT_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_query: '支付完成，请开始第一轮高压面试',
              history,
              is_first_message: false,
              payment_verified: true,
              resume_text: resumeText.value
            })
          })

          if (response.ok) {
            const data = await response.json()
            const reply = data.reply || data.content || data.message
            if (reply) {
              addMessage('ai', reply, 'text')
            }
          }
        } catch (error) {
          console.error('获取高压面试题失败:', error)
        }
      }, 1500)
    } else {
      addMessage('ai', '支付状态尚未确认，请稍后再试。', 'text')
    }
  } catch (error) {
    console.error('检查支付状态失败:', error)
    addMessage('ai', '支付验证系统异常，请稍后重试。', 'text')
  } finally {
    isPaymentChecking.value = false
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
    <!-- 动态网格背景 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute inset-0 transition-all duration-1000" :style="{
        backgroundImage: isPremiumMode
          ? 'linear-gradient(rgba(212, 175, 55, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(212, 175, 55, 0.06) 1px, transparent 1px)'
          : 'linear-gradient(rgba(236, 72, 153, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(236, 72, 153, 0.06) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }"></div>
      <!-- 径向渐变遮罩 -->
      <div class="absolute inset-0" style="background: radial-gradient(ellipse at center, transparent 0%, #050505 75%);"></div>
    </div>

    <!-- 视差极光背景 (游动光球) -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute w-[600px] h-[600px] rounded-full blur-[120px] transition-all duration-1000 animate-[aurora1_25s_ease-in-out_infinite]"
        :class="isPremiumMode ? 'bg-amber-500/15' : 'bg-fuchsia-600/15'"
        style="top: -10%; left: 5%;"></div>
      <div class="absolute w-[500px] h-[500px] rounded-full blur-[100px] transition-all duration-1000 animate-[aurora2_30s_ease-in-out_infinite]"
        :class="isPremiumMode ? 'bg-yellow-500/10' : 'bg-purple-600/10'"
        style="top: 40%; right: -5%;"></div>
      <div class="absolute w-[400px] h-[400px] rounded-full blur-[80px] transition-all duration-1000 animate-[aurora3_35s_ease-in-out_infinite]"
        :class="isPremiumMode ? 'bg-[#D4AF37]/10' : 'bg-pink-500/10'"
        style="bottom: -5%; left: 30%;"></div>
    </div>

    <!-- CRT 扫描线覆盖层 -->
    <div class="absolute inset-0 pointer-events-none z-50 opacity-[0.03]"
      style="background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.1) 2px, rgba(255,255,255,0.1) 4px);"></div>

    <!-- 主内容 -->
    <div class="relative z-10 flex w-full h-screen">
      <!-- 左侧候选人面板 -->
      <div class="w-[30%] flex flex-col border-r transition-all duration-1000 backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]"
        :class="isPremiumMode
          ? 'bg-white/[0.03] border-[#D4AF37]/20'
          : 'bg-white/[0.03] border-fuchsia-500/20'">
        <div class="p-4 border-b transition-all duration-1000"
          :class="isPremiumMode ? 'border-[#D4AF37]/20' : 'border-fuchsia-500/20'">
          <button
            @click="router.push('/dashboard')"
            class="w-full flex items-center gap-2 transition-all duration-1000 group"
            :class="isPremiumMode ? 'text-[#D4AF37]/70 hover:text-[#D4AF37]' : 'text-fuchsia-400/70 hover:text-fuchsia-400'">
            <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-300" />
            <span class="text-sm">返回工作台</span>
          </button>
        </div>

        <!-- 能力评估雷达 (带声呐扫描) -->
        <div class="p-4 border-b transition-all duration-1000"
          :class="isPremiumMode ? 'border-[#D4AF37]/20' : 'border-fuchsia-500/20'">
          <div class="flex items-center gap-2 mb-3">
            <Cpu class="w-5 h-5 transition-all duration-1000"
              :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'" />
            <h2 class="text-sm font-bold transition-all duration-1000"
              :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'">能力评估雷达</h2>
          </div>
          <div class="aspect-square rounded-xl border p-4 relative overflow-hidden backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000"
            :class="isPremiumMode
              ? 'bg-white/[0.02] border-[#D4AF37]/20'
              : 'bg-white/[0.02] border-fuchsia-500/20'">
            <!-- 声呐扫描扇面 -->
            <div class="absolute inset-4 rounded-full sonar-scan"></div>
            <svg viewBox="0 0 200 200" class="w-full h-full relative z-10">
              <defs>
                <linearGradient id="radarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" :stop-color="isPremiumMode ? '#D4AF37' : '#e879f9'" :stop-opacity="0.6" />
                  <stop offset="100%" :stop-color="isPremiumMode ? '#B8860B' : '#c026d3'" :stop-opacity="0.3" />
                </linearGradient>
              </defs>
              <polygon
                points="100,20 180,72 150,185 50,185 20,72"
                fill="none"
                :stroke="isPremiumMode ? 'rgba(212,175,55,0.15)' : 'rgba(232,121,249,0.15)'"
                stroke-width="1"
                class="transition-all duration-1000"
              />
              <polygon
                :points="radarPoints"
                fill="url(#radarGrad)"
                :stroke="isPremiumMode ? 'rgba(212,175,55,0.5)' : 'rgba(232,121,249,0.5)'"
                stroke-width="1.5"
                class="transition-all duration-1000"
              />
              <text x="100" y="15" text-anchor="middle" :fill="isPremiumMode ? '#D4AF37' : '#e879f9'" font-size="10" class="transition-all duration-1000">技术深度</text>
              <text x="180" y="100" text-anchor="middle" :fill="isPremiumMode ? '#D4AF37' : '#e879f9'" font-size="10" class="transition-all duration-1000">架构设计</text>
              <text x="150" y="185" text-anchor="middle" :fill="isPremiumMode ? '#D4AF37' : '#e879f9'" font-size="10" class="transition-all duration-1000">沟通能力</text>
              <text x="50" y="185" text-anchor="middle" :fill="isPremiumMode ? '#D4AF37' : '#e879f9'" font-size="10" class="transition-all duration-1000">问题解决</text>
              <text x="20" y="100" text-anchor="middle" :fill="isPremiumMode ? '#D4AF37' : '#e879f9'" font-size="10" class="transition-all duration-1000">领导力</text>
            </svg>
          </div>
        </div>

        <!-- 候选人档案 -->
        <div class="flex-1 p-4 overflow-y-auto">
          <div class="flex items-center gap-2 mb-3">
            <Shield class="w-5 h-5 transition-all duration-1000"
              :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'" />
            <h2 class="text-sm font-bold transition-all duration-1000"
              :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'">候选人档案</h2>
          </div>
          <div class="rounded-xl border p-4 max-h-[calc(100vh-500px)] overflow-y-auto backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000"
            :class="isResumeValid
              ? (isPremiumMode ? 'bg-white/[0.02] border-[#D4AF37]/20' : 'bg-white/[0.02] border-fuchsia-500/20')
              : 'bg-amber-500/5 border-amber-500/20'">
            <template v-if="isResumeValid">
              <p class="text-xs leading-relaxed whitespace-pre-wrap transition-all duration-1000"
                :class="isPremiumMode ? 'text-amber-100/70' : 'text-fuchsia-100/70'">{{ resumeText }}</p>
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
        </div>
      </div>

      <!-- 右侧主对话控制台 -->
      <div class="flex-1 flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000"
          :class="isPremiumMode
            ? 'border-[#D4AF37]/20 bg-white/[0.03]'
            : 'border-fuchsia-500/20 bg-white/[0.03]'">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all duration-1000"
              :class="isPremiumMode
                ? 'bg-gradient-to-br from-[#D4AF37] to-amber-600 shadow-[#D4AF37]/30'
                : 'bg-gradient-to-br from-fuchsia-500 to-pink-500 shadow-fuchsia-500/30'">
              <Cpu class="w-5 h-5" :class="isPremiumMode ? 'text-black' : 'text-white'" />
            </div>
            <div>
              <h1 class="text-lg font-bold transition-all duration-1000"
                :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'">👑 P8 级 AI 面试官系统</h1>
              <p class="text-xs transition-all duration-1000"
                :class="isPremiumMode ? 'text-amber-400/50' : 'text-pink-400/50'">
                {{ isPremiumMode ? '黑金版 · 高压测试模式' : '科技版 · 准备就绪' }}
              </p>
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
            class="flex items-start gap-3"
            :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
            style="animation: fadeIn 0.3s ease-out;">
            <!-- 头像 -->
            <div
              v-if="msg.type !== 'payment'"
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border transition-all duration-1000"
              :class="msg.role === 'user'
                ? 'bg-white/10 border-white/20'
                : (isPremiumMode ? 'bg-[#D4AF37]/20 border-[#D4AF37]/30' : 'bg-fuchsia-500/20 border-fuchsia-500/30')">
              <component
                :is="msg.role === 'user' ? UserCircle : Cpu"
                class="w-4 h-4 transition-all duration-1000"
                :class="msg.role === 'user' ? 'text-gray-300' : (isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400')" />
            </div>

            <!-- 支付卡片 (带悬浮呼吸动画) -->
            <div
              v-if="msg.type === 'payment'"
              class="max-w-[480px] w-full mx-auto rounded-2xl overflow-hidden backdrop-blur-3xl border shadow-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000 animate-[floating_4s_ease-in-out_infinite]"
              :class="isPremiumMode
                ? 'bg-white/[0.05] border-[#D4AF37]/30 shadow-[#D4AF37]/10'
                : 'bg-white/[0.05] border-fuchsia-500/30 shadow-fuchsia-500/10'">
              <!-- 顶部安全指示灯 -->
              <div class="px-5 py-3 border-b flex items-center justify-between transition-all duration-1000"
                :class="isPremiumMode ? 'border-[#D4AF37]/20' : 'border-fuchsia-500/20'">
                <div class="flex items-center gap-2.5">
                  <div class="w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-1000"
                    :class="isPremiumMode ? 'bg-[#D4AF37]/20' : 'bg-fuchsia-500/20'">
                    <CreditCard class="w-4 h-4 transition-all duration-1000"
                      :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'" />
                  </div>
                  <span class="text-sm font-semibold transition-all duration-1000"
                    :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'">Secure Payment</span>
                </div>
                <div class="flex items-center gap-1.5">
                  <div class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_6px_rgba(34,197,94,0.8)]"></div>
                  <span class="text-[10px] text-green-400 font-mono tracking-wider">ENCRYPTED</span>
                </div>
              </div>

              <!-- 二维码区域 -->
              <div class="p-6 text-center">
                <p class="text-sm mb-2 transition-all duration-1000"
                  :class="isPremiumMode ? 'text-amber-200/70' : 'text-fuchsia-200/70'">意向金解锁高级面试</p>
                <div class="text-3xl font-bold mb-5 bg-gradient-to-r transition-all duration-1000 bg-clip-text text-transparent"
                  :class="isPremiumMode ? 'from-[#D4AF37] to-amber-500' : 'from-fuchsia-400 to-pink-400'">￥0.01</div>

                <div class="w-48 h-48 mx-auto rounded-xl border flex items-center justify-center mb-5 relative overflow-hidden transition-all duration-1000"
                  :class="isPremiumMode
                    ? 'bg-black/60 border-[#D4AF37]/30 shadow-[0_0_50px_rgba(212,175,55,0.15)]'
                    : 'bg-black/60 border-fuchsia-500/30 shadow-[0_0_50px_rgba(232,121,249,0.15)]'">
                  <!-- 扫描线动画 -->
                  <div class="absolute inset-0 animate-[scanLine_2.5s_ease-in-out_infinite] z-10 pointer-events-none"
                    :style="{
                      background: isPremiumMode
                        ? 'linear-gradient(to bottom, transparent 0%, rgba(212,175,55,0.15) 50%, transparent 100%)'
                        : 'linear-gradient(to bottom, transparent 0%, rgba(236,72,153,0.15) 50%, transparent 100%)',
                      height: '20%'
                    }"></div>
                  <!-- 呼吸光晕边框 -->
                  <div class="absolute inset-0 rounded-xl animate-pulse transition-all duration-1000"
                    :class="isPremiumMode ? 'border-2 border-[#D4AF37]/20' : 'border-2 border-fuchsia-400/20'"></div>
                  <!-- 真实二维码图片 -->
                  <img
                    :src="msg.paymentData?.qrCode || 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=PremiumInterviewUnlock&margin=10'"
                    alt="支付二维码"
                    class="w-44 h-44 object-contain rounded-lg relative z-0"
                  />
                </div>

                <p class="text-xs mb-5 transition-all duration-1000"
                  :class="isPremiumMode ? 'text-amber-400/50' : 'text-pink-400/50'">微信扫码完成支付</p>

                <!-- 闪烁按钮 (Shimmer Button) -->
                <button
                  @click="handlePayment"
                  :disabled="isPaymentChecking"
                  class="shimmer-btn w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-1000 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative"
                  :class="isPremiumMode
                    ? 'bg-gradient-to-r from-[#D4AF37] to-amber-600 text-black shadow-lg shadow-[#D4AF37]/30 hover:shadow-xl hover:shadow-[#D4AF37]/50'
                    : 'bg-gradient-to-r from-fuchsia-500 to-pink-500 text-white shadow-lg shadow-fuchsia-500/30 hover:shadow-xl hover:shadow-fuchsia-500/50'">
                  <!-- 流星扫光特效 -->
                  <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
                  <Loader2 v-if="isPaymentChecking" class="w-4 h-4 animate-spin relative z-10" />
                  <CheckCircle v-else class="w-4 h-4 relative z-10" />
                  <span class="relative z-10">{{ isPaymentChecking ? '验证中...' : '扫码完成，开启高压面试' }}</span>
                </button>
              </div>
            </div>

            <!-- 普通消息气泡 -->
            <div
              v-else
              class="max-w-[70%] rounded-2xl px-4 py-3 transition-all duration-1000 relative overflow-hidden"
              :class="msg.role === 'user'
                ? 'bg-white/10 border border-white/20 text-gray-200 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
                : (isPremiumMode
                  ? 'bg-white/[0.03] border border-[#D4AF37]/10 text-[#D4AF37] shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]'
                  : 'bg-white/[0.03] border border-fuchsia-500/10 text-fuchsia-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]')">
              <!-- AI 气泡左侧高亮指示条 -->
              <div
                v-if="msg.role === 'ai'"
                class="absolute left-0 top-3 bottom-3 w-[2px] rounded-full transition-all duration-1000"
                :class="isPremiumMode ? 'bg-[#D4AF37]' : 'bg-fuchsia-500'"></div>
              <p class="text-sm leading-relaxed whitespace-pre-wrap" :class="msg.role === 'ai' ? 'pl-3' : ''">{{ msg.content }}</p>
              <p class="text-[10px] text-gray-500 mt-1.5 text-right" :class="msg.role === 'ai' ? 'pl-3' : ''">{{ msg.timestamp }}</p>
            </div>
          </div>

          <!-- Loading 动画 -->
          <div v-if="isLoading" class="flex items-start gap-3" style="animation: fadeIn 0.3s ease-out;">
            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border transition-all duration-1000"
              :class="isPremiumMode
                ? 'bg-[#D4AF37]/20 border-[#D4AF37]/30'
                : 'bg-fuchsia-500/20 border-fuchsia-500/30'">
              <Loader2 class="w-4 h-4 animate-spin transition-all duration-1000"
                :class="isPremiumMode ? 'text-[#D4AF37]' : 'text-fuchsia-400'" />
            </div>
            <div class="rounded-2xl px-5 py-3 border backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000"
              :class="isPremiumMode
                ? 'bg-white/[0.03] border-[#D4AF37]/10'
                : 'bg-white/[0.03] border-fuchsia-500/10'">
              <div class="flex items-center gap-1.5">
                <div class="w-2 h-2 rounded-full animate-bounce transition-all duration-1000"
                  :class="isPremiumMode ? 'bg-[#D4AF37]' : 'bg-fuchsia-500'"
                  style="animation-delay: 0s;"></div>
                <div class="w-2 h-2 rounded-full animate-bounce transition-all duration-1000"
                  :class="isPremiumMode ? 'bg-[#D4AF37]' : 'bg-fuchsia-500'"
                  style="animation-delay: 0.2s;"></div>
                <div class="w-2 h-2 rounded-full animate-bounce transition-all duration-1000"
                  :class="isPremiumMode ? 'bg-[#D4AF37]' : 'bg-fuchsia-500'"
                  style="animation-delay: 0.4s;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部输入区 -->
        <div class="border-t backdrop-blur-3xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] p-4 transition-all duration-1000"
          :class="isPremiumMode
            ? 'border-[#D4AF37]/20 bg-white/[0.03]'
            : 'border-fuchsia-500/20 bg-white/[0.03]'">
          <div class="flex items-end gap-3">
            <textarea
              v-model="userInput"
              @keydown="handleEnter"
              placeholder="输入你的回答..."
              rows="2"
              class="flex-1 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)] transition-all duration-1000"
              :class="isPremiumMode
                ? 'bg-black/60 border border-[#D4AF37]/30 text-amber-100 placeholder-amber-400/30 focus:border-[#D4AF37]/50 focus:ring-2 focus:ring-[#D4AF37]/20'
                : 'bg-black/60 border border-fuchsia-500/20 text-fuchsia-100 placeholder-pink-400/30 focus:border-fuchsia-500/50 focus:ring-2 focus:ring-fuchsia-500/20'"
            ></textarea>
            <!-- 发送按钮 (Shimmer) -->
            <button
              @click="sendMessage"
              :disabled="isLoading || !userInput.trim()"
              class="shimmer-btn px-6 py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-1000 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2 overflow-hidden relative"
              :class="isPremiumMode
                ? 'bg-gradient-to-r from-[#D4AF37] to-amber-600 text-black shadow-[#D4AF37]/30 hover:shadow-xl hover:shadow-[#D4AF37]/50'
                : 'bg-gradient-to-r from-fuchsia-500 to-pink-500 text-white shadow-fuchsia-500/30 hover:shadow-xl hover:shadow-fuchsia-500/50'">
              <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
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
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scanLine {
  0% {
    transform: translateY(-100%);
  }
  100% {
    transform: translateY(600%);
  }
}

@keyframes aurora1 {
  0%, 100% {
    transform: translate(0, 0) scale(1) rotate(0deg);
  }
  25% {
    transform: translate(120px, -80px) scale(1.15) rotate(5deg);
  }
  50% {
    transform: translate(-50px, 100px) scale(0.85) rotate(-3deg);
  }
  75% {
    transform: translate(-100px, -40px) scale(1.05) rotate(8deg);
  }
}

@keyframes aurora2 {
  0%, 100% {
    transform: translate(0, 0) scale(1) rotate(0deg);
  }
  25% {
    transform: translate(-150px, 70px) scale(1.1) rotate(-5deg);
  }
  50% {
    transform: translate(80px, -90px) scale(0.9) rotate(3deg);
  }
  75% {
    transform: translate(60px, 50px) scale(1.08) rotate(-8deg);
  }
}

@keyframes aurora3 {
  0%, 100% {
    transform: translate(0, 0) scale(1) rotate(0deg);
  }
  33% {
    transform: translate(80px, -100px) scale(1.2) rotate(10deg);
  }
  66% {
    transform: translate(-120px, 60px) scale(0.8) rotate(-6deg);
  }
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

@keyframes floating {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes sonarPing {
  0% {
    transform: scale(0.3);
    opacity: 0.6;
  }
  100% {
    transform: scale(1);
    opacity: 0;
  }
}

.shimmer-btn {
  position: relative;
}

.shimmer-btn .shimmer-effect {
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
  height: 100%;
  top: 0;
  left: -100%;
}

.sonar-scan {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(232, 121, 249, 0.2);
  animation: sonarPing 3s ease-out infinite;
  pointer-events: none;
}

.isPremiumMode .sonar-scan {
  border-color: rgba(212, 175, 55, 0.2);
}

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
