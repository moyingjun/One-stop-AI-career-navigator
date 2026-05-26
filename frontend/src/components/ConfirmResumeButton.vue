<script setup>
/**
 * ConfirmResumeButton.vue —— 「确认结构化结果」按钮
 *
 * 满足 Requirement 6.7 / 6.8 / 6.9 / 6.10:
 *   - 不含 missing/needs_confirmation → confirmedByUser=true,Toast「已确认结构化结果」
 *   - 含 missing/needs_confirmation → 弹出二次确认弹窗(基于 BaseModal)
 *     - 「仍然确认」→ 强制 confirmedByUser=true,Toast「已强制确认(仍含缺失字段)」
 *     - 「返回补全」/Esc/关闭图标 → 关闭弹窗,Resume_JSON 零变更
 */
import { computed, ref } from 'vue'
import { CheckCircle2, AlertTriangle } from 'lucide-vue-next'
import BaseModal from '@/components/BaseModal.vue'

const props = defineProps({
  hasMissing: { type: Boolean, default: false },
  missingPaths: { type: Array, default: () => [] },
  alreadyConfirmed: { type: Boolean, default: false }
})

const emit = defineEmits(['confirm', 'force-confirm'])

const showConfirmWithMissing = ref(false)

const buttonLabel = computed(() => {
  if (props.alreadyConfirmed) return '已确认 ✓'
  return '确认结构化结果'
})

const truncatedMissingPaths = computed(() => {
  const paths = props.missingPaths || []
  if (paths.length <= 10) return { items: paths, more: 0 }
  return { items: paths.slice(0, 10), more: paths.length - 10 }
})

const onClick = () => {
  if (props.alreadyConfirmed) return
  if (!props.hasMissing) {
    emit('confirm')
    return
  }
  showConfirmWithMissing.value = true
}

const onForceConfirm = () => {
  showConfirmWithMissing.value = false
  emit('force-confirm')
}

const onCancelConfirm = () => {
  showConfirmWithMissing.value = false
}
</script>

<template>
  <div class="confirm-resume">
    <button
      type="button"
      class="confirm-resume__btn"
      :class="{ 'is-confirmed': alreadyConfirmed }"
      :disabled="alreadyConfirmed"
      data-test="confirm-resume-button"
      @click="onClick"
    >
      <CheckCircle2 class="w-4 h-4" />
      <span>{{ buttonLabel }}</span>
    </button>
    <p class="confirm-resume__hint">
      确认后才能导出 PDF / DOCX
    </p>

    <BaseModal
      v-model="showConfirmWithMissing"
      max-width="max-w-md"
      @close="onCancelConfirm"
    >
      <div class="p-6">
        <div class="flex items-center gap-2 mb-3">
          <AlertTriangle class="w-5 h-5 text-amber-300" />
          <h3 class="text-base font-semibold text-white">仍含未补全字段</h3>
        </div>
        <p class="text-sm text-gray-400 leading-relaxed mb-3">
          以下字段仍处于 missing / needs_confirmation 状态:
        </p>
        <ul class="confirm-resume__missing-list">
          <li v-for="path in truncatedMissingPaths.items" :key="path">{{ path }}</li>
          <li v-if="truncatedMissingPaths.more > 0" class="confirm-resume__missing-more">
            ……等其余 {{ truncatedMissingPaths.more }} 项
          </li>
        </ul>
        <div class="flex gap-3 mt-5">
          <button
            type="button"
            class="confirm-resume__modal-btn"
            @click="onCancelConfirm"
          >
            返回补全
          </button>
          <button
            type="button"
            class="confirm-resume__modal-btn confirm-resume__modal-btn--danger"
            data-test="confirm-resume-force"
            @click="onForceConfirm"
          >
            仍然确认
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.confirm-resume {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
}
.confirm-resume__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.85), rgba(168, 85, 247, 0.85));
  border: 1px solid rgba(34, 211, 238, 0.5);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.25);
  cursor: pointer;
  transition: all 0.2s ease;
}
.confirm-resume__btn:hover:not(:disabled) {
  box-shadow: 0 0 28px rgba(34, 211, 238, 0.4);
  transform: translateY(-1px);
}
.confirm-resume__btn.is-confirmed {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.4);
  color: rgb(167, 243, 208);
  box-shadow: none;
}
.confirm-resume__btn:disabled {
  cursor: not-allowed;
}
.confirm-resume__hint {
  text-align: center;
  font-size: 11px;
  color: rgba(156, 163, 175, 0.7);
}
.confirm-resume__missing-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  color: rgba(252, 211, 77, 0.9);
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.18);
  border-radius: 8px;
  padding: 8px 10px;
}
.confirm-resume__missing-more {
  color: rgba(156, 163, 175, 0.7);
  font-style: italic;
  padding-top: 4px;
  border-top: 1px dashed rgba(245, 158, 11, 0.2);
  margin-top: 4px;
}
.confirm-resume__modal-btn {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: rgba(229, 231, 235, 0.85);
  cursor: pointer;
  transition: all 0.18s ease;
}
.confirm-resume__modal-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.confirm-resume__modal-btn--danger {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(168, 85, 247, 0.15));
  border-color: rgba(239, 68, 68, 0.35);
  color: rgb(252, 165, 165);
}
.confirm-resume__modal-btn--danger:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.28), rgba(168, 85, 247, 0.28));
  color: #fff;
}
</style>
