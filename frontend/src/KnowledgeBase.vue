<script setup>
/**
 * KnowledgeBase.vue —— 文档工作台 MVP（Tiptap 富文本编辑 + localStorage 草稿）
 *
 * Task B 范围：
 *   - 三栏布局：左 = 文档列表 + 类型筛选 + 新建；中 = 标题 + Tiptap 编辑器 + 自动保存状态；右 = 文档信息 / 后续功能预告
 *   - Tiptap 基础工具栏：bold / italic / heading / bullet list / ordered list / blockquote / undo / redo
 *   - 文档类型：简历草稿 / 求职笔记 / 升学资料 / 其他
 *   - 第一版仅写 localStorage（key: document_workspace_drafts），不接后端、不接 RAG、不接 ChatDock、不写 history
 *   - 暗黑赛博毛玻璃风格保持一致
 *
 * 严格不做：
 *   - 不调用 /api/* 任何接口（Tiptap 也是纯本地操作）
 *   - 不引入 marked / DOCX / PDF 导出依赖
 *   - 不修改 KnowledgePanel / kbService / ChatDock
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Plus,
  Trash2,
  FileEdit,
  NotebookPen,
  GraduationCap,
  StickyNote,
  Bold,
  Italic,
  Heading2,
  List,
  ListOrdered,
  Quote,
  Undo2,
  Redo2,
  Download,
  Printer,
  FileText,
  Sparkles,
  Database,
  Save,
  CheckCircle2,
  Loader2
} from 'lucide-vue-next'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import BaseModal from '@/components/BaseModal.vue'
import { showToast } from '@/utils/uiFallbacks'
import { exportDocxFromDocument } from '@/utils/docxExport.js'

const router = useRouter()

// ─────────────────────────────────────────────
// 常量与字典
// ─────────────────────────────────────────────

const STORAGE_KEY = 'document_workspace_drafts'
const ACTIVE_KEY = 'document_workspace_active_id'
const AUTOSAVE_DEBOUNCE_MS = 600

const DOC_TYPES = [
  { value: 'resume', label: '简历草稿', icon: FileEdit, tone: 'cyan' },
  { value: 'job-note', label: '求职笔记', icon: NotebookPen, tone: 'purple' },
  { value: 'edu-note', label: '升学资料', icon: GraduationCap, tone: 'pink' },
  { value: 'other', label: '其他', icon: StickyNote, tone: 'emerald' }
]

const TYPE_TONE_MAP = {
  cyan: {
    text: 'text-cyan-300',
    border: 'border-cyan-500/40',
    bg: 'bg-cyan-500/10',
    ring: 'ring-cyan-500/30'
  },
  purple: {
    text: 'text-purple-300',
    border: 'border-purple-500/40',
    bg: 'bg-purple-500/10',
    ring: 'ring-purple-500/30'
  },
  pink: {
    text: 'text-pink-300',
    border: 'border-pink-500/40',
    bg: 'bg-pink-500/10',
    ring: 'ring-pink-500/30'
  },
  emerald: {
    text: 'text-emerald-300',
    border: 'border-emerald-500/40',
    bg: 'bg-emerald-500/10',
    ring: 'ring-emerald-500/30'
  }
}

const TYPE_INDEX = Object.fromEntries(DOC_TYPES.map((t) => [t.value, t]))

const getTypeMeta = (typeValue) => TYPE_INDEX[typeValue] || TYPE_INDEX.other

// ─────────────────────────────────────────────
// 响应式状态
// ─────────────────────────────────────────────

/** 文档列表（按 updatedAt 倒序展示） */
const documents = ref([])
/** 当前激活文档 id */
const activeId = ref(null)
/** 类型筛选；'all' 表示全部 */
const filterType = ref('all')
/** 自动保存状态：'saved' | 'saving' | 'unsaved' */
const saveStatus = ref('saved')
/** 删除确认弹窗 */
const confirmDeleteId = ref(null)
const showConfirmDelete = ref(false)

let autosaveTimer = null

// ─────────────────────────────────────────────
// localStorage I/O（带防御性兜底）
// ─────────────────────────────────────────────

const readDrafts = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const list = JSON.parse(raw)
    if (!Array.isArray(list)) return []
    return list.filter((d) => d && typeof d.id === 'string')
  } catch (e) {
    console.warn('[DocWorkbench] 读取草稿失败:', e)
    return []
  }
}

const writeDrafts = (list) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
    return true
  } catch (e) {
    console.error('[DocWorkbench] 保存草稿失败:', e)
    showToast('本地存储已满，无法保存草稿', { type: 'error' })
    return false
  }
}

const readActiveId = () => {
  try {
    return localStorage.getItem(ACTIVE_KEY) || null
  } catch {
    return null
  }
}

const writeActiveId = (id) => {
  try {
    if (id) localStorage.setItem(ACTIVE_KEY, id)
    else localStorage.removeItem(ACTIVE_KEY)
  } catch {
    /* ignore */
  }
}

// ─────────────────────────────────────────────
// 计算属性
// ─────────────────────────────────────────────

