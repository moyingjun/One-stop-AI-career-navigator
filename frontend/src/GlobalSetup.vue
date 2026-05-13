<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Terminal, User, FileText, ArrowRight, Upload, Sparkles, Loader2, FileUp, ClipboardPaste } from 'lucide-vue-next'
import { parseFile } from '@/utils/ocrHelper.js'
import { ACCEPTED_EXTENSIONS, validateFile } from '@/utils/fileConstants.js'

const router = useRouter()

const candidate_name = ref('')
const resumeText = ref('')
const uploadedFileName = ref('')
const isParsing = ref(false)
const isSaving = ref(false)
const isLoaded = ref(false)
const dropZoneActive = ref(false)
const error = ref('')
const parseSuccess = ref(false)

const processFile = async (file) => {
  isParsing.value = true
  error.value = ''
  parseSuccess.value = false
  uploadedFileName.value = file.name

  try {
    const text = await parseFile(file)

    if (!text.trim()) {
      throw new Error('文件内容为空，请检查后重试')
    }

    resumeText.value = text
    parseSuccess.value = true
    isParsing.value = false
  } catch (e) {
    error.value = e.message || '文件解析失败，请重试'
    uploadedFileName.value = ''
    isParsing.value = false
    setTimeout(() => { error.value = '' }, 4000)
  }
}

const handleFileDrop = (event) => {
  dropZoneActive.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) processFile(files[0])
}

const handleSave = async () => {
  if (!candidate_name.value.trim()) {
    error.value = '请填写姓名'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }
  if (!resumeText.value.trim() || resumeText.value.trim().length < 20) {
    error.value = '简历内容至少需要 20 个字符'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }

  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 600))

  localStorage.setItem('candidate_name', candidate_name.value.trim())
  localStorage.setItem('resume_text', resumeText.value.trim())

  isSaving.value = false
  router.push('/dashboard')
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && event.ctrlKey) handleSave()
}

