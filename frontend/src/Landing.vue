<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()

const goToDashboard = () => {
  router.push('/dashboard')
}
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
    <main class="relative z-10 max-w-7xl mx-auto px-8 pt-12 pb-20">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <!-- 左侧：标题与内容 -->
        <div class="text-left">
          <div class="mb-8">
            <h1 class="font-black tracking-tight text-6xl md:text-7xl animate-fade-in-up">
              <span class="block text-white mb-2">重塑你的</span>
              <span class="block mb-2">
                <span class="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400 drop-shadow-lg animate-text-glow">
                  职业发展
                </span>
                <span class="inline-block ml-3">✨</span>
              </span>
              <span class="block text-white">轨迹</span>
            </h1>
          </div>

          <p class="text-gray-400 text-lg md:text-xl leading-relaxed mb-10 max-w-lg animate-fade-in-up animation-delay-200">
            AI 驱动的简历诊断与面试模拟，让你的每一次投递都充满底气，助力你在职场中脱颖而出。
          </p>

          <div class="flex flex-col sm:flex-row gap-4 mb-12 animate-fade-in-up animation-delay-400">
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

        <!-- 右侧：玻璃态悬浮卡片 - 强制高度的父容器 -->
        <div class="relative w-full min-h-[450px] lg:min-h-[500px] animate-fade-in-right animation-delay-500">
          <!-- 卡片1：简历评分 -->
          <div class="glass-card absolute top-0 left-[10%] md:left-[5%] z-10 w-72 p-6 rounded-2xl bg-white/5 backdrop-blur-xl border border-purple-500/30 shadow-xl shadow-purple-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(168,85,247,0.3)] hover:-translate-y-2 animate-float-1">
            <div class="flex items-center gap-4 mb-4">
              <div class="w-16 h-16 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <span class="text-white font-bold text-2xl">95</span>
              </div>
              <div>
                <p class="text-white font-semibold text-lg mb-1">简历评分</p>
                <p class="text-gray-400 text-sm">超越90%候选人</p>
              </div>
            </div>
            <div class="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
              <div class="w-[95%] h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"></div>
            </div>
          </div>

          <!-- 卡片2：面试通过率 -->
          <div class="glass-card absolute top-[130px] right-[5%] md:right-[-5%] z-20 w-64 p-6 rounded-2xl bg-white/5 backdrop-blur-xl border border-cyan-500/30 shadow-xl shadow-cyan-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(34,211,238,0.3)] hover:-translate-y-2 animate-float-2">
            <div class="flex items-center gap-3 mb-2">
              <span class="text-green-400 font-bold text-3xl">+42%</span>
            </div>
            <p class="text-white font-semibold text-lg mb-1">面试通过率</p>
            <p class="text-gray-400 text-xs">AI模拟面试大幅提升通过率</p>
          </div>

          <!-- 卡片3：AI助手 -->
          <div class="glass-card absolute top-[260px] left-[15%] md:left-[10%] z-30 w-60 p-5 rounded-2xl bg-white/5 backdrop-blur-xl border border-pink-500/30 shadow-xl shadow-pink-500/10 transition-all duration-300 hover:shadow-[0_0_40px_rgba(236,72,153,0.3)] hover:-translate-y-2 animate-float-3">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                <span class="text-white text-xs font-bold">AI</span>
              </div>
              <p class="text-white font-medium text-sm">AI 助手</p>
            </div>
            <div class="bg-white/5 rounded-lg p-3">
              <p class="text-gray-300 text-xs">已为您生成5条高频面试题...</p>
            </div>
          </div>
        </div>
      </div>
    </main>
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
.animation-delay-200 { animation-delay: 0.2s; }
.animation-delay-400 { animation-delay: 0.4s; }
.animation-delay-500 { animation-delay: 0.5s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-15px); }
}

@keyframes gradient-flow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.animate-float-1 { animation: float 6s ease-in-out infinite; }
.animate-float-2 { animation: float 7s ease-in-out infinite; animation-delay: -2s; }
.animate-float-3 { animation: float 8s ease-in-out infinite; animation-delay: -4s; }

.animate-text-glow {
  background-size: 200% auto;
  animation: gradient-flow 4s linear infinite;
}
</style>
