<script setup>
/**
 * ResumeBuilderWorkspace.vue —— 简历预览构建器工作区(全屏 Modal)
 *
 * 三栏布局:
 *   - 左 320px:DraftReadonlyPanel(只读草稿)
 *   - 中 flex-1:StructuredResumeForm(结构化表单)
 *   - 右 480-640px:ResumePreviewPanel + ExportToolbar
 *
 * 满足:
 *   - Requirement 1.2 / 1.3:1 秒打开 + 关闭后回到 /files
 *   - Requirement 8.3 / 11.5:编辑/切换不触发 HTTP
 *   - Requirement 11.4:无 localStorage 数据时空状态
 *   - Requirement 11.7:fabrication banner 由 StructuredResumeForm 内部渲染
 *
 * 暗黑赛博毛玻璃风格。
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { X, FileEdit, Loader2, AlertTriangle, RefreshCw } from 'lucide-vue-next'
import { useResumeBuilderStore } from '@/stores/resumeBuilderStore.js'
import DraftReadonlyPanel from './DraftReadonlyPanel.vue'
import StructuredResumeForm from './StructuredResumeForm.vue'
import ResumePreviewPanel from './ResumePreviewPanel.vue'
import ExportToolbar from './ExportToolbar.vue'

const props = defineProps({
  /** 由 /files 透传:{document_id, plain_text, content_json, provider_id} */
  draft: { type: Object, default: null },
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'close'])

const store = useResumeBuilderStore()

// ─── 关闭逻辑 ──
const handleClose = () => {
  emit('update:modelValue', false)
  emit('close')
}

const onEsc = (e) => {
  if (e.key === 'Escape' && props.modelValue) handleClose()
}

onMounted(() => {
  document.addEventListener('keydown', onEsc)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onEsc)
})

// ─── 进入时:initFromDraft ──
const startInit = async () => {
  if (!props.draft) return
  await store.initFromDraft(props.draft)
}

watch(
  () => [props.modelValue, props.draft],
  ([open, draft]) => {
    if (open && draft) {
      startInit()
    }
  },
  { immediate: true }
)

const isExtracting = computed(() => store.extracting)
const showEmptyState = computed(() => !store.resumeJson && !store.extracting)

// ─── Hotfix 4:LLM 抽取超时 / 失败提示 + 重新抽取 ──
/** 是否展示"AI 抽取超时 / 失败"横幅(本会话内可被关闭)。*/
const timeoutBannerDismissed = ref(false)
/** 是否正在重试。*/
const retrying = ref(false)

watch(
  () => store.warnings,
  () => {
    // 任何一次新的 extract 完成(warnings 数组引用变化)都重置 banner 关闭状态
    timeoutBannerDismissed.value = false
  }
)

const showTimeoutBanner = computed(() => {
  if (timeoutBannerDismissed.value) return false
  if (!Array.isArray(store.warnings)) return false
  return store.warnings.includes('extraction_timeout') || store.warnings.includes('json_parse_failed')
})

const timeoutBannerText = computed(() => {
  if (!Array.isArray(store.warnings)) return ''
  if (store.warnings.includes('extraction_timeout')) {
    return 'AI 抽取超时,已进入手动填写模式。你可以继续手动补全,或稍后重试。'
  }
  if (store.warnings.includes('json_parse_failed')) {
    return 'AI 抽取失败,已进入手动填写模式。你可以继续手动补全,或重试。'
  }
  return ''
})

const onRetryExtract = async () => {
  if (!props.draft || retrying.value) return
  retrying.value = true
  try {
    await store.reextractFromDraft(props.draft)
  } finally {
    retrying.value = false
  }
}

const onDismissTimeoutBanner = () => {
  timeoutBannerDismissed.value = true
}
</script>

