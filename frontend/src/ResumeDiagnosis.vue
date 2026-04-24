<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { FileText, ArrowLeft, Paperclip, Sparkles, Bot, Loader2 } from 'lucide-vue-next'

const router = useRouter()

const resumeText = ref('')
const jdText = ref('')
const diagnosisResult = ref('')
const displayedResult = ref('')
const isDiagnosing = ref(false)
const isComplete = ref(false)
const error = ref('')
const uploadedFileName = ref('')
const isDragging = ref(false)
const dropZoneActive = ref(false)

let typewriterTimer = null
let typewriterIndex = 0

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
  uploadedFileName.value = file.name
  if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
    const reader = new FileReader()
    reader.onload = (e) => { resumeText.value = e.target.result || '' }
    reader.readAsText(file)
  } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
    error.value = 'PDF 文件需要后端解析服务，请先粘贴 TXT 文本内容'
    setTimeout(() => { error.value = '' }, 3000)
  } else {
    error.value = '目前仅支持 TXT 格式的简历文件'
    setTimeout(() => { error.value = '' }, 3000)
  }
}

const startTypewriter = () => {
  const fullText = diagnosisResult.value
  typewriterIndex = 0
  displayedResult.value = ''

  const typeNext = () => {
    if (typewriterIndex < fullText.length) {
      displayedResult.value += fullText[typewriterIndex]
      typewriterIndex++
      typewriterTimer = setTimeout(typeNext, 15 + Math.random() * 20)
    } else {
      isComplete.value = true
    }
  }
  typeNext()
}

