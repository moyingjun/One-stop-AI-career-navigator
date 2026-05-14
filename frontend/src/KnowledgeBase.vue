<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Upload, FolderOpen, Loader2, Trash2, FileText, Image, File } from 'lucide-vue-next'
import CyberGlassCard from '@/components/CyberGlassCard.vue'
import { ACCEPTED_EXTENSIONS, validateFile, getFileType } from '@/utils/fileConstants.js'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBaseStore.js'

const router = useRouter()
const store = useKnowledgeBaseStore()

// Icon component map for dynamic rendering
const iconMap = { FileText, Image, File }

// KnowledgeBase 页面专用文件大小限制：10MB
const KB_MAX_FILE_SIZE = 10 * 1024 * 1024

// 后端 API 基础路径
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000/api'
  : '/api'

// Sorted files list (newest first by createdAt)
const sortedFiles = computed(() => {
  return [...store.files].sort((a, b) => b.createdAt - a.createdAt)
})

/**
 * Format file size to human-readable string (KB/MB)
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const isDragging = ref(false)
const fileInputRef = ref(null)

// Error toast state
const errorToast = ref('')
let toastTimer = null

/**
 * 显示错误 toast 提示，3 秒后自动消失
 */
function showError(message) {
  errorToast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    errorToast.value = ''
  }, 3000)
}

function handleDragOver(event) {
  event.preventDefault()
  isDragging.value = true
}

function handleDragLeave(event) {
  event.preventDefault()
  isDragging.value = false
}

/**
 * KnowledgeBase 页面专用文件校验（10MB 限制）
 * @param {File} file
 * @returns {{ valid: boolean, error: string | null }}
 */
function validateKBFile(file) {
  const baseValidation = validateFile(file)
  if (!baseValidation.valid) return baseValidation
  if (file.size > KB_MAX_FILE_SIZE) {
    return { valid: false, error: '文件大小超过限制 (最大 10MB)' }
  }
  return { valid: true, error: null }
}

function handleFileDrop(event) {
  event.preventDefault()
  isDragging.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  for (const file of droppedFiles) {
    const validation = validateKBFile(file)
    if (validation.valid) {
      handleFileUpload(file)
    } else {
      showError(`${file.name}: ${validation.error}`)
    }
  }
}

function handleFileSelect(event) {
  const selectedFiles = Array.from(event.target.files)
  for (const file of selectedFiles) {
    const validation = validateKBFile(file)
    if (validation.valid) {
      handleFileUpload(file)
    } else {
      showError(`${file.name}: ${validation.error}`)
    }
  }
  // Reset input so same file can be re-selected
  event.target.value = ''
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

/**
 * 文件上传核心逻辑 — 调用后端 POST /api/knowledge/upload
 * 1. 校验文件合法性（格式 + 10MB 限制）
 * 2. 创建 FileItem 并加入 Store（status: 'parsing'）
 * 3. 通过 FormData 将文件发送至后端知识库上传接口
 * 4. 成功时更新文件状态为 'completed'，失败时显示错误提示并标记 'failed'
 */
async function handleFileUpload(file) {
  const validation = validateKBFile(file)
  if (!validation.valid) {
    showError(validation.error)
    return
  }

  const fileItem = {
    id: crypto.randomUUID(),
    name: file.name,
    ext: file.name.split('.').pop().toLowerCase(),
    size: file.size,
    status: 'parsing',
    extractedText: '',
    errorMessage: '',
    createdAt: Date.now()
  }
  store.addFile(fileItem)

  try {
    const formData = new FormData()
    formData.append('file', file)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 秒超时

    const response = await fetch(`${API_BASE_URL}/knowledge/upload`, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}))
      const errorMsg = errBody.detail || `上传失败 (HTTP ${response.status})`
      store.updateFileStatus(fileItem.id, 'failed', '', errorMsg)
      showError(`${file.name}: ${errorMsg}`)
      return
    }

    const data = await response.json()
    if (data.success && data.knowledge_id) {
      store.updateFileStatus(fileItem.id, 'completed', '')
    } else {
      const errorMsg = data.message || '上传返回异常'
      store.updateFileStatus(fileItem.id, 'failed', '', errorMsg)
      showError(`${file.name}: ${errorMsg}`)
    }
  } catch (error) {
    const errorMsg = error.name === 'AbortError'
      ? '上传超时，请检查网络后重试'
      : (error.message || '网络错误，请重试')
    store.updateFileStatus(fileItem.id, 'failed', '', errorMsg)
    showError(`${file.name}: ${errorMsg}`)
  }
}
</script>