onMounted(() => {
  const savedName = localStorage.getItem('candidate_name')
  const savedResume = localStorage.getItem('resume_text')
  if (savedName) candidate_name.value = savedName
  if (savedResume) {
    resumeText.value = savedResume
    uploadedFileName.value = '已加载的简历数据'
    parseSuccess.value = true
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
      <div class="text-center mb-6 md:mb-10">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-purple-500/20 bg-purple-500/5 mb-4">
          <Terminal class="w-4 h-4 text-purple-400" />
          <span class="text-xs text-purple-400/80 font-mono tracking-wider">AI CAREER NAVIGATOR</span>
        </div>
        <h1 class="text-2xl md:text-4xl font-bold bg-gradient-to-r from-purple-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent mb-3">开启你的职业导航</h1>
        <p class="text-sm text-gray-500">输入姓名，上传或粘贴简历，AI 将为你深度解析</p>
      </div>

      <!-- 表单卡片 -->
      <div class="backdrop-blur-xl bg-white/[0.02] border border-white/10 rounded-2xl p-4 md:p-8 shadow-2xl">
        <div class="space-y-4 md:space-y-6">
          <!-- 姓名输入 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <User class="w-4 h-4 text-purple-400" />
              姓名
              <span class="text-red-400">*</span>
            </label>
            <input
              v-model="candidate_name"
              type="text"
              placeholder="请输入你的真实姓名"
              @keydown="handleKeyDown"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 focus:outline-none transition-all duration-300 focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 focus:shadow-[0_0_20px_rgba(168,85,247,0.15)]"
            />
          </div>

          <!-- 简历双模输入卡片 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <FileText class="w-4 h-4 text-fuchsia-400" />
              简历输入
              <span class="text-red-400">*</span>
              <span class="text-xs text-gray-500 ml-1">（支持文档与图片格式上传：PDF/Word/TXT/JPG/PNG/WEBP）</span>
            </label>

            <div class="resume-card relative rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
              <!-- 上半部分：拖拽上传区 -->
              <div
                class="relative upload-zone transition-all duration-300 cursor-pointer group border-b border-white/10"
                :class="{
                  'bg-purple-500/10 border-dashed': !dropZoneActive && !parseSuccess,
                  'bg-purple-500/15 border-dashed border-purple-400/40': dropZoneActive,
                  'bg-green-500/5 border-solid': parseSuccess
                }"
                @dragover.prevent="dropZoneActive = true"
                @dragleave.prevent="dropZoneActive = false"
                @drop.prevent="dropZoneActive = false; handleFileDrop($event)"
                @click="$refs.fileInput?.click()"
              >
                <input
                  ref="fileInput"
                  type="file"
                  class="hidden"
                  :accept="ACCEPTED_EXTENSIONS"
                  @change="handleFileSelect"
                />

                <!-- 拖拽区内容 -->
                <div class="flex items-center gap-4 px-4 py-4 md:px-6 md:py-5">
                  <div class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300"
                    :class="parseSuccess ? 'bg-green-500/20' : dropZoneActive ? 'bg-purple-500/20 scale-110' : 'bg-white/5 group-hover:bg-purple-500/10'"
                  >
                    <FileUp v-if="!parseSuccess" class="w-5 h-5 transition-all duration-300"
                      :class="dropZoneActive ? 'text-purple-400' : 'text-gray-500 group-hover:text-purple-400'"
                    />
                    <Sparkles v-else class="w-5 h-5 text-green-400 animate-pulse" />
                  </div>

                  <div class="flex-1">
                    <template v-if="!parseSuccess">
                      <p class="text-gray-300 text-sm font-medium">拖拽简历文档到此处，或点击上传</p>
                      <p class="text-gray-600 text-xs mt-0.5">支持文档与图片格式上传（PDF/Word/TXT/JPG/PNG/WEBP）</p>
                    </template>
                    <template v-else>
                      <div class="flex items-center gap-2">
                        <FileText class="w-4 h-4 text-green-400" />
                        <span class="text-green-300 text-sm font-medium truncate max-w-[280px]">{{ uploadedFileName }}</span>
                        <span class="text-xs text-gray-500">解析完成，可编辑下方内容</span>
                      </div>
                    </template>
                  </div>

                  <div v-if="isParsing" class="flex items-center gap-2 text-purple-300">
                    <Loader2 class="w-5 h-5 animate-spin" />
                    <span class="text-xs">解析中...</span>
                  </div>
                </div>

                <!-- 拖拽激活态光晕 -->
                <div v-if="dropZoneActive" class="absolute inset-0 pointer-events-none bg-gradient-to-r from-purple-500/10 via-fuchsia-500/10 to-pink-500/10 animate-pulse"></div>
              </div>

              <!-- 分隔线装饰 -->
              <div class="flex items-center gap-3 px-4 py-2 md:px-6 bg-black/20">
                <div class="h-px flex-1 bg-gradient-to-r from-purple-500/20 to-transparent"></div>
                <ClipboardPaste class="w-3.5 h-3.5 text-gray-500" />
                <span class="text-[10px] text-gray-500 font-mono tracking-wider">TEXT INPUT</span>
                <div class="h-px flex-1 bg-gradient-to-l from-fuchsia-500/20 to-transparent"></div>
              </div>

              <!-- 下半部分：文本编辑区 -->
              <div class="px-4 pb-4">
                <textarea
                  v-model="resumeText"
                  rows="8"
                  @keydown="handleKeyDown"
                  placeholder="或者直接在此处粘贴您的简历纯文本..."
                  class="w-full px-4 py-3 rounded-xl border-2 bg-black/40 text-gray-100 placeholder-gray-600 resize-none focus:outline-none transition-all duration-300 focus:border-purple-500/50 focus:ring-2 focus:ring-fuchsia-500/20 focus:shadow-[0_0_20px_rgba(236,72,153,0.1)] text-base leading-relaxed"
                  :class="resumeText.trim().length >= 20 ? 'border-fuchsia-500/20' : resumeText.trim() ? 'border-red-500/20' : 'border-purple-500/10'"
                ></textarea>

                <!-- 字数提示 -->
                <div class="flex items-center justify-between mt-2 px-1">
                  <span class="text-xs" :class="resumeText.trim().length >= 20 ? 'text-green-400/70' : resumeText.trim() ? 'text-red-400/70' : 'text-gray-600'">
                    {{ resumeText.trim().length >= 20 ? '✓ 字数达标' : resumeText.trim() ? `还需 ${20 - resumeText.trim().length} 字` : '至少 20 字' }}
                  </span>
                  <button
                    v-if="resumeText"
                    @click="resumeText = ''; uploadedFileName = ''; parseSuccess = false"
                    class="text-xs text-gray-500 hover:text-red-400 transition-colors duration-200"
                  >
                    清空内容
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 提交按钮 -->
        <button
          @click="handleSave"
          :disabled="!candidate_name.trim() || resumeText.trim().length < 20 || isSaving"
          class="shimmer-btn w-full mt-4 md:mt-8 py-4 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2.5 overflow-hidden relative bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/50"
        >
          <span class="absolute inset-0 shimmer-effect pointer-events-none"></span>
          <Loader2 v-if="isSaving" class="w-4 h-4 animate-spin relative z-10" />
          <ArrowRight v-else class="w-4 h-4 relative z-10" />
          <span class="relative z-10">{{ isSaving ? '保存中...' : '开启航程' }}</span>
        </button>

        <p class="text-center text-xs text-gray-600 mt-4">快捷键：Ctrl + Enter 保存</p>
      </div>

      <!-- 错误提示 -->
      <transition name="fade">
        <div v-if="error" class="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-400 text-center">
          {{ error }}
        </div>
      </transition>

      <!-- 底部装饰 -->
      <div class="flex items-center justify-center gap-4 mt-4 md:mt-8">
        <div class="h-px flex-1 bg-gradient-to-r from-transparent to-purple-500/20"></div>
        <div class="w-1.5 h-1.5 rounded-full bg-purple-500/30"></div>
        <div class="h-px flex-1 bg-gradient-to-l from-transparent to-pink-500/20"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes blob1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(100px, -50px) scale(1.1); }
  50% { transform: translate(-30px, 80px) scale(0.9); }
  75% { transform: translate(-80px, -30px) scale(1.05); }
}

@keyframes blob2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(-120px, 60px) scale(1.05); }
  50% { transform: translate(50px, -70px) scale(0.95); }
  75% { transform: translate(70px, 40px) scale(1.1); }
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.shimmer-btn { position: relative; }

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

.resume-card {
  position: relative;
  transition: all 0.3s ease;
}

.resume-card:focus-within {
  border-color: rgba(168, 85, 247, 0.3);
  box-shadow: 0 0 30px rgba(168, 85, 247, 0.1);
}

.upload-zone {
  position: relative;
}

textarea::-webkit-scrollbar { width: 6px; }
textarea::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); border-radius: 3px; }
textarea::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
textarea::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }

input::-webkit-search-decoration,
input::-webkit-search-cancel-button,
input::-webkit-search-results-button,
input::-webkit-search-results-decoration { display: none; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>