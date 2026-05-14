<script setup>
import { ref, onMounted } from 'vue'
import { X, User, FileText, FileUp, ClipboardPaste, Sparkles, Loader2 } from 'lucide-vue-next'
import { parseFile } from '@/utils/ocrHelper.js'
import { ACCEPTED_EXTENSIONS, validateFile } from '@/utils/fileConstants.js'
import { useUserStore } from '@/stores/userStore.js'

const userStore = useUserStore()

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

// Tab 切换状态
const activeTab = ref('job')  // 'job' | 'education'

// 求职模式字段
const targetJob = ref('')
const jobDescription = ref('')
const targetJobError = ref('')
const jobDescriptionError = ref('')

// 升学模式字段
const examType = ref('')
const estimatedScore = ref('')
const targetSchool = ref('')
const targetGoal = ref('')
const examTypeError = ref('')
const estimatedScoreError = ref('')
const targetSchoolError = ref('')

// 考试类型选项
const examTypeOptions = [
  { value: 'zhuanchaben', label: '专插本' },
  { value: 'gaokao', label: '普通高考' },
  { value: 'kaoyan', label: '考研' },
  { value: 'kaogong', label: '考公' },
  { value: 'other', label: '其他' }
]

// 表单提交处理
const handleSubmit = () => {
  // 清除之前的错误
  nameError.value = ''
  resumeError.value = ''
  targetJobError.value = ''
  jobDescriptionError.value = ''
  examTypeError.value = ''
  estimatedScoreError.value = ''
  targetSchoolError.value = ''

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
  } else if (resumeText.value.length > 10000) {
    resumeError.value = '简历内容不能超过 10000 个字符'
    hasError = true
  }

  // 模式特定字段验证
  if (activeTab.value === 'job') {
    if (jobDescription.value.length > 5000) {
      jobDescriptionError.value = 'JD 不能超过 5000 字符'
      hasError = true
    }
  }
  // 升学模式：所有字段可选，无必填验证

  if (hasError) return

  // 验证通过，写入 localStorage（用 try-catch 包裹，隐私模式或存储已满时静默失败）
  try {
    localStorage.setItem('candidate_name', trimmedName.slice(0, 50))
    localStorage.setItem('resume_text', trimmedResume.slice(0, 10000))
    localStorage.setItem('userRole', 'registered')
    localStorage.setItem('active_mode', activeTab.value)

    if (activeTab.value === 'job') {
      // 求职模式：写入目标岗位和 JD
      localStorage.setItem('target_job', targetJob.value.trim())
      localStorage.setItem('job_description', jobDescription.value.trim())
    } else if (activeTab.value === 'education') {
      // 升学模式：写入考试类型、预估分数、意向院校
      localStorage.setItem('exam_type', examType.value)
      localStorage.setItem('estimated_score', estimatedScore.value.trim())
      localStorage.setItem('target_school', targetSchool.value.trim())
      // target_goal 独立写入，与 target_school 互不干扰
      try {
        localStorage.setItem('target_goal', targetGoal.value.trim())
      } catch {
        // target_goal 写入失败时静默处理，不影响其他字段保存
      }
    }
  } catch {
    // localStorage 写入失败（隐私模式/存储已满）时静默处理，不阻断后续 Store 更新
  }

  // 同步所有字段到 Pinia Store（单一数据源）
  userStore.updateUserProfile({
    candidateName: trimmedName.slice(0, 50),
    resumeText: trimmedResume.slice(0, 10000),
    activeMode: activeTab.value,
    targetJob: targetJob.value.trim(),
    jobDescription: jobDescription.value.trim(),
    examType: examType.value,
    estimatedScore: estimatedScore.value.trim(),
    targetSchool: targetSchool.value.trim(),
    targetGoal: targetGoal.value.trim()
  })

  // 通知父组件完成
  emit('complete')
}

