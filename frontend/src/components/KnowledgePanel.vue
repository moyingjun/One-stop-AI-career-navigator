<script setup>
/**
 * KnowledgePanel.vue — 知识库资产背包（赛博朋克悬浮面板）
 *
 * 功能：
 *   - 拖拽 / 点击上传 PDF、DOCX、TXT 文件
 *   - 沉浸式 Embedding Loading 动画
 *   - 上传成功后自动刷新文件列表
 *   - 每条记录提供红色删除按钮
 *
 * Props：
 *   - modelValue (Boolean) — 控制面板显示/隐藏（v-model）
 *
 * Emits：
 *   - update:modelValue — 关闭面板时触发
 */

import { ref, watch, onMounted } from 'vue'
import { X, Upload, FolderOpen, Loader2, Trash2, FileText, File, Zap } from 'lucide-vue-next'
import { uploadFile, getKnowledgeList, deleteKnowledgeSource } from '@/services/kbService'

// ─────────────────────────────────────────────
// Props & Emits
// ─────────────────────────────────────────────
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

// ─────────────────────────────────────────────
// 状态
// ─────────────────────────────────────────────
const isDragging = ref(false)
const isUploading = ref(false)
const isLoadingList = ref(false)
const fileInputRef = ref(null)
const knowledgeSources = ref([])   // { source_name, chunk_count }
const uploadingFileName = ref('')  // 当前正在上传的文件名（用于 Loading 提示）
const toast = ref({ show: false, message: '', type: 'error' })
let toastTimer = null

// ─────────────────────────────────────────────
// 面板打开时自动加载列表
// ─────────────────────────────────────────────
watch(() => props.modelValue, (visible) => {
  if (visible) fetchList()
})

// ─────────────────────────────────────────────
// Toast 工具
// ─────────────────────────────────────────────
function showToast(message, type = 'error') {
  toast.value = { show: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 3500)
}

// ─────────────────────────────────────────────
// 获取知识库列表
// ─────────────────────────────────────────────
async function fetchList() {
  isLoadingList.value = true
  try {
    const data = await getKnowledgeList()
    knowledgeSources.value = data.sources || []
  } catch (err) {
    showToast(err.message || '获取列表失败', 'error')
  } finally {
    isLoadingList.value = false
  }
}

// ─────────────────────────────────────────────
// 文件校验
// ─────────────────────────────────────────────
const ALLOWED_EXTS = ['.pdf', '.docx', '.doc', '.txt', '.md']
const MAX_SIZE_MB = 20

function validateKBFile(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ALLOWED_EXTS.includes(ext)) {
    return { valid: false, error: `不支持的格式，请上传 PDF / Word / TXT / MD` }
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return { valid: false, error: `文件超过 ${MAX_SIZE_MB}MB 限制` }
  }
  return { valid: true, error: null }
}

// ─────────────────────────────────────────────
// 拖拽事件
// ─────────────────────────────────────────────
function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave(e) {
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  processFiles(files)
}

function onFileSelect(e) {
  const files = Array.from(e.target.files)
  processFiles(files)
  e.target.value = ''
}

function triggerInput() {
  if (!isUploading.value) fileInputRef.value?.click()
}

// ─────────────────────────────────────────────
// 文件处理（逐个上传）
// ─────────────────────────────────────────────
async function processFiles(files) {
  for (const file of files) {
    const { valid, error } = validateKBFile(file)
    if (!valid) {
      showToast(`${file.name}：${error}`, 'error')
      continue
    }
    await doUpload(file)
  }
}

async function doUpload(file) {
  isUploading.value = true
  uploadingFileName.value = file.name

  try {
    await uploadFile(file)
    showToast(`「${file.name}」已成功入库`, 'success')
    // 上传成功后立刻刷新列表
    await fetchList()
  } catch (err) {
    showToast(`${file.name}：${err.message || '上传失败'}`, 'error')
  } finally {
    isUploading.value = false
    uploadingFileName.value = ''
  }
}

// ─────────────────────────────────────────────
// 删除来源
// ─────────────────────────────────────────────
async function handleDelete(sourceName) {
  try {
    await deleteKnowledgeSource(sourceName)
    showToast(`已删除「${sourceName}」`, 'success')
    await fetchList()
  } catch (err) {
    showToast(err.message || '删除失败', 'error')
  }
}

// ─────────────────────────────────────────────
// 关闭面板
// ─────────────────────────────────────────────
function close() {
  emit('update:modelValue', false)
}

// ─────────────────────────────────────────────
// 工具：截断长文件名
// ─────────────────────────────────────────────
function truncateName(name, max = 28) {
  if (name.length <= max) return name
  const ext = name.includes('.') ? '.' + name.split('.').pop() : ''
  return name.slice(0, max - ext.length - 3) + '...' + ext
}
</script>