<template>
  <Teleport to="body">
    <Transition name="rb-workspace">
      <div
        v-if="modelValue"
        class="rb-workspace"
        role="dialog"
        aria-modal="true"
        data-test="resume-builder-workspace"
      >
        <!-- 顶栏 -->
        <header class="rb-workspace__header">
          <div class="flex items-center gap-2">
            <FileEdit class="w-4 h-4 text-cyan-300" />
            <div class="flex flex-col leading-tight">
              <h2 class="text-sm font-semibold text-white">简历预览构建器</h2>
              <span class="text-[11px] text-gray-400">结构化简历 · 模板预览 · 导出投递版</span>
            </div>
          </div>
          <button
            type="button"
            class="rb-workspace__close"
            aria-label="关闭"
            @click="handleClose"
            data-test="resume-builder-close"
          >
            <X class="w-4 h-4" />
          </button>
        </header>

        <!-- Hotfix 4:抽取超时 / 失败横幅 -->
        <div
          v-if="showTimeoutBanner"
          class="rb-workspace__timeout-banner"
          role="status"
          data-test="resume-builder-timeout-banner"
        >
          <AlertTriangle class="w-4 h-4 flex-shrink-0 text-amber-300" />
          <span class="rb-workspace__timeout-text">{{ timeoutBannerText }}</span>
          <button
            type="button"
            class="rb-workspace__retry-btn"
            :disabled="retrying || isExtracting"
            data-test="resume-builder-retry"
            @click="onRetryExtract"
          >
            <Loader2 v-if="retrying" class="w-3.5 h-3.5 animate-spin" />
            <RefreshCw v-else class="w-3.5 h-3.5" />
            <span>{{ retrying ? '重新抽取中…' : '重新抽取' }}</span>
          </button>
          <button
            type="button"
            class="rb-workspace__dismiss-btn"
            aria-label="关闭提示"
            @click="onDismissTimeoutBanner"
          >
            ×
          </button>
        </div>

        <!-- Beta 提示横幅:实验功能,提醒用户核对后再导出 -->
        <div class="rb-workspace__beta-banner" role="note" data-test="resume-builder-beta-banner">
          <span class="rb-workspace__beta-tag">Beta</span>
          <span class="rb-workspace__beta-text">实验功能:请核对 AI 抽取结果后再导出。</span>
        </div>

        <!-- 三栏 -->
        <div class="rb-workspace__body">
          <aside class="rb-workspace__col rb-workspace__col--left">
            <DraftReadonlyPanel
              :plain-text="props.draft?.plain_text || ''"
              :truncated="store.draftTruncated"
            />
          </aside>

          <section class="rb-workspace__col rb-workspace__col--center">
            <div v-if="isExtracting" class="rb-workspace__loading">
              <Loader2 class="w-6 h-6 animate-spin text-cyan-300" />
              <p class="mt-3 text-sm text-gray-300">AI 正在抽取草稿,请稍候</p>
              <p class="text-[11px] text-gray-500 mt-1">大约 5-15 秒</p>
            </div>
            <div v-else-if="showEmptyState" class="rb-workspace__empty">
              <h3 class="text-base font-semibold text-white mb-2">暂无本地结构化简历</h3>
              <p class="text-sm text-gray-400 mb-5 max-w-sm leading-relaxed">
                点击下方按钮,从当前文档生成一份结构化简历。
              </p>
              <button
                type="button"
                class="rb-workspace__cta"
                @click="startInit"
                data-test="resume-builder-empty-cta"
              >
                从当前文档生成
              </button>
            </div>
            <StructuredResumeForm v-else />
          </section>

          <section class="rb-workspace__col rb-workspace__col--right">
            <ResumePreviewPanel class="flex-1 min-h-0" />
            <ExportToolbar />
          </section>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.rb-workspace {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(2, 2, 5, 0.92);
  backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
}
.rb-workspace__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
}
.rb-workspace__close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.7);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.18s ease;
}
.rb-workspace__close:hover {
  background: rgba(34, 211, 238, 0.1);
  border-color: rgba(34, 211, 238, 0.4);
  color: #fff;
}

