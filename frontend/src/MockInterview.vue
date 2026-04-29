<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Clipboard, Sparkles, Check, ExternalLink, UserCircle } from 'lucide-vue-next'

const router = useRouter()
const showPanel = ref(true)
const copied = ref(false)
const promptText = ref('')
const popupBlocked = ref(false)

const TENCENT_ADP_URL = 'https://adp.cloud.tencent.com/webim_exp/#/chat/yuGvvl'

const generatePrompt = () => {
  const resume = localStorage.getItem('resume_text') || ''
  const jd = localStorage.getItem('jd_content') || localStorage.getItem('jd_text') || ''
  return `考官你好，我是候选人。以下是我的简历：\n${resume || '（暂无简历内容，请在输入框中粘贴）'}\n目标岗位JD：\n${jd || '（暂无岗位描述）'}\n请直接基于此开始第一轮技术面试，直接提问。`
}

const copyAndNotify = () => {
  promptText.value = generatePrompt()
  navigator.clipboard.writeText(promptText.value).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 6000)
  })
}

const openInterviewWindow = () => {
  const url = TENCENT_ADP_URL
  
  try {
    const newWin = window.open(url, 'InterviewWindow', 'width=1200,height=800,menubar=no,toolbar=no,location=no,status=no')
    
    if (!newWin || newWin.closed || typeof newWin.closed === 'undefined') {
      popupBlocked.value = true
    } else {
      popupBlocked.value = false
    }
  } catch (error) {
    console.error('弹窗打开失败:', error)
    popupBlocked.value = true
  }
}

const handlePopupFallback = () => {
  if (confirm('检测到弹窗被拦截，请在浏览器地址栏右侧允许弹窗，或点击确定直接跳转。')) {
    window.open(TENCENT_ADP_URL, '_blank')
    popupBlocked.value = false
  }
}

onMounted(() => {
  promptText.value = generatePrompt()
})
</script>