const filteredDocuments = computed(() => {
  const list = filterType.value === 'all'
    ? documents.value
    : documents.value.filter((d) => d.type === filterType.value)
  return [...list].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
})

const activeDoc = computed(() =>
  documents.value.find((d) => d.id === activeId.value) || null
)

const wordCount = computed(() => {
  if (!activeDoc.value) return 0
  const text = (activeDoc.value.plainText || '').trim()
  if (!text) return 0
  // 中文按字、英文按单词，简单计数：去除空白 + 标点的可见字符数
  return Array.from(text.replace(/\s+/g, '')).length
})

const formattedUpdatedAt = computed(() => {
  if (!activeDoc.value || !activeDoc.value.updatedAt) return '—'
  return new Date(activeDoc.value.updatedAt).toLocaleString('zh-CN', { hour12: false })
})

// ─────────────────────────────────────────────
// Tiptap 编辑器
// ─────────────────────────────────────────────

const editor = useEditor({
  extensions: [StarterKit],
  content: '',
  editorProps: {
    attributes: {
      class: 'doc-editor-prose'
    }
  },
  onUpdate: ({ editor: ed }) => {
    if (!activeDoc.value) return
    saveStatus.value = 'unsaved'
    const html = ed.getHTML()
    const json = ed.getJSON()
    const plain = ed.getText()
    activeDoc.value.contentHtml = html
    activeDoc.value.contentJson = json
    activeDoc.value.plainText = plain
    activeDoc.value.updatedAt = Date.now()
    scheduleAutosave()
  }
})

// ─────────────────────────────────────────────
// 文档操作
// ─────────────────────────────────────────────

const generateId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'doc-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

const createDocument = (type = 'resume') => {
  const now = Date.now()
  const doc = {
    id: generateId(),
    title: '未命名文档',
    type,
    contentHtml: '',
    contentJson: { type: 'doc', content: [{ type: 'paragraph' }] },
    plainText: '',
    createdAt: now,
    updatedAt: now
  }
  documents.value.unshift(doc)
  setActive(doc.id)
  // 立即落盘（新建动作必须立刻保存，避免刷新丢失）
  persistAll()
  saveStatus.value = 'saved'
  showToast('已新建文档', { type: 'success' })
}

const setActive = (id) => {
  if (autosaveTimer) {
    clearTimeout(autosaveTimer)
    autosaveTimer = null
    persistAll()
    saveStatus.value = 'saved'
  }
  activeId.value = id
  writeActiveId(id)

  nextTick(() => {
    const doc = activeDoc.value
    if (!doc || !editor.value) return
    // 防止 onUpdate 把"切换文档"当作正常输入触发 autosave
    const html = doc.contentHtml || '<p></p>'
    editor.value.commands.setContent(html, false)
  })
}

const onTitleInput = (e) => {
  if (!activeDoc.value) return
  activeDoc.value.title = e.target.value
  activeDoc.value.updatedAt = Date.now()
  saveStatus.value = 'unsaved'
  scheduleAutosave()
}

const onTypeChange = (newType) => {
  if (!activeDoc.value) return
  activeDoc.value.type = newType
  activeDoc.value.updatedAt = Date.now()
  saveStatus.value = 'unsaved'
  scheduleAutosave()
}

const requestDelete = (id) => {
  confirmDeleteId.value = id
  showConfirmDelete.value = true
}

const confirmDelete = () => {
  const id = confirmDeleteId.value
  showConfirmDelete.value = false
  confirmDeleteId.value = null
  if (!id) return

  const idx = documents.value.findIndex((d) => d.id === id)
  if (idx < 0) return
  documents.value.splice(idx, 1)
  if (activeId.value === id) {
    const next = documents.value[0]
    if (next) setActive(next.id)
    else {
      activeId.value = null
      writeActiveId(null)
      if (editor.value) editor.value.commands.setContent('<p></p>', false)
    }
  }
  persistAll()
  showToast('文档已删除', { type: 'success' })
}

const cancelDelete = () => {
  showConfirmDelete.value = false
  confirmDeleteId.value = null
}

const docToDelete = computed(() =>
  documents.value.find((d) => d.id === confirmDeleteId.value) || null
)

// ─────────────────────────────────────────────
// 自动保存（debounce）
// ─────────────────────────────────────────────

const persistAll = () => {
  writeDrafts(documents.value)
}

const scheduleAutosave = () => {
  saveStatus.value = 'saving'
  if (autosaveTimer) clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(() => {
    persistAll()
    saveStatus.value = 'saved'
    autosaveTimer = null
  }, AUTOSAVE_DEBOUNCE_MS)
}

// 离开页面前 flush
const flushBeforeUnload = () => {
  if (autosaveTimer) {
    clearTimeout(autosaveTimer)
    autosaveTimer = null
  }
  persistAll()
}

// ─────────────────────────────────────────────
// 导出：TXT / 浏览器打印（PDF）
// ─────────────────────────────────────────────

/**
 * 文件名安全化：把非法/危险字符替换为 -，并裁剪长度。
 * 仅保留：中文 / 英文 / 数字 / 空格 / 中划线 / 下划线 / 点
 */
