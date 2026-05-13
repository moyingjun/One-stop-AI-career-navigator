<script setup>
import { ref, onMounted } from 'vue'
import { X, User, FileText, FileUp, ClipboardPaste, Sparkles, Loader2 } from 'lucide-vue-next'
import { parseFile } from '@/utils/ocrHelper.js'
import { ACCEPTED_EXTENSIONS } from '@/utils/fileConstants.js'

const emit = defineEmits(['close', 'complete'])

const candidateName = ref('')
const resumeText = ref('')
const uploadedFileName = ref('')
const isParsing = ref(false)
const parseSuccess = ref(false)
const dropZoneActive = ref(false)
const error = ref('')

// 表单验证错误状态
const nameError = ref('')
const resumeError = ref('')

// 表单提交处理
const handleSubmit = () => {
  // 清除之前的错误
  nameError.value = ''
  resumeError.value = ''

  let hasError = false

  // 验证姓名
  const trimmedName = candidateName.value.trim()
  if (!trimmedName) {
    nameError.value = '请填写姓名'
    hasError = true
  } else if (trimmedName.length > 50) {
    nameError.value = '姓名不能超过 50 个字符'
    hasError = true
  }

  // 验证简历
  const trimmedResume = resumeText.value.trim()
  if (trimmedResume.length < 20) {
    resumeError.value = '简历内容至少需要 20 个字符'
    hasError = true
  }

  if (hasError) return

  // 验证通过，写入 localStorage
  localStorage.setItem('candidate_name', trimmedName.slice(0, 50))
  localStorage.setItem('resume_text', trimmedResume.slice(0, 10000))
  localStorage.setItem('userRole', 'registered')

  // 通知父组件完成
  emit('complete')
}

// 文件处理逻辑
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
  } catch (e) {
    error.value = e.message || '文件解析失败，请重试'
    uploadedFileName.value = ''
    setTimeout(() => { error.value = '' }, 4000)
  } finally {
    isParsing.value = false
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

// mounted 时从 localStorage 预填充
onMounted(() => {
  const savedName = localStorage.getItem('candidate_name')
  const savedResume = localStorage.getItem('resume_text')
  if (savedName) candidateName.value = savedName
  if (savedResume) {
    resumeText.value = savedResume
    uploadedFileName.value = '已加载的简历数据'
    parseSuccess.value = true
  }
})
</script>

<template>
  <!-- 遮罩层 -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
    <!-- 弹窗内容区 - CyberGlassCard 风格 -->
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl backdrop-blur-xl bg-white/[0.02] border border-white/10 shadow-2xl">
      <!-- 关闭按钮 -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-lg border border-white/10 bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all duration-200"
        aria-label="关闭"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- 表单内容 -->
      <div class="p-6 md:p-8">
        <!-- 标题 -->
        <div class="text-center mb-6">
          <h2 class="text-xl md:text-2xl font-bold bg-gradient-to-r from-purple-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent">
            完善个人信息
          </h2>
          <p class="text-sm text-gray-500 mt-2">填写姓名并上传简历，解锁完整 AI 分析能力</p>
        </div>

        <div class="space-y-4 md:space-y-6">
          <!-- 姓名输入 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <User class="w-4 h-4 text-purple-400" />
              姓名
              <span class="text-red-400">*</span>
            </label>
            <input
              v-model="candidateName"
              type="text"
              placeholder="请输入你的真实姓名"
              class="w-full px-4 py-3 rounded-xl border bg-black/40 text-gray-100 placeholder-gray-600 focus:outline-none transition-all duration-300 focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 focus:shadow-[0_0_20px_rgba(168,85,247,0.15)]"
              :class="nameError ? 'border-red-500/50' : 'border-white/10'"
              @input="nameError = ''"
            />
            <!-- 姓名验证错误提示 -->
            <p v-if="nameError" class="text-xs text-red-400 mt-1 pl-1">{{ nameError }}</p>
          </div>

          <!-- 简历双模输入卡片 -->
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm font-medium text-gray-300">
              <FileText class="w-4 h-4 text-fuchsia-400" />
              简历输入
              <span class="text-red-400">*</span>
              <span class="text-xs text-gray-500 ml-1">（支持 PDF/Word/TXT/JPG/PNG/WEBP）</span>
            </label>

            <div class="relative rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
              <!-- 上半部分：拖拽上传区 -->
              <div
                class="relative transition-all duration-300 cursor-pointer group border-b border-white/10"
                :class="{
                  'bg-purple-500/10': !dropZoneActive && !parseSuccess,
                  'bg-purple-500/15': dropZoneActive,
                  'bg-green-500/5': parseSuccess
                }"
                @dragover.prevent="dropZoneActive = true"
                @dragleave.prevent="dropZoneActive = false"
                @drop.prevent="handleFileDrop($event)"
                @click="$refs.fileInput?.click()"
              >
                <input
                  ref="fileInput"
                  type="file"
                  class="hidden"
                  :accept="ACCEPTED_EXTENSIONS"
                  @change="handleFileSelect"
                />

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
                      <p class="text-gray-600 text-xs mt-0.5">支持文档与图片格式上传</p>
                    </template>
                    <template v-else>
                      <div class="flex items-center gap-2">
                        <FileText class="w-4 h-4 text-green-400" />
                        <span class="text-green-300 text-sm font-medium truncate max-w-[240px]">{{ uploadedFileName }}</span>
                        <span class="text-xs text-gray-500">解析完成</span>
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
                  rows="6"
                  placeholder="或者直接在此处粘贴您的简历纯文本..."
                  class="w-full px-4 py-3 rounded-xl border-2 bg-black/40 text-gray-100 placeholder-gray-600 resize-none focus:outline-none transition-all duration-300 focus:border-purple-500/50 focus:ring-2 focus:ring-fuchsia-500/20 focus:shadow-[0_0_20px_rgba(236,72,153,0.1)] text-sm leading-relaxed"
                  :class="resumeError ? 'border-red-500/30' : resumeText.trim().length >= 20 ? 'border-fuchsia-500/20' : resumeText.trim() ? 'border-red-500/20' : 'border-purple-500/10'"
                  @input="resumeError = ''"
                ></textarea>

                <!-- 字数提示 -->
                <div class="flex items-center justify-between mt-2 px-1">
                  <span class="text-xs" :class="resumeText.trim().length >= 20 ? 'text-green-400/70' : resumeText.trim() ? 'text-red-400/70' : 'text-gray-600'">
                    {{ resumeText.trim().length >= 20 ? '✓ 字数达标' : resumeText.trim() ? `还需 ${20 - resumeText.trim().length} 字` : '至少 20 字' }}
                  </span>
                  <button
                    v-if="resumeText"
                    @click.stop="resumeText = ''; uploadedFileName = ''; parseSuccess = false"
                    class="text-xs text-gray-500 hover:text-red-400 transition-colors duration-200"
                  >
                    清空内容
                  </button>
                </div>
                <!-- 简历验证错误提示 -->
                <p v-if="resumeError" class="text-xs text-red-400 mt-1 pl-1">{{ resumeError }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误提示 -->
        <transition name="fade">
          <div v-if="error" class="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-400 text-center">
            {{ error }}
          </div>
        </transition>

        <!-- 提交按钮 -->
        <button
          @click="handleSubmit"
          class="w-full mt-6 py-3 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
        >
          完成设置
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
textarea::-webkit-scrollbar { width: 5px; }
textarea::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); border-radius: 3px; }
textarea::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
textarea::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