/* Hotfix 4:抽取超时 / 失败横幅 */
.rb-workspace__timeout-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  background: rgba(245, 158, 11, 0.08);
  border-bottom: 1px solid rgba(245, 158, 11, 0.4);
  color: rgb(252, 211, 77);
  flex-shrink: 0;
  font-size: 13px;
}
.rb-workspace__timeout-text {
  flex: 1;
  line-height: 1.5;
}
.rb-workspace__retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(34, 211, 238, 0.5);
  background: rgba(34, 211, 238, 0.1);
  color: rgb(165, 243, 252);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
}
.rb-workspace__retry-btn:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.2);
  color: #fff;
}
.rb-workspace__retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rb-workspace__dismiss-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 18px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.rb-workspace__dismiss-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

/* Beta 提示横幅 */
.rb-workspace__beta-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 18px;
  background: rgba(168, 85, 247, 0.06);
  border-bottom: 1px solid rgba(168, 85, 247, 0.18);
  color: rgba(216, 180, 254, 0.95);
  flex-shrink: 0;
  font-size: 12px;
}
.rb-workspace__beta-tag {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(168, 85, 247, 0.18);
  border: 1px solid rgba(168, 85, 247, 0.4);
  color: rgb(216, 180, 254);
}
.rb-workspace__beta-text {
  flex: 1;
  line-height: 1.5;
}

.rb-workspace__body {
  flex: 1;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) minmax(420px, 540px);
  gap: 12px;
  padding: 12px;
  min-height: 0;
}
.rb-workspace__col {
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.rb-workspace__col--left {
  /* DraftReadonlyPanel 自带边框 */
}
.rb-workspace__col--center {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(12px);
  overflow: hidden;
}
.rb-workspace__col--right {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(12px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.rb-workspace__loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px;
}
.rb-workspace__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px;
}
.rb-workspace__cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.85), rgba(168, 85, 247, 0.85));
  border: 1px solid rgba(34, 211, 238, 0.5);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.25);
  cursor: pointer;
  transition: all 0.2s ease;
}
.rb-workspace__cta:hover {
  box-shadow: 0 0 28px rgba(34, 211, 238, 0.4);
  transform: translateY(-1px);
}

.rb-workspace-enter-active,
.rb-workspace-leave-active {
  transition: opacity 0.2s ease;
}
.rb-workspace-enter-from,
.rb-workspace-leave-to {
  opacity: 0;
}

@media (max-width: 1100px) {
  .rb-workspace__body {
    grid-template-columns: 280px 1fr 380px;
  }
}
@media (max-width: 900px) {
  .rb-workspace__body {
    grid-template-columns: 1fr;
    grid-auto-rows: minmax(280px, auto);
    overflow-y: auto;
  }
}

/* ─────────────── 打印样式(导出 PDF) ─────────────── */
/* 当 body 含 print-only-resume-preview 时,只保留 .rb-preview__doc 内容打印 */
</style>

<style>
/* 全局打印样式(非 scoped):配合 ExportToolbar 在 body 上加/去 class 控制 */
@media print {
  body.print-only-resume-preview > *:not(.rb-workspace) {
    display: none !important;
  }
  body.print-only-resume-preview .rb-workspace {
    position: static !important;
    background: #fff !important;
    backdrop-filter: none !important;
  }
  body.print-only-resume-preview .rb-workspace__header,
  body.print-only-resume-preview .rb-workspace__col--left,
  body.print-only-resume-preview .rb-workspace__col--center,
  body.print-only-resume-preview .rb-preview__head,
  body.print-only-resume-preview .rb-export {
    display: none !important;
  }
  body.print-only-resume-preview .rb-workspace__body {
    display: block !important;
    padding: 0 !important;
    background: #fff !important;
  }
  body.print-only-resume-preview .rb-workspace__col--right,
  body.print-only-resume-preview .rb-preview,
  body.print-only-resume-preview .rb-preview__body {
    display: block !important;
    background: #fff !important;
    border: none !important;
    overflow: visible !important;
    box-shadow: none !important;
    padding: 0 !important;
  }
  body.print-only-resume-preview .rb-preview__doc {
    background: #fff !important;
    color: #111 !important;
  }
  /* 字段值保持为文字,绝不允许被截断 */
  body.print-only-resume-preview * {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: normal !important;
  }
  @page {
    size: A4;
    margin: 18mm 16mm;
  }
}
</style>
