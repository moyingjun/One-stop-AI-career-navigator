<template>
  <div class="hero-section relative min-h-screen flex items-center overflow-hidden bg-[#050505]">
    <!-- 背景极光效果 -->
    <div class="absolute inset-0 overflow-hidden">
      <!-- 左侧紫红光晕 -->
      <div class="absolute -left-1/4 -top-1/4 w-1/2 h-1/2 bg-purple-600/30 rounded-full blur-[120px]"></div>
      <!-- 右侧深蓝光晕 -->
      <div class="absolute -right-1/4 -bottom-1/4 w-1/2 h-1/2 bg-indigo-600/30 rounded-full blur-[120px]"></div>
    </div>

    <!-- 主内容容器 -->
    <div class="container relative z-10 max-w-7xl mx-auto px-6 py-20">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <!-- 左侧：文案与行动呼吁 -->
        <div class="text-left">
          <!-- 主标题 -->
          <h1 class="text-5xl md:text-7xl font-extrabold mb-6 leading-tight">
            重塑你的
            <span class="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400">
              职业发展轨迹
            </span>
          </h1>
          
          <!-- 副标题 -->
          <p class="text-gray-400 text-lg md:text-xl mb-8 leading-relaxed">
            AI 驱动的简历诊断与面试模拟，让你的每一次投递都充满底气。
          </p>
          
          <!-- 操作按钮区 -->
          <div class="flex flex-col sm:flex-row gap-4">
            <!-- 主按钮 -->
            <button class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:shadow-lg hover:shadow-purple-500/30 transition-all duration-300 hover:-translate-y-1">
              免费开始使用
            </button>
            <!-- 次按钮 -->
            <button class="bg-white/5 backdrop-blur-xl border border-white/10 text-gray-300 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white/10 transition-all duration-300 hover:-translate-y-1">
              查看演示
            </button>
          </div>
        </div>

        <!-- 右侧：悬浮玻璃卡片群 -->
        <div class="relative h-[400px] flex items-center justify-center">
          <!-- 卡片 1：简历评分 -->
          <div class="glass-card absolute w-72 h-80 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-6 shadow-lg z-20 hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300">
            <h3 class="text-white font-semibold text-lg mb-4">简历评分</h3>
            <div class="flex items-center justify-center mb-4">
              <!-- 环形进度条 -->
              <div class="relative w-32 h-32">
                <svg class="w-full h-full" viewBox="0 0 100 100">
                  <!-- 背景圆环 -->
                  <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
                  <!-- 进度圆环 -->
                  <circle cx="50" cy="50" r="45" fill="none" stroke="url(#gradient)" stroke-width="8" stroke-linecap="round" stroke-dasharray="283" stroke-dashoffset="14"/>
                  <!-- 渐变定义 -->
                  <defs>
                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#a855f7"/>
                      <stop offset="100%" stop-color="#4f46e5"/>
                    </linearGradient>
                  </defs>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-4xl font-bold text-white">95</span>
                </div>
              </div>
            </div>
            <p class="text-green-400 text-sm text-center">超越 90% 候选人</p>
          </div>

          <!-- 卡片 2：AI 对话框 -->
          <div class="glass-card absolute w-64 h-64 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 shadow-lg z-10 -top-10 -right-10 hover:shadow-xl hover:shadow-indigo-500/10 transition-all duration-300">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center">
                <span class="text-white text-xs font-bold">AI</span>
              </div>
              <h4 class="text-white font-medium">AI 助手</h4>
            </div>
            <div class="bg-white/10 rounded-lg p-4">
              <p class="text-gray-300 text-sm">已为您生成 5 条面试高频问题</p>
            </div>
            <div class="mt-4 flex justify-end">
              <button class="text-purple-400 text-sm hover:text-purple-300 transition-colors duration-300">
                查看详情 →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 自定义样式 */
.hero-section {
  background-color: #050505;
}

/* 玻璃卡片通用样式 */
.glass-card {
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-5px);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .glass-card {
    position: relative !important;
    top: 0 !important;
    right: 0 !important;
    margin: 0 auto;
  }
  
  .hero-section {
    min-height: auto;
    padding: 100px 0;
  }
}
</style>