<template>
  <div class="min-h-[100dvh] bg-[#020205] text-gray-200 relative overflow-hidden">
    <!-- 背景 blur 层 -->
    <div class="absolute inset-0 pointer-events-none">
      <div
        class="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vh] rounded-full bg-purple-600/15 blur-[120px]"
      ></div>
      <div
        class="absolute bottom-[-10%] right-[-5%] w-[45vw] h-[45vh] rounded-full bg-cyan-500/15 blur-[120px]"
      ></div>
    </div>

    <!-- 主内容 -->
    <div class="relative z-10 min-h-[100dvh] flex flex-col">
      <!-- 顶部导航 -->
      <header class="px-4 py-4 md:px-6">
        <div class="max-w-6xl mx-auto flex items-center gap-3">
          <button
            @click="router.push('/dashboard')"
            class="p-2 rounded-lg border border-white/10 hover:bg-white/5 hover:border-cyan-400/30 transition-all duration-300 group"
          >
            <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-cyan-300 transition-colors" />
          </button>
          <div>
            <h1 class="text-lg md:text-xl font-bold text-white">知识库资产管理舱</h1>
            <p class="text-xs text-gray-500">Knowledge Base Asset Manager</p>
          </div>
        </div>
      </header>

      <!-- 主体区域：响应式分栏 -->
      <main class="flex-1 px-4 py-6 md:px-6">
        <div class="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- 左侧：拖拽上传区 -->
          <CyberGlassCard title="文件上传" :icon="Upload" variant="cyan">
            <div
              class="dropzone"
              :class="{ 'dropzone--active': isDragging }"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleFileDrop"
              @click="triggerFileInput"
            >
              <input
                ref="fileInputRef"
                type="file"
                :accept="ACCEPTED_EXTENSIONS"
                multiple
                class="hidden"
                @change="handleFileSelect"
              />
              <div class="flex flex-col items-center justify-center py-10 px-4">
                <div
                  class="w-14 h-14 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 flex items-center justify-center mb-4"
                >
                  <Upload class="w-7 h-7 text-cyan-300" />
                </div>
                <h3 class="text-base font-semibold text-white mb-2">
                  拖拽文件到此处上传
                </h3>
                <p class="text-sm text-gray-500 text-center max-w-xs leading-relaxed">
                  支持文档与图片格式上传（PDF/Word/TXT/JPG/PNG/WEBP）
                </p>
                <span
                  class="mt-5 px-5 py-2 rounded-xl border border-cyan-400/30 bg-cyan-500/10 text-cyan-200 text-sm hover:bg-cyan-500/20 hover:text-white transition-all duration-300 cursor-pointer"
                >
                  点击选择文件
                </span>
              </div>
            </div>
          </CyberGlassCard>

          <!-- 右侧：文件列表区 -->
          <CyberGlassCard title="文件资产列表" :icon="FolderOpen" variant="purple">
            <!-- 空状态 -->
            <div
              v-if="sortedFiles.length === 0"
              class="min-h-[260px] flex flex-col items-center justify-center py-10 px-4"
            >
              <FolderOpen class="w-10 h-10 text-purple-400/50 mb-3" />
              <p class="text-sm text-gray-500 text-center">
                暂无文件，上传后将在此展示文件资产列表
              </p>
            </div>

            <!-- 文件列表 -->
            <div v-else class="min-h-[260px] flex flex-col">
              <div
                v-for="file in sortedFiles"
                :key="file.id"
                class="file-item group flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-b-0 hover:bg-white/[0.02] transition-colors duration-200"
              >
                <!-- 文件类型图标 -->
                <div
                  class="w-9 h-9 rounded-lg border border-white/10 bg-white/5 flex items-center justify-center flex-shrink-0"
                >
                  <component
                    :is="iconMap[getFileType(file.name).icon] || File"
                    class="w-4.5 h-4.5"
                    :class="getFileType(file.name).color"
                  />
                </div>

                <!-- 文件信息 -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-gray-200 truncate">{{ file.name }}</p>
                  <p class="text-xs text-gray-500 mt-0.5">
                    {{ getFileType(file.name).label }} · {{ formatFileSize(file.size) }}
                  </p>
                </div>

                <!-- 解析状态 -->
                <div class="flex items-center gap-1.5 flex-shrink-0">
                  <!-- 解析中 -->
                  <template v-if="file.status === 'parsing'">
                    <Loader2 class="w-3.5 h-3.5 text-purple-400 animate-spin" />
                    <span class="text-xs text-purple-400">解析中</span>
                  </template>
                  <!-- 已完成 -->
                  <template v-else-if="file.status === 'completed'">
                    <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span class="text-xs text-emerald-400">已完成</span>
                  </template>
                  <!-- 失败 -->
                  <template v-else-if="file.status === 'failed'">
                    <span class="w-2 h-2 rounded-full bg-red-400"></span>
                    <span class="text-xs text-red-400" :title="file.errorMessage">失败</span>
                  </template>
                  <!-- 待处理 -->
                  <template v-else>
                    <span class="w-2 h-2 rounded-full bg-gray-500"></span>
                    <span class="text-xs text-gray-500">待处理</span>
                  </template>
                </div>

                <!-- 删除按钮 -->
                <button
                  @click.stop="store.removeFile(file.id)"
                  class="p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 transition-all duration-200"
                  title="删除文件"
                >
                  <Trash2 class="w-3.5 h-3.5 text-gray-500 hover:text-red-400 transition-colors" />
                </button>
              </div>
            </div>
          </CyberGlassCard>
        </div>
      </main>
    </div>

    <!-- Error Toast -->
    <Transition name="toast">
      <div
        v-if="errorToast"
        class="fixed bottom-6 right-6 z-50 max-w-sm px-4 py-3 rounded-xl border border-red-500/40 bg-red-950/80 backdrop-blur-md shadow-lg shadow-red-500/10"
      >
        <p class="text-sm text-red-200">{{ errorToast }}</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dropzone {
  min-height: 260px;
  border: 2px dashed rgba(6, 182, 212, 0.3);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dropzone:hover {
  border-color: rgba(6, 182, 212, 0.6);
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.15), inset 0 0 20px rgba(6, 182, 212, 0.05);
  background: rgba(6, 182, 212, 0.03);
}

.dropzone--active {
  border-color: rgba(168, 85, 247, 0.7);
  box-shadow: 0 0 30px rgba(168, 85, 247, 0.25), 0 0 60px rgba(6, 182, 212, 0.15), inset 0 0 30px rgba(168, 85, 247, 0.08);
  background: rgba(168, 85, 247, 0.06);
}

/* Toast transition */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
