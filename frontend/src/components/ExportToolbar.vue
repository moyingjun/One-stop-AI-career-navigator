<script setup>
/**
 * ExportToolbar.vue —— 导出工具栏(PDF / DOCX)
 *
 * 满足 Requirement 9.1 / 9.2 / 9.3 / 9.4 / 9.5 / 9.6 / 9.7 / 9.8 / 11.1:
 *   - confirmedByUser=false 时按钮 disabled + tooltip
 *   - confirmedByUser=false 点击 → Toast「请先在表单底部点击『确认结构化结果』」≥3s
 *   - 含 missing/needs_confirmation 时弹 ExportRiskModal,二选一
 *   - PDF 流:document.body 加 print-only-resume-preview class → window.print() → afterprint 移除
 *   - DOCX 流:resumeDocxBuilder.buildDocxBlob → URL.createObjectURL → <a download>
 *   - 文件名:buildExportFilename(basics, ext)
 *   - DOCX 写入失败 → Toast「导出失败,请重试」+ 不输出文件
 */
import { computed, ref } from 'vue'
import { Printer, FileText, AlertTriangle } from 'lucide-vue-next'
import { showToast } from '@/utils/uiFallbacks.js'
import { useResumeBuilderStore } from '@/stores/resumeBuilderStore.js'
import { buildExportFilename } from '@/utils/resumeFilename.js'
import { buildDocxBlob, ResumeDocxBuildError } from '@/utils/resumeDocxBuilder.js'
import { listMissingPaths } from '@/utils/resumeJsonSchema.js'
import ExportRiskModal from './ExportRiskModal.vue'

const store = useResumeBuilderStore()

const showRiskModal = ref(false)
const pendingFormat = ref('pdf') // 'pdf' | 'docx'
const exporting = ref(false)

const disabledReason = computed(() => {
  if (!store.resumeJson) return '尚未生成结构化简历'
  if (!store.isConfirmedByUser) return '请先确认结构化结果'
  return ''
})

const isDisabled = computed(() => disabledReason.value.length > 0)

const missingPaths = computed(() => {
  if (!store.resumeJson) return []
  // 用人类可读形式表达
  return listMissingPaths(store.resumeJson)
})

const onClickPdf = () => onClickExport('pdf')
const onClickDocx = () => onClickExport('docx')

const onClickExport = (fmt) => {
  if (!store.resumeJson) return
  if (!store.isConfirmedByUser) {
    showToast('请先在表单底部点击「确认结构化结果」', { type: 'error', duration: 3500 })
    return
  }
  if (store.stillHasMissing) {
    pendingFormat.value = fmt
    showRiskModal.value = true
    return
  }
  performExport(fmt)
}

const onContinueRisky = () => {
  performExport(pendingFormat.value)
}

const onCancelRisky = () => {
  // 零变更
}

const performExport = async (fmt) => {
  if (exporting.value) return
  exporting.value = true
  try {
    if (fmt === 'docx') {
      await exportDocx()
    } else {
      printPdf()
    }
  } finally {
    exporting.value = false
  }
}

const exportDocx = async () => {
  try {
    const blob = await buildDocxBlob(store.resumeJson, store.currentTemplateId)
    const filename = buildExportFilename(store.resumeJson?.basics, 'docx')
    triggerDownload(blob, filename)
    showToast('已导出 DOCX', { type: 'success' })
  } catch (err) {
    if (err instanceof ResumeDocxBuildError) {
      console.error('[ExportToolbar] DOCX 导出失败:', err)
    } else {
      console.error('[ExportToolbar] DOCX 未预期异常:', err)
    }
    showToast('导出失败,请重试', { type: 'error' })
  }
}

const triggerDownload = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const PRINT_CLASS = 'print-only-resume-preview'

const printPdf = () => {
  // 给 body 加 class,触发 print CSS;打印后由 afterprint 移除
  const body = document.body
  body.classList.add(PRINT_CLASS)
  const cleanup = () => {
    body.classList.remove(PRINT_CLASS)
    window.removeEventListener('afterprint', cleanup)
  }
  window.addEventListener('afterprint', cleanup, { once: true })
  // 兜底:某些浏览器(Safari)afterprint 可能不触发
  setTimeout(cleanup, 60_000)
  try {
    window.print()
  } catch (err) {
    console.error('[ExportToolbar] window.print 失败:', err)
    cleanup()
    showToast('打印失败,请稍后重试', { type: 'error' })
  }
}
</script>

<template>
  <div class="rb-export">
    <button
      type="button"
      class="rb-export__btn"
      :disabled="isDisabled || exporting"
      :title="disabledReason || '导出 PDF(浏览器打印)'"
      data-test="export-toolbar-pdf"
      @click="onClickPdf"
    >
      <Printer class="w-4 h-4" />
      <span>导出 PDF</span>
    </button>
    <button
      type="button"
      class="rb-export__btn"
      :disabled="isDisabled || exporting"
      :title="disabledReason || '导出 DOCX'"
      data-test="export-toolbar-docx"
      @click="onClickDocx"
    >
      <FileText class="w-4 h-4" />
      <span>导出 DOCX</span>
    </button>
    <p v-if="!store.isConfirmedByUser" class="rb-export__hint">
      <AlertTriangle class="w-3 h-3" />
      请先确认结构化结果
    </p>

    <ExportRiskModal
      v-model="showRiskModal"
      :missing-paths="missingPaths"
      :export-format="pendingFormat"
      @continue="onContinueRisky"
      @cancel="onCancelRisky"
    />
  </div>
</template>

<style scoped>
.rb-export {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}
.rb-export__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(34, 211, 238, 0.06);
  color: rgb(165, 243, 252);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
}
.rb-export__btn:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.14);
  color: #fff;
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.18);
}
.rb-export__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.45);
  box-shadow: none;
}
.rb-export__hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: rgba(252, 211, 77, 0.85);
  margin: 0;
}
</style>