// 文件处理逻辑
const processFile = async (file) => {
  error.value = ''
  parseSuccess.value = false

  // 文件大小和格式校验（Requirements 8.6, 8.7）
  const validation = validateFile(file)
  if (!validation.valid) {
    error.value = validation.error
    setTimeout(() => { error.value = '' }, 4000)
    return
  }

  isParsing.value = true
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

  // 预填充模式相关字段
  activeTab.value = localStorage.getItem('active_mode') || 'job'
  targetJob.value = localStorage.getItem('target_job') || ''
  jobDescription.value = localStorage.getItem('job_description') || ''
  examType.value = localStorage.getItem('exam_type') || ''
  estimatedScore.value = localStorage.getItem('estimated_score') || ''
  targetSchool.value = localStorage.getItem('target_school') || ''
  // target_goal 独立读取，渲染错误时降级处理，不影响其他字段
  try {
    targetGoal.value = localStorage.getItem('target_goal') || ''
  } catch {
    targetGoal.value = ''
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
                      <p class="text-gray-500 text-xs mt-0.5">支持文档与图片格式上传</p>
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
                <span class="text-xs text-gray-500 font-mono tracking-wider">TEXT INPUT</span>
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
                  <span class="text-xs" :class="resumeText.trim().length >= 20 ? 'text-green-400/70' : resumeText.trim() ? 'text-red-400/70' : 'text-gray-500'">
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

        <!-- 模式切换 Tab -->
        <div class="mt-4 mb-3">
          <label class="block text-sm text-gray-400 mb-2">选择模式</label>
          <div class="flex gap-2 p-1 rounded-lg bg-white/5 backdrop-blur-sm border border-white/10">
            <button
              type="button"
              @click="activeTab = 'job'"
              :class="[
                'flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200',
                activeTab === 'job'
                  ? 'bg-purple-500/20 text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.3)] border border-purple-500/30'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
              ]"
            >
              💼 求职模式
            </button>
            <button
              type="button"
              @click="activeTab = 'education'"
              :class="[
                'flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200',
                activeTab === 'education'
                  ? 'bg-purple-500/20 text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.3)] border border-purple-500/30'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
              ]"
            >
              🎓 升学模式
            </button>
          </div>
        </div>

        <!-- 求职模式字段 -->
        <div v-if="activeTab === 'job'" class="space-y-3">
          <div>
            <label class="block text-sm text-gray-400 mb-1">目标岗位</label>
            <input
              v-model="targetJob"
              type="text"
              maxlength="100"
              placeholder="如：前端工程师、产品经理..."
              class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all"
            />
            <p v-if="targetJobError" class="mt-1 text-xs text-red-400">{{ targetJobError }}</p>
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">岗位描述 JD</label>
            <textarea
              v-model="jobDescription"
              maxlength="5000"
              rows="3"
              placeholder="粘贴目标岗位的职位描述..."
              class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all resize-none"
            ></textarea>
            <p v-if="jobDescriptionError" class="mt-1 text-xs text-red-400">{{ jobDescriptionError }}</p>
          </div>
        </div>

        <!-- 升学模式字段 -->
        <div v-else class="space-y-3">
          <div>
            <label class="block text-sm text-gray-400 mb-1">考试类型</label>
            <select
              v-model="examType"
              class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all"
            >
              <option value="" disabled class="bg-gray-900">请选择考试类型</option>
              <option v-for="opt in examTypeOptions" :key="opt.value" :value="opt.value" class="bg-gray-900">
                {{ opt.label }}
              </option>
            </select>
            <p v-if="examTypeError" class="mt-1 text-xs text-red-400">{{ examTypeError }}</p>
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">预估分数/排位</label>
            <input
              v-model="estimatedScore"
              type="text"
              maxlength="50"
              placeholder="如：550分、前10%..."
              class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all"
            />
            <p v-if="estimatedScoreError" class="mt-1 text-xs text-red-400">{{ estimatedScoreError }}</p>
          </div>
          <!-- 两栏布局：意向院校 + 目标志愿/目标 -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm text-gray-400 mb-1">意向院校</label>
              <input
                v-model="targetSchool"
                type="text"
                maxlength="200"
                placeholder="如：华南理工大学..."
                class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all"
              />
              <p v-if="targetSchoolError" class="mt-1 text-xs text-red-400">{{ targetSchoolError }}</p>
            </div>
            <div>
              <label class="block text-sm text-gray-400 mb-1">目标志愿/目标</label>
              <input
                v-model="targetGoal"
                type="text"
                maxlength="200"
                placeholder="如：计算机科学与技术专业..."
                class="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:border-purple-500/50 focus:outline-none focus:ring-1 focus:ring-purple-500/30 transition-all"
              />
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
