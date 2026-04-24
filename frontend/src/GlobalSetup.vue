<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Terminal, User, Target, FileText, ArrowRight, Sparkles } from 'lucide-vue-next'

const router = useRouter()

const name = ref('')
const targetRole = ref('')
const resumeText = ref('')
const isSaving = ref(false)
const isLoaded = ref(false)

const handleSave = async () => {
  if (!name.value.trim() || !targetRole.value.trim() || !resumeText.value.trim()) {
    return
  }

  isSaving.value = true

  await new Promise(resolve => setTimeout(resolve, 800))

  localStorage.setItem('candidate_name', name.value.trim())
  localStorage.setItem('target_role', targetRole.value.trim())
  localStorage.setItem('resume_text', resumeText.value.trim())

  isSaving.value = false
  router.push('/dashboard')
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && event.ctrlKey) {
    handleSave()
  }
}

onMounted(() => {
  const savedName = localStorage.getItem('candidate_name')
  const savedRole = localStorage.getItem('target_role')
  const savedResume = localStorage.getItem('resume_text')

  if (savedName) name.value = savedName
  if (savedRole) targetRole.value = savedRole
  if (savedResume) resumeText.value = savedResume

  setTimeout(() => { isLoaded.value = true }, 100)
})
</script>

<template>
  <div class="min-h-screen relative flex items-center justify-center overflow-hidden bg-[#050505]">
    <!-- 动态网格背景 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute inset-0" style="background-image: linear-gradient(rgba(168, 85, 247, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(168, 85, 247, 0.06) 1px, transparent 1px); background-size: 40px 40px;"></div>
      <div class="absolute inset-0" style="background: radial-gradient(ellipse at center, transparent 0%, #050505 75%);"></div>
    </div>

    <!-- 游动光球 -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute w-[500px] h-[500px] rounded-full blur-[120px] bg-purple-600/10 animate-[blob1_20s_ease-in-out_infinite]" style="top: 10%; left: 15%;"></div>
      <div class="absolute w-[400px] h-[400px] rounded-full blur-[100px] bg-fuchsia-600/10 animate-[blob2_25s_ease-in-out_infinite]" style="top: 60%; right: 10%;"></div>
    </div>

    <!-- 主表单容器 -->
    <div class="relative z-10 w-full max-w-2xl mx-4 transition-all duration-700" :class="isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'">
      <!-- 标题区 -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-purple-500/20 bg-purple-500/5 mb-4">
          <Terminal class="w-4 h-4 text-purple-400" />
          <span class="text-xs text-purple-400/80 font-mono tracking-wider">AI CAREER NAVIGATOR</span>
        </div>
        <h1 class="text-4xl font-bold bg-gradient-to-r from-purple-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent mb-3">全局信息录入</h1>
        <p class="text-sm text-gray-500">填写你的基本信息，开启 AI 职业导航之旅</p>
      </div>

      <!-- 表单卡片 -->
      <div class="backdrop-blur-xl bg-white/[0.02] border border-white/10 rounded-2xl p-8 shadow-2xl">
        <div class="space-y-6">
          <!-- 姓名输入 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <User class="w-4 h-4 text-purple-400" />
              姓名
              <span class="text-red-400">*</span>
            </label>
            <input
              v-model="name"
              type="text"
              placeholder="请输入你的真实姓名"
              @keydown="handleKeyDown"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 focus:outline-none transition-all duration-300 focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 focus:shadow-[0_0_20px_rgba(168,85,247,0.15)]"
            />
          </div>

          <!-- 目标岗位输入 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <Target class="w-4 h-4 text-fuchsia-400" />
              目标岗位 / JD
              <span class="text-red-400">*</span>
            </label>
            <input
              v-model="targetRole"
              type="text"
              placeholder="例如：高级前端开发工程师 / 技术专家"
              @keydown="handleKeyDown"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 focus:outline-none transition-all duration-300 focus:border-fuchsia-500/50 focus:ring-2 focus:ring-fuchsia-500/20 focus:shadow-[0_0_20px_rgba(232,121,249,0.15)]"
            />
          </div>

          <!-- 简历内容输入 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <FileText class="w-4 h-4 text-pink-400" />
              完整简历内容
              <span class="text-red-400">*</span>
            </label>
            <textarea
              v-model="resumeText"
              placeholder="请粘贴你的完整简历内容..."
              rows="10"
              @keydown="handleKeyDown"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 resize-none focus:outline-none transition-all duration-300 focus:border-pink-500/50 focus:ring-2 focus:ring-pink-500/20 focus:shadow-[0_0_20px_rgba(236,72,153,0.15)]"
            ></textarea>
          </div>
        </div>

        <!-- 提交按钮 -->
        <button
          @click="handleSave"
          :disabled="!name.trim() || !targetRole.trim() || !resumeText.trim() || isSaving"
          class="shimmer-btn w-full mt-8 py-4 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/50"
        >
          <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
          <Sparkles v-if="isSaving" class="w-4 h-4 animate-spin relative z-10" />
          <ArrowRight v-else class="w-4 h-4 relative z-10" />
          <span class="relative z-10">{{ isSaving ? '保存中...' : '保存并开启导航' }}</span>
        </button>

        <!-- 快捷键提示 -->
        <p class="text-center text-xs text-gray-600 mt-4">快捷键：Ctrl + Enter 保存</p>
      </div>

      <!-- 底部装饰 -->
      <div class="flex items-center justify-center gap-4 mt-8">
        <div class="h-px flex-1 bg-gradient-to-r from-transparent to-purple-500/20"></div>
        <div class="w-1.5 h-1.5 rounded-full bg-purple-500/30"></div>
        <div class="h-px flex-1 bg-gradient-to-l from-transparent to-pink-500/20"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes blob1 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(100px, -50px) scale(1.1);
  }
  50% {
    transform: translate(-30px, 80px) scale(0.9);
  }
  75% {
    transform: translate(-80px, -30px) scale(1.05);
  }
}

@keyframes blob2 {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(-120px, 60px) scale(1.05);
  }
  50% {
    transform: translate(50px, -70px) scale(0.95);
  }
  75% {
    transform: translate(70px, 40px) scale(1.1);
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

input::-webkit-search-decoration,
input::-webkit-search-cancel-button,
input::-webkit-search-results-button,
input::-webkit-search-results-decoration {
  display: none;
}
</style>
