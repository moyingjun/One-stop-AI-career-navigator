<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Terminal, User, FileText, ArrowRight, Upload, Sparkles, Loader2 } from 'lucide-vue-next'

const router = useRouter()

const name = ref('')
const resumeText = ref('')
const uploadedFileName = ref('')
const isParsing = ref(false)
const isSaving = ref(false)
const isLoaded = ref(false)
const isDragging = ref(false)
const dropZoneActive = ref(false)
const error = ref('')

const handleFileDrop = (event) => {
  isDragging.value = false
  dropZoneActive.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) processFile(files[0])
}

const processFile = (file) => {
  isParsing.value = true
  error.value = ''
  uploadedFileName.value = file.name

  if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
    const reader = new FileReader()
    reader.onload = (e) => {
      resumeText.value = e.target.result || ''
      isParsing.value = false
    }
    reader.onerror = () => {
      error.value = '文件读取失败，请重试'
      isParsing.value = false
    }
    reader.readAsText(file)
  } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
    error.value = 'PDF 文件需要后端解析服务，请先使用 TXT 文本格式'
    isParsing.value = false
    setTimeout(() => { error.value = '' }, 4000)
  } else {
    error.value = '目前仅支持 TXT 格式的简历文件'
    isParsing.value = false
    setTimeout(() => { error.value = '' }, 4000)
  }
}

const handleSave = async () => {
  if (!name.value.trim() || !resumeText.value.trim()) {
    error.value = '请填写姓名并上传简历'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }

  isSaving.value = true

  await new Promise(resolve => setTimeout(resolve, 600))

  localStorage.setItem('candidate_name', name.value.trim())
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
  const savedResume = localStorage.getItem('resume_text')

  if (savedName) name.value = savedName
  if (savedResume) {
    resumeText.value = savedResume
    uploadedFileName.value = '已加载的简历数据'
  }

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
    <div class="relative z-10 w-full max-w-3xl mx-4 transition-all duration-700" :class="isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'">
      <!-- 标题区 -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-purple-500/20 bg-purple-500/5 mb-4">
          <Terminal class="w-4 h-4 text-purple-400" />
          <span class="text-xs text-purple-400/80 font-mono tracking-wider">AI CAREER NAVIGATOR</span>
        </div>
        <h1 class="text-4xl font-bold bg-gradient-to-r from-purple-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent mb-3">开启你的职业导航</h1>
        <p class="text-sm text-gray-500">输入姓名，上传简历，AI 将为你深度解析</p>
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

          <!-- 巨大拖拽上传区 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <FileText class="w-4 h-4 text-fuchsia-400" />
              简历上传
              <span class="text-red-400">*</span>
            </label>
            <div
              class="relative min-h-[240px] rounded-2xl border-2 border-dashed transition-all duration-500 cursor-pointer group overflow-hidden"
              :class="{
                'border-purple-500/60 bg-purple-500/10 shadow-[0_0_40px_rgba(168,85,247,0.2)]': dropZoneActive || uploadedFileName,
                'border-white/10 bg-white/[0.02] hover:border-purple-500/30 hover:bg-purple-500/5': !dropZoneActive && !uploadedFileName
              }"
              @dragover.prevent="dropZoneActive = true; isDragging = true"
              @dragleave.prevent="dropZoneActive = false; isDragging = false"
              @drop.prevent="handleFileDrop"
              @click="$refs.fileInput?.click()"
            >
              <!-- 光晕背景 -->
              <div class="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-fuchsia-500/5 pointer-events-none"></div>
              
              <!-- 隐藏的文件输入框 -->
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept=".txt,.pdf"
                @change="handleFileSelect"
              />

              <!-- 上传提示内容 -->
              <div class="relative z-10 flex flex-col items-center justify-center h-full py-8">
                <!-- 上传图标 -->
                <div 
                  class="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-all duration-500"
                  :class="dropZoneActive 
                    ? 'bg-purple-500/20 scale-110' 
                    : 'bg-white/5 group-hover:bg-purple-500/10 group-hover:scale-105'"
                >
                  <Upload 
                    class="w-7 h-7 transition-all duration-300" 
                    :class="dropZoneActive ? 'text-purple-400' : 'text-gray-500 group-hover:text-purple-400'" 
                  />
                </div>

                <!-- 文字提示 -->
                <template v-if="!uploadedFileName">
                  <p class="text-gray-300 text-sm font-medium mb-1">
                    拖拽简历文件到此处
                  </p>
                  <p class="text-gray-600 text-xs">
                    或点击上传 · 支持 TXT 格式
                  </p>
                </template>

                <!-- 已加载文件提示 -->
                <template v-else>
                  <div class="flex items-center gap-3 bg-purple-500/10 border border-purple-500/30 rounded-xl px-4 py-2">
                    <FileText class="w-4 h-4 text-purple-400" />
                    <span class="text-purple-200 text-sm truncate max-w-[200px]">{{ uploadedFileName }}</span>
                    <Sparkles class="w-3 h-3 text-green-400 animate-pulse" />
                  </div>
                  <p class="text-gray-500 text-xs mt-3">点击可重新上传</p>
                </template>
              </div>

              <!-- 解析加载动画 -->
              <div 
                v-if="isParsing" 
                class="absolute inset-0 z-20 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center"
              >
                <Loader2 class="w-8 h-8 text-purple-400 animate-spin mb-3" />
                <p class="text-purple-300 text-sm">正在解析文件...</p>
              </div>
            </div>
          </div>

          <!-- 简历内容预览（可编辑） -->
          <div v-if="resumeText" class="space-y-2">
            <label class="flex items-center gap-2 text-xs font-medium text-gray-500">
              <FileText class="w-3 h-3" />
              简历内容预览（可编辑）
            </label>
            <textarea
              v-model="resumeText"
              rows="6"
              @keydown="handleKeyDown"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 resize-none focus:outline-none transition-all duration-300 focus:border-fuchsia-500/50 focus:ring-2 focus:ring-fuchsia-500/20 text-sm leading-relaxed"
            ></textarea>
          </div>
        </div>

        <!-- 提交按钮 -->
        <button
          @click="handleSave"
          :disabled="!name.trim() || !resumeText.trim() || isSaving"
          class="shimmer-btn w-full mt-8 py-4 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/50"
        >
          <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
          <Loader2 v-if="isSaving" class="w-4 h-4 animate-spin relative z-10" />
          <ArrowRight v-else class="w-4 h-4 relative z-10" />
          <span class="relative z-10">{{ isSaving ? '保存中...' : '开启航程' }}</span>
        </button>

        <!-- 快捷键提示 -->
        <p class="text-center text-xs text-gray-600 mt-4">快捷键：Ctrl + Enter 保存</p>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-400 text-center">
        {{ error }}
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
