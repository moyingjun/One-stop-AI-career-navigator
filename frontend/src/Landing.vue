<script setup>
import { useRouter } from 'vue-router'
import { ref, onMounted, onUnmounted } from 'vue'

const router = useRouter()

const goToDashboard = () => {
  router.push('/dashboard')
}

// 轮播状态
const currentSlide = ref(0)
let timer = null
// 视频DOM引用
const videoRefs = ref([])
// 视频实际时长：video1=8s, video2=8s, video3=5s, 图层3=6s
// 每个视频总时长减去1秒过渡时间，实现完美淡出
const slideDurations = [7000, 7000, 4000, 6000]

const startTimer = () => {
  // 清除旧定时器
  if (timer) {
    clearTimeout(timer)
  }
  // 启动新定时器
  timer = setTimeout(nextSlide, slideDurations[currentSlide.value])
}

const setSlide = (index) => {
  // 立即切换，不等待过渡
  currentSlide.value = index
  // 重置视频播放进度
  if (index < 3 && videoRefs.value[index]) {
    videoRefs.value[index].currentTime = 0
    videoRefs.value[index].play()
  }
  startTimer()
}

const nextSlide = () => {
  currentSlide.value = (currentSlide.value + 1) % 4
  // 重置视频播放进度
  if (currentSlide.value < 3 && videoRefs.value[currentSlide.value]) {
    videoRefs.value[currentSlide.value].currentTime = 0
    videoRefs.value[currentSlide.value].play()
  }
  startTimer()
}

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