<template>
  <!-- 遮罩层 -->
  <Transition name="overlay">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
      @click.self="close"
    />
  </Transition>

  <!-- 悬浮面板 -->
  <Transition name="panel">
    <div
      v-if="modelValue"
      class="knowledge-panel fixed right-0 top-0 bottom-0 z-50 w-full max-w-md flex flex-col"
      role="dialog"
      aria-label="知识库资产背包"
    >
      <!-- 面板头部 -->
      <div class="panel-header flex items-center justify-between px-5 py-4 border-b border-white/10">
        <div class="flex items-center gap-2.5">
          <div class="icon-badge">
            <Zap class="w-4 h-4 text-cyan-300" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-white tracking-wide">知识库资产背包</h2>
            <p class="text-[11px] text-gray-500 mt-0.5">Knowledge Asset Panel</p>
          </div>
        </div>
        <button
          @click="close"
          class="close-btn p-1.5 rounded-lg border border-white/10 hover:border-red-500/40 hover:bg-red-500/10 transition-all duration-200"
          aria-label="关闭面板"
        >
          <X class="w-4 h-4 text-gray-400 hover:text-red-400 transition-colors" />
        </button>
      </div>

      <!-- 面板主体 -->
      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-5 scrollbar-thin">

        <!-- ── 上传区 ── -->
        <section>
          <p class="section-label">上传文件</p>

          <!-- Embedding Loading 状态 -->
          <div v-if="isUploading" class="loading-zone">
            <div class="loading-orb">
              <Loader2 class="w-6 h-6 text-cyan-300 animate-spin" />
            </div>
            <div class="text-center">
              <p class="text-sm font-medium text-cyan-200 mb-1">
                AI 正在拆解并理解您的背景资料...
              </p>
              <p class="text-xs text-gray-500 truncate max-w-[240px]">
                {{ uploadingFileName }}
              </p>
              <div class="scan-line mt-3" />
            </div>
          </div>

          <!-- 拖拽上传区 -->
          <div
            v-else
            class="dropzone"
            :class="{ 'dropzone--active': isDragging }"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
            @click="triggerInput"
            role="button"
            tabindex="0"
            @keydown.enter="triggerInput"
            aria-label="点击或拖拽上传文件"
          >
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md"
              multiple
              class="hidden"
              @change="onFileSelect"
            />
            <div class="flex flex-col items-center py-7 px-4">
              <div class="upload-icon-wrap mb-3">
                <Upload class="w-6 h-6 text-cyan-300" />
              </div>
              <p class="text-sm font-medium text-white mb-1">拖拽文件到此处</p>
              <p class="text-xs text-gray-500 text-center leading-relaxed">
                支持 PDF · Word · TXT · MD<br />单文件最大 {{ MAX_SIZE_MB }}MB
              </p>
              <span class="upload-btn mt-4">点击选择文件</span>
            </div>
          </div>
        </section>

        <!-- ── 文件列表 ── -->
        <section>
          <div class="flex items-center justify-between mb-2.5">
            <p class="section-label mb-0">已入库文件</p>
            <span v-if="knowledgeSources.length > 0" class="text-[11px] text-gray-600">
              {{ knowledgeSources.length }} 个来源
            </span>
          </div>

          <!-- 加载中 -->
          <div v-if="isLoadingList" class="flex items-center justify-center py-8 gap-2">
            <Loader2 class="w-4 h-4 text-purple-400 animate-spin" />
            <span class="text-xs text-gray-500">加载中...</span>
          </div>

          <!-- 空状态 -->
          <div
            v-else-if="knowledgeSources.length === 0"
            class="empty-state"
          >
            <FolderOpen class="w-8 h-8 text-purple-400/40 mb-2" />
            <p class="text-xs text-gray-600 text-center">
              暂无文件，上传后 AI 将自动学习您的背景资料
            </p>
          </div>

          <!-- 文件列表 -->
          <div v-else class="space-y-1.5">
            <div
              v-for="source in knowledgeSources"
              :key="source.source_name"
              class="file-row group"
            >
              <!-- 文件图标 -->
              <div class="file-icon-wrap">
                <FileText class="w-3.5 h-3.5 text-cyan-400" />
              </div>

              <!-- 文件信息 -->
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-200 truncate" :title="source.source_name">
                  {{ truncateName(source.source_name) }}
                </p>
                <p class="text-[11px] text-gray-600 mt-0.5">
                  {{ source.chunk_count }} 个检索片段
                </p>
              </div>

              <!-- 删除按钮 -->
              <button
                @click="handleDelete(source.source_name)"
                class="delete-btn opacity-0 group-hover:opacity-100"
                :title="`删除「${source.source_name}」`"
                aria-label="删除此文件"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </section>

        <!-- ── 说明文字 ── -->
        <section class="hint-block">
          <p class="text-[11px] text-gray-600 leading-relaxed">
            💡 上传的文件将自动向量化入库，AI 在对话时会优先参考您的私有资料，
            与系统知识库共同为您提供精准解答。
          </p>
        </section>
      </div>

      <!-- Toast 提示 -->
      <Transition name="toast">
        <div
          v-if="toast.show"
          class="absolute bottom-5 left-4 right-4 px-4 py-3 rounded-xl border backdrop-blur-md text-sm"
          :class="toast.type === 'success'
            ? 'border-emerald-500/40 bg-emerald-950/80 text-emerald-200 shadow-lg shadow-emerald-500/10'
            : 'border-red-500/40 bg-red-950/80 text-red-200 shadow-lg shadow-red-500/10'"
        >
          {{ toast.message }}
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
/* ── 面板容器 ── */
.knowledge-panel {
  background: rgba(10, 10, 18, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    -8px 0 40px rgba(0, 0, 0, 0.6),
    -2px 0 0 rgba(0, 210, 255, 0.08),
    0 0 60px rgba(139, 92, 246, 0.06);
}

/* ── 头部 ── */
.panel-header {
  background: rgba(255, 255, 255, 0.02);
}

.icon-badge {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid rgba(0, 210, 255, 0.25);
  background: rgba(0, 210, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn {
  transition: all 0.2s ease;
}

/* ── 分区标签 ── */
.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(139, 92, 246, 0.7);
  margin-bottom: 10px;
}

/* ── 拖拽上传区 ── */
.dropzone {
  border: 1.5px dashed rgba(0, 210, 255, 0.25);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dropzone:hover {
  border-color: rgba(0, 210, 255, 0.5);
  background: rgba(0, 210, 255, 0.03);
  box-shadow:
    0 0 20px rgba(0, 210, 255, 0.1),
    inset 0 0 20px rgba(0, 210, 255, 0.04);
}

.dropzone--active {
  border-color: rgba(139, 92, 246, 0.7);
  background: rgba(139, 92, 246, 0.06);
  box-shadow:
    0 0 30px rgba(139, 92, 246, 0.2),
    0 0 60px rgba(0, 210, 255, 0.1),
    inset 0 0 30px rgba(139, 92, 246, 0.06);
}

.upload-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: 1px solid rgba(0, 210, 255, 0.3);
  background: rgba(0, 210, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn {
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid rgba(0, 210, 255, 0.3);
  background: rgba(0, 210, 255, 0.08);
  color: rgba(0, 210, 255, 0.9);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-btn:hover {
  background: rgba(0, 210, 255, 0.15);
  color: white;
}

/* ── Embedding Loading 区 ── */
.loading-zone {
  border: 1.5px solid rgba(0, 210, 255, 0.3);
  border-radius: 12px;
  background: rgba(0, 210, 255, 0.04);
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  box-shadow:
    0 0 30px rgba(0, 210, 255, 0.08),
    inset 0 0 20px rgba(0, 210, 255, 0.03);
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: rgba(0, 210, 255, 0.3); }
  50%       { border-color: rgba(0, 210, 255, 0.6); }
}

.loading-orb {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid rgba(0, 210, 255, 0.3);
  background: rgba(0, 210, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 20px rgba(0, 210, 255, 0.2);
}

/* 流光扫描线 */
.scan-line {
  width: 180px;
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 210, 255, 0.8) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: scan 1.5s linear infinite;
}

@keyframes scan {
  0%   { background-position: -100% 0; }
  100% { background-position: 200% 0; }
}

/* ── 文件列表 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 16px;
  border: 1px dashed rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.01);
}

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.2s ease;
}

.file-row:hover {
  border-color: rgba(0, 210, 255, 0.15);
  background: rgba(0, 210, 255, 0.03);
}

.file-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid rgba(0, 210, 255, 0.2);
  background: rgba(0, 210, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.delete-btn {
  padding: 5px;
  border-radius: 6px;
  border: 1px solid transparent;
  color: rgba(239, 68, 68, 0.6);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.delete-btn:hover {
  color: rgb(239, 68, 68);
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}

/* ── 说明块 ── */
.hint-block {
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid rgba(139, 92, 246, 0.12);
  background: rgba(139, 92, 246, 0.04);
}

/* ── 滚动条 ── */
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(139, 92, 246, 0.3) transparent;
}

.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.3);
  border-radius: 2px;
}

/* ── 过渡动画 ── */
.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.25s ease;
}

.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

.panel-enter-active,
.panel-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
}

.panel-enter-from,
.panel-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