<template>
  <div class="min-h-screen bg-[#050510] relative flex flex-col overflow-hidden">
    <!-- 背景光效 -->
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-600/8 rounded-full blur-[200px] animate-pulse"></div>
      <div class="absolute bottom-0 right-0 w-[600px] h-[600px] bg-cyan-600/5 rounded-full blur-[150px]"></div>
    </div>

    <!-- 顶部导航栏 -->
    <nav class="flex items-center justify-between px-4 py-3 md:px-6 md:py-3 border-b border-white/5 bg-[#050510]/60 backdrop-blur-xl z-30 relative" style="height: 64px;">
      <button
        @click="router.push('/dashboard')"
        class="flex items-center gap-2 text-gray-400 hover:text-white transition-colors duration-300 group"
      >
        <ArrowLeft class="w-5 h-5 group-hover:-translate-x-1 transition-transform duration-300" />
        <span class="text-sm">返回工作台</span>
      </button>
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-gradient-to-r from-pink-500 to-rose-600 flex items-center justify-center shadow-lg shadow-pink-500/30">
          <Sparkles class="w-4 h-4 text-white" />
        </div>
        <h1 class="text-lg font-bold text-white">AI 模拟面试</h1>
      </div>
      <div class="w-24"></div>
    </nav>

    <!-- 主内容区 -->
    <div class="flex-1 relative z-10 flex items-center justify-center">
      <!-- 数字人剪影 -->
      <div class="flex flex-col items-center gap-6 md:gap-8 px-4">
        <!-- 头像外圈 -->
        <div class="relative">
          <!-- 外圈波纹 -->
          <div class="absolute inset-0 -m-8 rounded-full border border-purple-500/10 animate-ping" style="animation-duration: 3s;"></div>
          <div class="absolute inset-0 -m-16 rounded-full border border-pink-500/5 animate-ping" style="animation-duration: 4.5s;"></div>
          <!-- 剪影 -->
          <div class="w-40 h-40 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-2 border-purple-500/30 flex items-center justify-center backdrop-blur-sm shadow-2xl shadow-purple-500/10">
            <UserCircle class="w-24 h-24 text-purple-400/60" />
          </div>
          <!-- 中心光点 -->
          <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_20px_rgba(34,211,238,0.8)]"></div>
        </div>

        <!-- 唤醒按钮 -->
        <button
          @click="openInterviewWindow"
          class="group bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-8 py-4 md:px-10 md:py-5 rounded-2xl font-bold text-base md:text-lg shadow-xl shadow-purple-500/30 hover:shadow-2xl hover:shadow-purple-500/40 transition-all duration-500 hover:-translate-y-1 active:scale-95 flex items-center gap-3"
        >
          <ExternalLink class="w-5 h-5 group-hover:rotate-12 transition-transform duration-300" />
          唤醒数字人面试官
        </button>

        <p class="text-gray-500 text-sm">点击后将打开独立的面试窗口</p>

        <div v-if="popupBlocked" class="mt-4 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 flex items-start gap-3 animate-fade-in-up">
          <div class="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
            <span class="text-xl">⚠️</span>
          </div>
          <div class="flex-1 text-left">
            <p class="text-sm text-amber-300 font-semibold">弹窗被拦截，请点击此处手动开启</p>
            <p class="text-xs text-amber-400/70 mt-1 mb-2">浏览器已阻止弹出窗口，请选择以下方式之一继续</p>
            <div class="flex flex-wrap gap-2">
              <button
                @click="handlePopupFallback"
                class="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg text-xs text-amber-300 font-medium transition-all duration-300 hover:-translate-y-0.5"
              >
                🔓 确定直接跳转
              </button>
              <a
                :href="TENCENT_ADP_URL"
                target="_blank"
                class="px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/40 rounded-lg text-xs text-purple-300 font-medium transition-all duration-300 hover:-translate-y-0.5 flex items-center gap-1"
              >
                <ExternalLink class="w-3 h-3" />
                在新标签页打开
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 浮动简历助手面板 -->
    <div
      v-if="showPanel"
      class="absolute md:right-4 md:top-20 right-4 bottom-20 md:bottom-auto w-[calc(100%-2rem)] md:w-80 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl shadow-purple-500/10 overflow-hidden"
    >
      <!-- 面板头部 -->
      <div class="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
          <span class="text-sm font-semibold text-gray-300">简历助手</span>
        </div>
        <button @click="showPanel = false" class="text-gray-500 hover:text-white transition-colors text-lg leading-none w-6 h-6 flex items-center justify-center rounded-full hover:bg-white/10">&times;</button>
      </div>

      <!-- 面板内容 -->
      <div class="p-4">
        <!-- 引导步骤 -->
        <div class="mb-4 bg-white/5 rounded-xl p-3 border border-white/5">
          <p class="text-xs text-gray-300 leading-relaxed mb-2 font-medium">操作步骤：</p>
          <ol class="text-[11px] text-gray-400 leading-relaxed space-y-1 list-decimal list-inside">
            <li>点击上方按钮唤醒面试官</li>
            <li>面试官就绪后，在弹出窗口中<span class="text-purple-400 font-semibold">【粘贴并发送】</span></li>
            <li>开启你的高压面试</li>
          </ol>
        </div>

        <button
          @click="copyAndNotify"
          :disabled="copied"
          class="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-xl font-semibold text-sm shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40 transition-all duration-300 hover:-translate-y-0.5 disabled:shadow-green-500/20 flex items-center justify-center gap-2 group"
          :class="copied ? '!from-green-600 !to-emerald-600' : ''"
        >
          <Clipboard v-if="!copied" class="w-4 h-4" />
          <Check v-else class="w-4 h-4" />
          {{ copied ? '已复制' : '复制简历指令 (准备投喂)' }}
        </button>

        <!-- 成功提示气泡 -->
        <div v-if="copied" class="mt-3 bg-green-500/10 border border-green-500/20 rounded-xl p-3 animate-fade-in-up">
          <p class="text-xs text-green-400 leading-relaxed">
            已复制！请在弹出窗口中 <span class="font-bold text-green-300 bg-green-500/20 px-1.5 py-0.5 rounded">【粘贴并发送】</span>，即可开启专家级面试。
          </p>
        </div>

        <!-- 预览区域 -->
        <div class="mt-3 bg-white/5 rounded-xl p-3 max-h-24 overflow-y-auto border border-white/5">
          <p class="text-[10px] text-gray-500 mb-1">预览指令：</p>
          <p class="text-[11px] text-gray-400 leading-relaxed whitespace-pre-wrap line-clamp-3">{{ promptText }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in-up {
  animation: fade-in-up 0.3s ease-out;
}
</style>