const sanitizeFilename = (raw) => {
  const fallback = '未命名文档'
  const src = (raw || '').trim() || fallback
  // 替换 Windows / POSIX 非法字符 + 控制字符 + 路径分隔
  let cleaned = src.replace(/[\\/:*?"<>|\x00-\x1F]/g, '-').trim()
  // 合并多余的连续 -
  cleaned = cleaned.replace(/-{2,}/g, '-')
  // 长度限制（按 UTF-8 视觉字符截断到 80）
  if (cleaned.length > 80) cleaned = cleaned.slice(0, 80).trim()
  return cleaned || fallback
}

/**
 * 浏览器原生 Blob 下载
 */
const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  // Firefox 需要 a 在 DOM 内才能触发下载
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // 释放 ObjectURL（异步以确保下载已开始）
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * HTML 转义（用于注入打印窗口的标题 / 类型 / 时间字段）
 * 正文 contentHtml 由 Tiptap 直出，已通过其 schema 限制为安全 markup。
 */
const escapeHtml = (str) => {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 导出 TXT：标题 + 类型 + 更新时间 + 空行 + plainText
 */
const exportTxt = () => {
  if (!activeDoc.value) return
  const doc = activeDoc.value
  const typeLabel = getTypeMeta(doc.type).label
  const updatedAtStr = doc.updatedAt
    ? new Date(doc.updatedAt).toLocaleString('zh-CN', { hour12: false })
    : '—'

  const lines = [
    `标题：${doc.title || '未命名文档'}`,
    `类型：${typeLabel}`,
    `更新时间：${updatedAtStr}`,
    '',
    doc.plainText || ''
  ]

  // Windows 友好换行 + UTF-8 BOM（让记事本默认按 UTF-8 打开中文不乱码）
  const text = lines.join('\r\n')
  const blob = new Blob(['\uFEFF' + text], { type: 'text/plain;charset=utf-8' })
  const filename = sanitizeFilename(doc.title) + '.txt'
  downloadBlob(blob, filename)
  showToast('已导出 TXT', { type: 'success' })
}

/**
 * 浏览器打印（保存为 PDF）：写入临时 iframe，调用 contentWindow.print()
 *
 * 不污染当前页面 DOM；不引入 html2pdf；不依赖后端 Playwright。
 * 用户在打印对话框选择"另存为 PDF"即可获得 PDF。
 */
const printPdf = () => {
  if (!activeDoc.value) return
  const doc = activeDoc.value
  const typeLabel = getTypeMeta(doc.type).label
  const updatedAtStr = doc.updatedAt
    ? new Date(doc.updatedAt).toLocaleString('zh-CN', { hour12: false })
    : '—'

  // 构造打印友好的最小 HTML 文档（白底黑字 / A4 / 合理字号行距）
  const printDocHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<title>${escapeHtml(doc.title || '未命名文档')}</title>
<style>
  @page { size: A4; margin: 18mm 16mm; }
  html, body {
    margin: 0;
    padding: 0;
    background: #ffffff;
    color: #111111;
    font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", Roboto, sans-serif;
    font-size: 12pt;
    line-height: 1.7;
  }
  .doc {
    max-width: 178mm;
    margin: 0 auto;
    padding: 4mm 0 8mm;
  }
  .doc-header { border-bottom: 1px solid #d4d4d4; padding-bottom: 8px; margin-bottom: 16px; }
  .doc-title  { font-size: 22pt; font-weight: 700; margin: 0 0 6px; color: #111; }
  .doc-meta   { font-size: 10pt; color: #555; }
  .doc-meta span + span::before { content: " · "; color: #aaa; padding: 0 4px; }
  .doc-body { font-size: 12pt; }
  .doc-body p { margin: 0.4em 0; }
  .doc-body h1 { font-size: 18pt; margin: 0.8em 0 0.4em; color: #111; }
  .doc-body h2 { font-size: 15pt; margin: 0.7em 0 0.35em; color: #111; }
  .doc-body h3 { font-size: 13pt; margin: 0.6em 0 0.3em; color: #111; }
  .doc-body strong { color: #111; }
  .doc-body em { color: #333; }
  .doc-body ul, .doc-body ol { padding-left: 1.4em; margin: 0.4em 0; }
  .doc-body li { margin: 0.2em 0; }
  .doc-body blockquote {
    margin: 0.6em 0;
    padding: 0.4em 0.9em;
    border-left: 3px solid #888;
    background: #f6f6f6;
    color: #333;
  }
  .doc-body code {
    font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
    background: #f3f3f3;
    padding: 0.05em 0.3em;
    border-radius: 3px;
    font-size: 0.92em;
  }
  .doc-body pre {
    background: #f3f3f3;
    border: 1px solid #e2e2e2;
    border-radius: 6px;
    padding: 8px 10px;
    overflow: auto;
    font-size: 10.5pt;
  }
  .doc-body pre code { background: none; padding: 0; }
  .doc-body hr { border: 0; border-top: 1px dashed #bbb; margin: 1em 0; }
  /* 不强行分页，避免长文档错位；浏览器自带分页足够 */
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style>
</head>
<body>
  <article class="doc">
    <header class="doc-header">
      <h1 class="doc-title">${escapeHtml(doc.title || '未命名文档')}</h1>
      <div class="doc-meta">
        <span>类型：${escapeHtml(typeLabel)}</span>
        <span>更新时间：${escapeHtml(updatedAtStr)}</span>
      </div>
    </header>
    <section class="doc-body">${doc.contentHtml || '<p></p>'}</section>
  </article>
</body>
</html>`

  // 用隐藏 iframe 触发打印，避免 window.open 被弹窗拦截器干掉
  const iframe = document.createElement('iframe')
  iframe.setAttribute('aria-hidden', 'true')
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  iframe.style.opacity = '0'
  iframe.style.pointerEvents = 'none'
  document.body.appendChild(iframe)

  const cleanup = () => {
    setTimeout(() => {
      try { document.body.removeChild(iframe) } catch { /* ignore */ }
    }, 1500)
  }

  // 写入 srcdoc 后等 iframe load 再调用 print
  iframe.onload = () => {
    try {
      const win = iframe.contentWindow
      if (!win) {
        showToast('打印窗口初始化失败', { type: 'error' })
        cleanup()
        return
      }
      // 监听 afterprint 卸载 iframe；部分浏览器不支持时由 cleanup() 兜底
      try {
        win.addEventListener('afterprint', cleanup, { once: true })
      } catch { /* ignore */ }
      win.focus()
      win.print()
      // 兜底卸载（用户取消 / 浏览器不触发 afterprint）
      setTimeout(cleanup, 60_000)
    } catch (e) {
      console.error('[DocWorkbench] 打印失败:', e)
      showToast('打印失败，请稍后重试', { type: 'error' })
      cleanup()
    }
  }

  // srcdoc 在所有现代浏览器（含 Edge）都支持
  iframe.srcdoc = printDocHtml
}

/**
 * 导出 DOCX：基于 docx 包，将 Tiptap contentJson 转为 .docx Blob 触发下载。
 * 失败时不影响当前文档内容，不清空 localStorage。
 */
const exportDocx = async () => {
  if (!activeDoc.value) return
  const doc = activeDoc.value
  const typeLabel = getTypeMeta(doc.type).label
  const updatedAtStr = doc.updatedAt
    ? new Date(doc.updatedAt).toLocaleString('zh-CN', { hour12: false })
    : '—'

  try {
    await exportDocxFromDocument(doc, typeLabel, updatedAtStr)
    showToast('DOCX 已导出', { type: 'success' })
  } catch (err) {
    console.error('[DocWorkbench] DOCX 导出失败:', err)
    showToast('DOCX 导出失败，请稍后重试', { type: 'error' })
  }
}

// ─────────────────────────────────────────────
// 工具栏命令（封装 Tiptap chain）
// ─────────────────────────────────────────────

const toggleBold = () => editor.value?.chain().focus().toggleBold().run()
const toggleItalic = () => editor.value?.chain().focus().toggleItalic().run()
const toggleH2 = () => editor.value?.chain().focus().toggleHeading({ level: 2 }).run()
const toggleBulletList = () => editor.value?.chain().focus().toggleBulletList().run()
const toggleOrderedList = () => editor.value?.chain().focus().toggleOrderedList().run()
const toggleBlockquote = () => editor.value?.chain().focus().toggleBlockquote().run()
const undoCmd = () => editor.value?.chain().focus().undo().run()
const redoCmd = () => editor.value?.chain().focus().redo().run()

const isActive = (name, opts) => {
  if (!editor.value) return false
  return opts ? editor.value.isActive(name, opts) : editor.value.isActive(name)
}

// ─────────────────────────────────────────────
// 生命周期
// ─────────────────────────────────────────────

onMounted(() => {
  documents.value = readDrafts()

  const savedId = readActiveId()
  const candidate =
    documents.value.find((d) => d.id === savedId) ||
    documents.value[0] ||
    null

  if (candidate) {
    setActive(candidate.id)
  }

  window.addEventListener('beforeunload', flushBeforeUnload)
})

// 编辑器实例在 EditorContent 挂载完成后才就绪；
// 首次挂载时如果 setActive() 早于 editor.value 就绪，需要在编辑器到位后补一次 setContent。
watch(
  () => editor.value,
  (ed) => {
    if (!ed) return
    const doc = activeDoc.value
    if (doc) {
      const html = doc.contentHtml || '<p></p>'
      ed.commands.setContent(html, false)
    }
  }
)

onBeforeUnmount(() => {
  flushBeforeUnload()
  window.removeEventListener('beforeunload', flushBeforeUnload)
  if (editor.value) editor.value.destroy()
})

// 切换 filter 时不影响 active，只影响左侧列表显示。
// 若当前 active 被过滤掉，仍保留编辑视图，由用户自己再选择。
watch(filterType, () => {
  /* no-op */
})
</script>

<template>
  <div class="min-h-[100dvh] bg-[#020205] text-gray-200 relative overflow-hidden">
    <!-- 背景 blur 层 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-[-10%] left-[-5%] w-[50vw] h-[50vh] rounded-full bg-purple-600/15 blur-[120px]"></div>
      <div class="absolute bottom-[-10%] right-[-5%] w-[45vw] h-[45vh] rounded-full bg-cyan-500/15 blur-[120px]"></div>
    </div>

    <div class="relative z-10 min-h-[100dvh] flex flex-col">
      <!-- 顶部导航 -->
      <header class="px-4 py-4 md:px-6 flex-shrink-0">
        <div class="max-w-[1400px] mx-auto flex items-center gap-3">
          <button
            @click="router.push('/dashboard')"
            class="p-2 rounded-lg border border-white/10 hover:bg-white/5 hover:border-cyan-400/30 transition-all duration-300 group"
            data-test="docs-workbench-back"
          >
            <ArrowLeft class="w-5 h-5 text-gray-400 group-hover:text-cyan-300 transition-colors" />
          </button>
          <div class="flex-1">
            <h1 class="text-lg md:text-xl font-bold text-white" data-test="docs-workbench-title">
              文档工作台
            </h1>
            <p class="text-xs text-gray-500">Document Workbench · MVP</p>
          </div>

          <!-- 自动保存状态 -->
          <div class="flex items-center gap-2 text-xs">
            <span v-if="saveStatus === 'saved'" class="flex items-center gap-1.5 text-emerald-300/90">
              <CheckCircle2 class="w-3.5 h-3.5" />
              已保存
            </span>
            <span v-else-if="saveStatus === 'saving'" class="flex items-center gap-1.5 text-cyan-300/90">
              <Loader2 class="w-3.5 h-3.5 animate-spin" />
              保存中
            </span>
            <span v-else class="flex items-center gap-1.5 text-amber-300/90">
              <Save class="w-3.5 h-3.5" />
              未保存
            </span>
          </div>
        </div>
      </header>

      <!-- 主体 -->
      <main class="flex-1 px-3 pb-6 md:px-6">
        <div class="max-w-[1400px] mx-auto grid grid-cols-1 md:grid-cols-12 gap-4">
          <!-- ─────────────── 左侧：列表 + 筛选 + 新建 ─────────────── -->
          <aside class="md:col-span-3">
            <div class="dw-panel p-3 flex flex-col gap-3">
              <!-- 新建按钮 -->
              <button
                type="button"
                @click="createDocument(filterType === 'all' ? 'resume' : filterType)"
                class="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-500 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 hover:scale-[1.01] active:scale-[0.99] transition-all"
                data-test="docs-new-doc"
              >
                <Plus class="w-4 h-4" />
                新建文档
              </button>

              <!-- 类型筛选 -->
              <div>
                <p class="text-[11px] font-mono uppercase tracking-wider text-gray-500 mb-1.5">FILTER</p>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    @click="filterType = 'all'"
                    class="dw-chip"
                    :class="filterType === 'all' ? 'dw-chip--active' : ''"
                  >
                    全部
                  </button>
                  <button
                    v-for="t in DOC_TYPES"
                    :key="t.value"
                    type="button"
                    @click="filterType = t.value"
                    class="dw-chip"
                    :class="[
                      filterType === t.value ? 'dw-chip--active' : '',
                      filterType === t.value ? TYPE_TONE_MAP[t.tone].text : ''
                    ]"
                  >
                    {{ t.label }}
                  </button>
                </div>
              </div>

              <!-- 列表 -->
              <div class="flex-1 min-h-[200px] max-h-[58vh] overflow-y-auto pr-1 -mr-1">
                <p
                  v-if="filteredDocuments.length === 0"
                  class="text-xs text-gray-500 text-center py-6"
                >
                  暂无文档，点击上方「新建文档」开始。
                </p>

                <ul v-else class="space-y-1.5">
                  <li
                    v-for="d in filteredDocuments"
                    :key="d.id"
                    class="dw-list-item group"
                    :class="d.id === activeId ? 'dw-list-item--active' : ''"
                    @click="setActive(d.id)"
                    :data-test="'docs-list-item-' + d.id"
                  >
                    <div class="flex items-start gap-2.5">
                      <span
                        class="w-7 h-7 rounded-md flex items-center justify-center border flex-shrink-0 mt-0.5"
                        :class="[
                          TYPE_TONE_MAP[getTypeMeta(d.type).tone].bg,
                          TYPE_TONE_MAP[getTypeMeta(d.type).tone].border
                        ]"
                      >
                        <component
                          :is="getTypeMeta(d.type).icon"
                          class="w-3.5 h-3.5"
                          :class="TYPE_TONE_MAP[getTypeMeta(d.type).tone].text"
                        />
                      </span>
                      <div class="flex-1 min-w-0">
                        <p class="text-sm text-gray-100 truncate">{{ d.title || '未命名文档' }}</p>
                        <p class="text-[10px] text-gray-500 mt-0.5">
                          {{ getTypeMeta(d.type).label }} ·
                          {{ new Date(d.updatedAt).toLocaleDateString('zh-CN') }}
                        </p>
                      </div>
                      <button
                        type="button"
                        @click.stop="requestDelete(d.id)"
                        class="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 transition-all"
                        title="删除"
                        :data-test="'docs-delete-' + d.id"
                      >
                        <Trash2 class="w-3.5 h-3.5 text-gray-500 hover:text-red-400 transition-colors" />
                      </button>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </aside>

          <!-- ─────────────── 中间：编辑器 ─────────────── -->
          <section class="md:col-span-6">
            <div class="dw-panel flex flex-col" style="min-height: 70vh;">
              <!-- 空态 -->
              <div
                v-if="!activeDoc"
                class="flex-1 flex flex-col items-center justify-center text-center px-6 py-16"
              >
                <div class="w-14 h-14 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 flex items-center justify-center mb-4">
                  <FileEdit class="w-7 h-7 text-cyan-300" />
                </div>
                <h3 class="text-base font-semibold text-white mb-2">还没有打开任何文档</h3>
                <p class="text-sm text-gray-500 mb-5 max-w-xs leading-relaxed">
                  点击左侧「新建文档」开始你的第一份草稿。所有内容会保存在你本地浏览器，不会上传服务器。
                </p>
                <button
                  type="button"
                  @click="createDocument('resume')"
                  class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-500 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all"
                >
                  <Plus class="w-4 h-4" />
                  新建一份简历草稿
                </button>
              </div>

              <!-- 编辑器主体 -->
              <template v-else>
                <!-- 标题 + 类型选择 -->
                <div class="px-4 pt-4 pb-2 flex flex-col gap-2">
                  <input
                    type="text"
                    :value="activeDoc.title"
                    @input="onTitleInput"
                    placeholder="文档标题"
                    class="w-full bg-transparent border-0 outline-none text-xl md:text-2xl font-bold text-white placeholder-gray-600 focus:ring-0"
                    data-test="docs-title-input"
                  />
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="text-[11px] text-gray-500 font-mono uppercase tracking-wider mr-1">TYPE</span>
                    <button
                      v-for="t in DOC_TYPES"
                      :key="t.value"
                      type="button"
                      @click="onTypeChange(t.value)"
                      class="dw-type-chip"
                      :class="[
                        activeDoc.type === t.value ? 'dw-type-chip--active' : '',
                        activeDoc.type === t.value ? [TYPE_TONE_MAP[t.tone].border, TYPE_TONE_MAP[t.tone].bg, TYPE_TONE_MAP[t.tone].text] : ''
                      ]"
                    >
                      <component :is="t.icon" class="w-3 h-3" />
                      {{ t.label }}
                    </button>
                  </div>
                </div>

                <!-- 工具栏 -->
                <div class="px-4 py-2 flex items-center gap-1 flex-wrap border-y border-white/5 bg-white/[0.02]">
                  <button type="button" class="dw-tb" :class="isActive('bold') ? 'dw-tb--active' : ''" @click="toggleBold" title="加粗">
                    <Bold class="w-3.5 h-3.5" />
                  </button>
                  <button type="button" class="dw-tb" :class="isActive('italic') ? 'dw-tb--active' : ''" @click="toggleItalic" title="斜体">
                    <Italic class="w-3.5 h-3.5" />
                  </button>
                  <button type="button" class="dw-tb" :class="isActive('heading', { level: 2 }) ? 'dw-tb--active' : ''" @click="toggleH2" title="标题">
                    <Heading2 class="w-3.5 h-3.5" />
                  </button>
                  <span class="dw-tb-sep"></span>
                  <button type="button" class="dw-tb" :class="isActive('bulletList') ? 'dw-tb--active' : ''" @click="toggleBulletList" title="无序列表">
                    <List class="w-3.5 h-3.5" />
                  </button>
                  <button type="button" class="dw-tb" :class="isActive('orderedList') ? 'dw-tb--active' : ''" @click="toggleOrderedList" title="有序列表">
                    <ListOrdered class="w-3.5 h-3.5" />
                  </button>
                  <button type="button" class="dw-tb" :class="isActive('blockquote') ? 'dw-tb--active' : ''" @click="toggleBlockquote" title="引用">
                    <Quote class="w-3.5 h-3.5" />
                  </button>
                  <span class="dw-tb-sep"></span>
                  <button type="button" class="dw-tb" @click="undoCmd" title="撤销">
                    <Undo2 class="w-3.5 h-3.5" />
                  </button>
                  <button type="button" class="dw-tb" @click="redoCmd" title="重做">
                    <Redo2 class="w-3.5 h-3.5" />
                  </button>
                </div>

                <!-- 编辑区 -->
                <div class="flex-1 px-4 pb-4 pt-3 overflow-y-auto" data-test="docs-editor-area">
                  <EditorContent :editor="editor" />
                </div>
              </template>
            </div>
          </section>

          <!-- ─────────────── 右侧：文档信息 + 后续预告 ─────────────── -->
          <aside class="md:col-span-3 flex flex-col gap-4">
            <div class="dw-panel p-4">
              <div class="flex items-center gap-2 mb-3">
                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.6)]"></span>
                <h2 class="text-xs font-mono uppercase tracking-wider text-gray-300">DOC INFO</h2>
              </div>

              <dl class="space-y-3 text-sm">
                <div>
                  <dt class="text-[11px] text-gray-500 uppercase tracking-wider mb-0.5">类型</dt>
                  <dd class="flex items-center gap-1.5 text-gray-200">
                    <template v-if="activeDoc">
                      <span
                        class="w-5 h-5 rounded-md flex items-center justify-center border"
                        :class="[
                          TYPE_TONE_MAP[getTypeMeta(activeDoc.type).tone].bg,
                          TYPE_TONE_MAP[getTypeMeta(activeDoc.type).tone].border
                        ]"
                      >
                        <component
                          :is="getTypeMeta(activeDoc.type).icon"
                          class="w-3 h-3"
                          :class="TYPE_TONE_MAP[getTypeMeta(activeDoc.type).tone].text"
                        />
                      </span>
                      {{ getTypeMeta(activeDoc.type).label }}
                    </template>
                    <span v-else class="text-gray-500">—</span>
                  </dd>
                </div>
                <div>
                  <dt class="text-[11px] text-gray-500 uppercase tracking-wider mb-0.5">字数</dt>
                  <dd class="text-gray-200">
                    <span v-if="activeDoc">{{ wordCount }} 字</span>
                    <span v-else class="text-gray-500">—</span>
                  </dd>
                </div>
                <div>
                  <dt class="text-[11px] text-gray-500 uppercase tracking-wider mb-0.5">更新时间</dt>
                  <dd class="text-gray-200 text-[13px]">{{ formattedUpdatedAt }}</dd>
                </div>
              </dl>
            </div>

            <!-- 导出操作 -->
            <div class="dw-panel p-4">
              <div class="flex items-center gap-2 mb-3">
                <Download class="w-3.5 h-3.5 text-cyan-300" />
                <h2 class="text-xs font-mono uppercase tracking-wider text-gray-300">EXPORT</h2>
              </div>

              <div class="flex flex-col gap-2">
                <button
                  type="button"
                  @click="exportTxt"
                  :disabled="!activeDoc"
                  class="dw-export-btn"
                  data-test="docs-export-txt"
                >
                  <FileText class="w-4 h-4" />
                  <span>导出 TXT</span>
                </button>

                <button
                  type="button"
                  @click="exportDocx"
                  :disabled="!activeDoc"
                  class="dw-export-btn"
                  data-test="docs-export-docx"
                >
                  <FileText class="w-4 h-4" />
                  <span>导出 DOCX</span>
                </button>

                <button
                  type="button"
                  @click="printPdf"
                  :disabled="!activeDoc"
                  class="dw-export-btn"
                  data-test="docs-export-print"
                >
                  <Printer class="w-4 h-4" />
                  <span>打印 / 导出 PDF</span>
                </button>
              </div>

              <p v-if="!activeDoc" class="mt-3 text-[11px] text-amber-300/80 leading-relaxed">
                请先创建文档。
              </p>
              <p v-else class="mt-3 text-[11px] text-gray-500 leading-relaxed">
                打印对话框中可选择"另存为 PDF"获得 PDF 文件。
              </p>
            </div>

            <!-- 后续功能预告 -->
            <div class="dw-panel p-4">
              <div class="flex items-center gap-2 mb-2">
                <Sparkles class="w-3.5 h-3.5 text-purple-300" />
                <h2 class="text-xs font-mono uppercase tracking-wider text-gray-300">UPCOMING</h2>
              </div>
              <ul class="space-y-1.5 text-[13px] text-gray-400">
                <li class="flex items-center gap-2">
                  <Sparkles class="w-3.5 h-3.5 text-purple-300/70" />
                  AI 优化 / 改写
                  <span class="ml-auto text-[10px] font-mono text-gray-500">soon</span>
                </li>
                <li class="flex items-center gap-2">
                  <Database class="w-3.5 h-3.5 text-pink-300/70" />
                  加入个人知识库
                  <span class="ml-auto text-[10px] font-mono text-gray-500">soon</span>
                </li>
              </ul>
              <p class="mt-3 text-[11px] text-gray-500 leading-relaxed">
                目前文档仅保存在浏览器本地，刷新或换设备后请回到本页查看。
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>

    <!-- 删除确认弹窗 -->
    <BaseModal
      v-model="showConfirmDelete"
      max-width="max-w-sm"
      @close="cancelDelete"
    >
      <div class="p-6">
        <h3 class="text-base font-semibold text-white mb-2">确认删除文档？</h3>
        <p class="text-sm text-gray-400 leading-relaxed mb-5">
          <span class="text-gray-200">{{ docToDelete?.title || '未命名文档' }}</span>
          将从本地草稿中移除，且无法恢复。
        </p>
        <div class="flex gap-3">
          <button
            type="button"
            @click="cancelDelete"
            class="flex-1 py-2.5 rounded-xl text-sm font-medium border border-white/10 text-gray-300 hover:bg-white/5 transition-all"
          >
            取消
          </button>
          <button
            type="button"
            @click="confirmDelete"
            class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-red-500 to-orange-500 shadow-lg shadow-red-500/20 hover:shadow-red-500/40 transition-all"
            data-test="docs-confirm-delete"
          >
            删除
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
/* ─── 玻璃面板 ─── */
.dw-panel {
  background: rgba(0, 0, 0, 0.32);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.04);
}

/* ─── 类型 chip（左侧筛选） ─── */
.dw-chip {
  font-size: 11px;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
  color: rgba(229, 231, 235, 0.7);
  transition: all 0.18s ease;
  cursor: pointer;
}
.dw-chip:hover {
  border-color: rgba(255, 255, 255, 0.18);
  color: #fff;
}
.dw-chip--active {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.22);
  color: #fff;
}

/* ─── 类型 chip（编辑器顶部） ─── */
.dw-type-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
  color: rgba(229, 231, 235, 0.7);
  transition: all 0.18s ease;
  cursor: pointer;
}
.dw-type-chip:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}
.dw-type-chip--active {
  font-weight: 600;
}

/* ─── 列表项 ─── */
.dw-list-item {
  border-radius: 10px;
  padding: 8px 10px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.015);
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}
.dw-list-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
.dw-list-item--active {
  background: rgba(34, 211, 238, 0.08);
  border-color: rgba(34, 211, 238, 0.35);
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.08);
}

/* ─── 工具栏按钮 ─── */
.dw-tb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid transparent;
  color: rgba(229, 231, 235, 0.7);
  background: transparent;
  transition: all 0.15s ease;
  cursor: pointer;
}
.dw-tb:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.dw-tb--active {
  background: rgba(34, 211, 238, 0.12);
  border-color: rgba(34, 211, 238, 0.35);
  color: rgb(165, 243, 252);
}
.dw-tb-sep {
  display: inline-block;
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.08);
  margin: 0 4px;
}

/* ─── 导出按钮（右侧操作面板） ─── */
.dw-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(34, 211, 238, 0.28);
  background: rgba(34, 211, 238, 0.06);
  color: rgb(165, 243, 252);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.18s ease;
  cursor: pointer;
}
.dw-export-btn:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.12);
  border-color: rgba(34, 211, 238, 0.5);
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.18);
  color: #fff;
}
.dw-export-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.dw-export-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.45);
  box-shadow: none;
}

/* ─── Tiptap ProseMirror 视觉规范（暗色 + 紫青 accent） ─── */
:deep(.ProseMirror) {
  min-height: 50vh;
  outline: none;
  color: rgba(229, 231, 235, 0.92);
  font-size: 14px;
  line-height: 1.75;
}
:deep(.ProseMirror:focus) {
  outline: none;
}
:deep(.ProseMirror p) {
  margin: 0.4em 0;
}
:deep(.ProseMirror h1),
:deep(.ProseMirror h2),
:deep(.ProseMirror h3) {
  font-weight: 700;
  color: #fff;
  margin: 0.8em 0 0.4em;
  background: linear-gradient(135deg, #a78bfa, #22d3ee);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
:deep(.ProseMirror h1) { font-size: 1.55em; }
:deep(.ProseMirror h2) { font-size: 1.3em; }
:deep(.ProseMirror h3) { font-size: 1.1em; }
:deep(.ProseMirror strong) { color: #f0abfc; font-weight: 700; }
:deep(.ProseMirror em) { color: #a5f3fc; }
:deep(.ProseMirror ul),
:deep(.ProseMirror ol) {
  padding-left: 1.4em;
  margin: 0.3em 0;
}
:deep(.ProseMirror li) {
  margin: 0.2em 0;
}
:deep(.ProseMirror li::marker) {
  color: rgba(167, 139, 250, 0.85);
}
:deep(.ProseMirror blockquote) {
  margin: 0.6em 0;
  padding: 0.4em 0.8em;
  border-left: 3px solid rgba(34, 211, 238, 0.45);
  background: rgba(34, 211, 238, 0.04);
  border-radius: 0 6px 6px 0;
  color: rgba(229, 231, 235, 0.78);
}
:deep(.ProseMirror code) {
  background: rgba(168, 85, 247, 0.12);
  padding: 0.1em 0.35em;
  border-radius: 4px;
  font-size: 0.9em;
  color: #f0abfc;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
:deep(.ProseMirror pre) {
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(168, 85, 247, 0.18);
  border-radius: 8px;
  padding: 0.8em;
  overflow-x: auto;
  margin: 0.5em 0;
}
:deep(.ProseMirror pre code) {
  background: none;
  padding: 0;
}
:deep(.ProseMirror hr) {
  border: 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.12);
  margin: 1em 0;
}
:deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: '在这里开始书写...';
  color: rgba(255, 255, 255, 0.18);
  pointer-events: none;
  height: 0;
  float: left;
}

/* ─── 滚动条 ─── */
.dw-panel::-webkit-scrollbar,
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.dw-panel::-webkit-scrollbar-thumb,
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}
.dw-panel::-webkit-scrollbar-thumb:hover,
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.16);
}

/* ─── 移动端：上下布局降级 ─── */
@media (max-width: 767px) {
  .dw-panel {
    border-radius: 12px;
  }
}
</style>