onMounted(() => {
  startTimer()
  playConsoleAnimation()
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <!-- 最外层容器 -->
  <div class="min-h-screen relative z-0 overflow-hidden aurora-bg">
    <!-- 科技网格背景 -->
    <div class="absolute inset-0 bg-grid-pattern opacity-[0.15] z-[-1] pointer-events-none"></div>

    <!-- 导航栏 -->
    <nav class="relative z-10 flex justify-between items-center py-6 px-8 max-w-7xl mx-auto">
      <div class="flex items-center gap-3 cursor-pointer" @click="goToDashboard">
        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
          <span class="text-white font-bold text-sm">AI</span>
        </div>
        <span class="text-white font-semibold text-lg">AI 职业导航</span>
      </div>

      <div class="hidden md:flex items-center gap-8">
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">产品功能</a>
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">工作原理</a>
        <a href="#" class="text-gray-400 hover:text-white transition-colors duration-300">关于我们</a>
      </div>

      <div class="flex items-center gap-4">
        <button class="text-gray-300 hover:text-white transition-colors duration-300 px-4 py-2">
          登录
        </button>
        <button 
          @click="goToDashboard"
          class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-2 rounded-full font-medium hover:shadow-lg hover:shadow-purple-500/40 transition-all duration-300"
        >
          免费开始
        </button>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="relative z-10 max-w-7xl mx-auto px-8 min-h-[calc(100vh-120px)] flex flex-col justify-center">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <!-- 左侧：标题与内容 -->
        <div class="text-left">
          <div class="mb-8">
            <h1 class="font-black tracking-tight text-5xl md:text-6xl leading-tight flex flex-col items-start mb-6">
              <div class="text-white mb-2 overflow-hidden whitespace-nowrap animate-typewriter-1">重塑你的</div>
              <div class="flex items-center overflow-hidden whitespace-nowrap animate-typewriter-2 opacity-0">
                <span class="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400 drop-shadow-lg">
                  职业发展轨迹
                </span>
                <span class="text-4xl ml-2">✨</span>
                <span class="animate-cursor-blink text-purple-400 ml-3 font-light opacity-100">|</span>
              </div>
            </h1>
          </div>

          <p class="text-gray-400 text-lg md:text-xl leading-relaxed mb-10 max-w-lg animate-blur-in-up animation-delay-300">
            AI 驱动的简历诊断与面试模拟，让你的每一次投递都充满底气，助力你在职场中脱颖而出。
          </p>

          <div class="flex flex-col sm:flex-row gap-4 mb-12 animate-blur-in-up animation-delay-400">
            <button 
              @click="goToDashboard"
              class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-10 py-4 rounded-xl font-semibold text-lg shadow-[0_0_30px_rgba(168,85,247,0.4)] hover:shadow-[0_0_40px_rgba(168,85,247,0.6)] transition-all duration-300 hover:-translate-y-0.5"
            >
              免费开始使用
            </button>
            <button class="bg-white/5 backdrop-blur-xl border border-white/10 text-gray-300 px-10 py-4 rounded-xl font-semibold text-lg hover:bg-white/10 transition-all duration-300 hover:-translate-y-0.5">
              查看演示
            </button>
          </div>

          <!-- 信任背书区域 -->
          <div class="mt-12">
            <p class="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-4">TRUSTED BY</p>
            <div class="flex flex-wrap items-center gap-4 md:gap-6 text-sm text-gray-500 font-medium">
              <span>Google</span>
              <span>Microsoft</span>
              <span>Tencent</span>
              <span>Amazon</span>
              <span>Meta</span>
            </div>
          </div>
        </div>

        <!-- 右侧：经典科技设备框 -->
        <div class="relative w-full min-h-[600px] lg:min-h-[650px] animate-fade-in-right animation-delay-500">
          <!-- 主设备外壳 -->
          <div class="absolute inset-0 z-10 animate-float" style="transform: perspective(1000px) rotateY(-5deg);">
            <div class="w-full h-full flex flex-col bg-white/5 backdrop-blur-xl rounded-3xl border border-purple-500/30 shadow-[0_0_60px_rgba(139,92,246,0.25)] overflow-hidden">
              <!-- 顶部边框（带摄像头和切换按钮） -->
              <div class="h-10 bg-white/8 border-b border-white/10 flex items-center justify-between px-6">
                <div class="flex items-center">
                  <div class="w-2.5 h-2.5 rounded-full bg-black/80 shadow-inner mr-4"></div>
                </div>
                <!-- 加大的标签指示器 -->
                <div class="flex items-center gap-3">
                  <button 
                    v-for="(item, index) in 4" 
                    :key="index"
                    @click="setSlide(index)"
                    class="rounded-full transition-all duration-200 hover:scale-110 cursor-pointer"
                    :class="currentSlide === index 
                      ? 'w-8 h-2 bg-purple-500 shadow-sm shadow-purple-500/30 cursor-default' 
                      : 'w-2 h-2 bg-white/30 hover:bg-white/50' 
                    "
                  ></button>
                </div>
                <div class="w-8"></div>
              </div>
              
              <!-- 中间屏幕区（16:9比例） -->
              <div class="flex-1 relative overflow-hidden" style="aspect-ratio: 16/9;">
                <!-- 4图层丝滑轮播 -->
                <div class="absolute inset-0 w-full h-full">
                  <!-- 图层0：AI 大脑 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 0 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[0] = el" src="/video1.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层1：神经核心 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 1 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[1] = el" src="/video2.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层2：数据光缆 -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 2 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <video :ref="el => videoRefs[2] = el" src="/video3.mp4" autoplay loop muted playsinline class="w-full h-full object-cover"></video>
                  </div>

                  <!-- 图层3：现有内容（产品演示视频区 + 毛玻璃卡片） -->
                  <div 
                    class="absolute inset-0 w-full h-full transition-all duration-1000 ease-in-out"
                    :class="currentSlide === 3 ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'"
                  >
                    <div class="w-full h-full bg-gradient-to-br from-purple-900/60 via-indigo-900/60 to-black flex items-center justify-center">
                      <!-- 紫色渐变占位 -->
                      <div class="text-center p-8 animate-pulse">
                        <div class="w-20 h-20 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-500/30 animate-pulse">
                          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 10 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <p class="text-white font-semibold text-lg">产品演示视频区</p>
                        <p class="text-gray-400 text-sm mt-2">demo.mp4 即将上线</p>
                      </div>
                    </div>

                    <!-- 环绕卫星卡片1：简历评分 -->
                    <div class="glass-card absolute bottom-6 left-6 z-30 w-60 p-4 rounded-2xl bg-white/5 backdrop-blur-xl border border-purple-500/30 shadow-xl shadow-purple-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(168,85,247,0.3)] hover:-translate-y-2 animate-float-1">
                      <div class="flex items-center gap-3 mb-3">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                          <span class="text-white font-bold text-lg">95</span>
                        </div>
                        <div>
                          <p class="text-white font-semibold text-sm mb-1">简历评分</p>
                          <p class="text-gray-400 text-xs">超越90%候选人</p>
                        </div>
                      </div>
                      <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div class="w-[95%] h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"></div>
                      </div>
                    </div>

                    <!-- 环绕卫星卡片2：面试通过率 -->
                    <div class="glass-card absolute top-6 right-6 z-30 w-60 p-4 rounded-2xl bg-white/5 backdrop-blur-xl border border-cyan-500/30 shadow-xl shadow-cyan-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(34,211,238,0.3)] hover:-translate-y-2 animate-float-2">
                      <div class="flex items-center gap-3 mb-2">
                        <span class="text-green-400 font-bold text-xl">+42%</span>
                      </div>
                      <p class="text-white font-semibold text-sm mb-1">面试通过率</p>
                      <p class="text-gray-400 text-xs">AI模拟面试大幅提升通过率</p>
                    </div>

                    <!-- 环绕卫星卡片3：AI助手 -->
                    <div class="glass-card absolute bottom-6 right-6 z-30 w-60 p-4 rounded-2xl bg-white/5 backdrop-blur-xl border border-pink-500/30 shadow-xl shadow-pink-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(236,72,153,0.3)] hover:-translate-y-2 animate-float-3 flex flex-col items-start">
                      <div class="flex items-center gap-3 mb-3 w-full">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
                          <span class="text-white font-bold text-lg">AI</span>
                        </div>
                        <div>
                          <p class="text-white font-semibold text-sm mb-1">AI 助手</p>
                          <p class="text-gray-400 text-xs">已为您生成 5 条高频面试题...</p>
                        </div>
                      </div>
                      <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div class="w-[80%] h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 底部边框（带下吧和Home键） -->
              <div class="h-10 bg-white/8 border-t border-white/10 flex items-center justify-center">
                <div class="w-16 h-1.5 rounded-full bg-white/30"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 底部 Footer -->
    <footer class="relative z-10 py-8 text-center text-xs text-gray-600">
      © 2026 Designed & Developed by Moyingjun 广东水利电力职业技术学院
    </footer>
  </div>
</template>

<style scoped>
.glass-card {
  transition: all 0.3s ease;
}

/* 极光流体呼吸背景 */
.aurora-bg {
  background-color: #030014;
  background-image: 
    radial-gradient(ellipse at 20% 0%, rgba(147, 51, 234, 0.25) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(79, 70, 229, 0.25) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(255, 255, 255, 0.05) 0%, transparent 60%);
  background-size: 200% 200%;
  animation: aurora-breathe 15s ease infinite alternate;
}

@keyframes aurora-breathe {
  0% { background-position: 0% 0%; }
  50% { background-position: 100% 100%; opacity: 0.8; }
  100% { background-position: 0% 100%; }
}

/* 科技感网格背景 */
.bg-grid-pattern {
  background-image: linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px),
                    linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* 电影级模糊显现入场动画 */
@keyframes blurInUp {
  from { opacity: 0; transform: translateY(30px); filter: blur(10px); }
  to { opacity: 1; transform: translateY(0); filter: blur(0); }
}

.animate-blur-in-up {
  animation: blurInUp 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

/* 两段式多行打字机 */
@keyframes typing {
  from { max-width: 0; }
  to { max-width: 100%; }
}

@keyframes showNextLine {
  to { opacity: 1; }
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.animate-typewriter-1 {
  display: inline-block;
  max-width: 0;
  /* 1.2s 敲完第一行 */
  animation: typing 1.2s steps(4) forwards;
}

.animate-typewriter-2 {
  display: inline-flex;
  max-width: 0;
  /* 延迟 1.2s 等第一行敲完，再用 1.8s 敲第二行 */
  animation: showNextLine 0.1s 1.2s forwards, typing 1.8s steps(7) 1.2s forwards;
}

.animate-cursor-blink {
  animation: cursorBlink 1s step-end infinite;
}

/* 丝滑入场动画关键帧 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(40px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 入场动画类 */
.animate-fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.animate-fade-in-right {
  animation: fadeInRight 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

/* 动画延迟工具类 */
.animation-delay-300 { animation-delay: 0.3s; }
.animation-delay-400 { animation-delay: 0.4s; }
.animation-delay-500 { animation-delay: 0.5s; }

@keyframes float {
  0%, 100% { transform: translateY(0) perspective(1000px) rotateY(-5deg); }
  50% { transform: translateY(-15px) perspective(1000px) rotateY(-5deg); }
}

@keyframes gradient-flow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animate-float { 
  animation: float 6s ease-in-out infinite; 
}
.animate-float-1 { animation: float 6s ease-in-out infinite; }
.animate-float-2 { animation: float 7s ease-in-out infinite; animation-delay: -2s; }
.animate-float-3 { animation: float 8s ease-in-out infinite; animation-delay: -4s; }

.animate-text-glow {
  background-size: 200% auto;
  animation: gradient-flow 4s linear infinite;
}

/* 粒子动画 */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.5); }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