const startDiagnosis = async () => {
  if (!resumeText.value.trim()) {
    error.value = '请先粘贴简历内容或上传简历文件'
    setTimeout(() => { error.value = '' }, 3000)
    return
  }

  isDiagnosing.value = true
  isComplete.value = false
  diagnosisResult.value = ''
  displayedResult.value = ''
  error.value = ''

  try {
    const response = await fetch('/api/resume/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: resumeText.value,
        jd_text: jdText.value
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `请求失败 (HTTP ${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const data = line.substring(5).trim()
          if (data) {
            try {
              const parsed = JSON.parse(data)
              if (parsed.type === 'error') {
                error.value = '腾讯云 API 报错：请求参数错误'
                console.error('腾讯云 API 错误:', parsed)
                isDiagnosing.value = false
                return
              }
              if (parsed.type === 'reply' && parsed.payload) {
                const content = parsed.payload.content || ''
                if (content) diagnosisResult.value += content
              } else {
                const content = parsed.content || parsed.answer || parsed.text || parsed.message || parsed.delta || ''
                if (content) diagnosisResult.value += content
              }
            } catch {
              if (data) diagnosisResult.value += data
            }
          }
        } else if (line.trim() && !line.startsWith('event:') && !line.startsWith('id:')) {
          diagnosisResult.value += line
        }
      }
    }

    if (diagnosisResult.value) startTypewriter()
  } catch (err) {
    console.error('诊断请求失败:', err)
    if (err.message.includes('Failed to fetch')) {
      error.value = '无法连接到后端 (http://127.0.0.1:8000)，请确认 FastAPI 服务已启动'
    } else {
      error.value = `诊断失败: ${err.message}`
    }
    setTimeout(() => { error.value = '' }, 8000)
  } finally {
    isDiagnosing.value = false
  }
}

onUnmounted(() => {
  if (typewriterTimer) clearTimeout(typewriterTimer)
})
</script>

<template>
  <div class="min-h-screen bg-[#0a0a0f] relative flex">
    <!-- 左侧侧边栏（与 Dashboard 风格一致） -->
    <div class="w-64 fixed h-full z-20">
      <div class="bg-white/5 backdrop-blur-xl border-r border-white/10 rounded-3xl m-4 h-[calc(100vh-2rem)] shadow-xl shadow-purple-500/5 flex flex-col">
        <!-- Logo -->
        <div class="p-3 border-b border-white/10 pl-4 cursor-pointer" @click="router.push('/')">
          <div class="flex items-center gap-3 text-left">
            <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/20">
              <span class="text-white text-sm font-bold">AI</span>
            </div>
            <div class="flex flex-col">
              <h1 class="text-xl font-bold text-white leading-tight">AI 职业导航</h1>
              <p class="text-xs text-gray-500 leading-tight mt-0.5">智能助手</p>
            </div>
          </div>
        </div>

        <!-- 返回按钮 -->
        <div class="p-4">
          <button
            @click="router.push('/dashboard')"
            class="w-full bg-white/10 hover:bg-white/15 text-white py-2 px-4 rounded-full transition-all duration-300 flex items-center justify-center gap-2 border border-white/10 hover:border-purple-500/50 group"
          >
            <ArrowLeft class="w-5 h-5 group-hover:-translate-x-1 transition-transform duration-300" />
            <span>返回工作台</span>
          </button>
        </div>

        <!-- 菜单 -->
        <div class="p-4 flex-1">
          <div class="mb-6">
            <h2 class="text-xs text-gray-500 uppercase mb-2 font-semibold text-left pl-2">简历诊断</h2>
            <div class="flex items-center gap-3 py-1.5 px-2 rounded-lg bg-white/10 text-white">
              <FileText class="w-5 h-5 text-purple-400" />
              <span class="text-sm">深度分析</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧主工作区 -->
    <div class="ml-64 flex-1 flex flex-col h-screen">
      <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl m-4 flex-1 shadow-xl shadow-purple-500/5 overflow-hidden flex flex-col">
        <!-- 顶栏 -->
        <div class="top-bar p-4 border-b border-white/10 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-indigo-600 flex items-center justify-center">
              <Sparkles class="w-4 h-4 text-white" />
            </div>
            <h1 class="text-lg font-bold text-white">AI 简历诊断</h1>
          </div>
          <div class="flex items-center gap-2 text-xs text-gray-500">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></div>
            <span class="text-green-400 font-mono">DeepSeek-V3 Active</span>
          </div>
        </div>

        <!-- 主内容区 -->
        <div class="main-content flex-1 overflow-y-auto relative flex flex-col">
          <!-- 背景环境光 -->
          <div class="absolute top-0 left-10 w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none z-0"></div>
          <div class="absolute bottom-20 right-10 w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[150px] pointer-events-none z-0"></div>

          <div class="max-w-6xl mx-auto w-full flex-1 flex flex-col justify-center pb-24 relative z-10 px-8">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <!-- 左侧：输入区 -->
              <div class="space-y-6">
                <!-- 文件上传区（照抄 Dashboard 风格） -->
                <div
                  class="upload-zone relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 cursor-pointer transition-all duration-300"
                  :class="{ 'border-purple-500/50 bg-purple-500/5': dropZoneActive }"
                  @dragover.prevent="dropZoneActive = true; isDragging = true"
                  @dragleave.prevent="dropZoneActive = false; isDragging = false"
                  @drop.prevent="handleFileDrop"
                >
                  <input
                    type="file"
                    ref="fileInput"
                    class="hidden"
                    accept=".txt,.pdf"
                    @change="handleFileSelect"
                  />
                  <div class="flex items-center gap-4">
                    <div
                      class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300"
                      :class="dropZoneActive ? 'bg-purple-500/20' : 'bg-white/5'"
                    >
                      <Paperclip class="w-5 h-5" :class="dropZoneActive ? 'text-purple-400' : 'text-gray-500'" />
                    </div>
                    <div class="flex-1 text-left">
                      <p class="text-sm text-gray-300">
                        <span class="text-purple-400 cursor-pointer font-medium" @click="$refs.fileInput.click()">点击上传</span>
                        <span class="text-gray-500"> 或拖拽文件到此处</span>
                      </p>
                      <p class="text-xs text-gray-600 mt-1">支持 TXT、PDF 格式</p>
                    </div>
                  </div>
                  <p v-if="uploadedFileName" class="mt-3 text-xs text-purple-400 flex items-center gap-1">
                    <FileText class="w-3 h-3" />
                    已加载：{{ uploadedFileName }}
                  </p>
                </div>

                <!-- 简历内容输入 -->
                <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
                  <label class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 block">
                    简历内容
                  </label>
                  <textarea
                    v-model="resumeText"
                    rows="8"
                    placeholder="在此粘贴你的简历内容..."
                    class="w-full bg-[#151520]/60 border border-white/10 rounded-xl p-4 text-sm text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                  ></textarea>
                </div>

                <!-- JD 输入 -->
                <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
                  <label class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 block">
                    岗位描述 (可选)
                  </label>
                  <textarea
                    v-model="jdText"
                    rows="5"
                    placeholder="粘贴目标岗位的 JD..."
                    class="w-full bg-[#151520]/60 border border-white/10 rounded-xl p-4 text-sm text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                  ></textarea>
                </div>

                <!-- 开始诊断按钮 -->
                <button
                  @click="startDiagnosis"
                  :disabled="isDiagnosing || !resumeText.trim()"
                  class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-4 rounded-2xl font-semibold text-lg shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40 transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 flex items-center justify-center gap-3"
                >
                  <Loader2 v-if="isDiagnosing" class="w-5 h-5 animate-spin" />
                  <Sparkles v-else class="w-5 h-5" />
                  {{ isDiagnosing ? 'AI 正在深度分析中...' : '开始深度诊断' }}
                </button>

                <!-- 错误提示 -->
                <div v-if="error" class="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-400 text-center">
                  {{ error }}
                </div>
              </div>

              <!-- 右侧：结果展示区 -->
              <div class="bg-[#151520]/60 backdrop-blur-2xl border border-white/5 rounded-3xl overflow-hidden flex flex-col min-h-[500px]">
                <!-- 标题栏 -->
                <div class="px-6 py-4 border-b border-white/10 flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <Bot class="w-5 h-5 text-purple-400" />
                    <h2 class="text-sm font-semibold text-gray-300">诊断报告</h2>
                  </div>
                  <div v-if="isComplete" class="flex items-center gap-2">
                    <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span class="text-xs text-green-400">分析完成</span>
                  </div>
                  <div v-else-if="isDiagnosing" class="flex items-center gap-2">
                    <Loader2 class="w-3 h-3 animate-spin text-purple-400" />
                    <span class="text-xs text-purple-400">正在接收数据...</span>
                  </div>
                </div>

                <!-- 内容区 -->
                <div class="flex-1 p-6 overflow-y-auto">
                  <div v-if="displayedResult">
                    <pre class="whitespace-pre-wrap text-sm leading-relaxed text-gray-300 font-sans">{{ displayedResult }}<span class="inline-block w-2 h-4 bg-purple-500 animate-pulse ml-1"></span></pre>
                  </div>

                  <div v-else-if="isDiagnosing" class="flex flex-col items-center justify-center h-full text-center">
                    <div class="w-16 h-16 rounded-full bg-purple-500/10 flex items-center justify-center mb-4 animate-pulse">
                      <Loader2 class="w-8 h-8 text-purple-400 animate-spin" />
                    </div>
                    <p class="text-gray-400 text-sm">AI 正在解析你的简历</p>
                    <p class="text-gray-600 text-xs mt-2">这可能需要 30-60 秒</p>
                  </div>

                  <div v-else class="flex flex-col items-center justify-center h-full text-center">
                    <div class="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                      <FileText class="w-8 h-8 text-gray-600" />
                    </div>
                    <p class="text-gray-500 text-sm">粘贴简历后点击"开始深度诊断"</p>
                    <p class="text-gray-600 text-xs mt-2">AI 将为你提供详细的优化建议</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
textarea::-webkit-scrollbar {
  width: 6px;
}

textarea::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}

textarea::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.upload-zone {
  transition: all 0.3s ease;
}
</style>
