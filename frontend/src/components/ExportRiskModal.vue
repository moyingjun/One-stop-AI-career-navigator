<script setup>
/**
 * ExportRiskModal.vue —— 导出前的缺失字段风险确认弹窗
 *
 * 满足 Requirement 9.6:
 *   - 列出缺失字段(≤10 全展示,>10 折叠 + 「等其余 N 项」)
 *   - 提供「忽略缺失继续导出」与「返回补全」二选一
 *   - 用户必须显式选择其一才能继续
 */
import { computed } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import BaseModal from '@/components/BaseModal.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  missingPaths: { type: Array, default: () => [] },
  exportFormat: { type: String, default: 'pdf' } // 'pdf' | 'docx'
})

const emit = defineEmits(['update:modelValue', 'continue', 'cancel'])

const truncated = computed(() => {
  const paths = props.missingPaths || []
  if (paths.length <= 10) return { items: paths, more: 0 }
  return { items: paths.slice(0, 10), more: paths.length - 10 }
})

const formatLabel = computed(() => (props.exportFormat === 'docx' ? 'DOCX' : 'PDF'))

const onContinue = () => {
  emit('update:modelValue', false)
  emit('continue')
}
const onCancel = () => {
  emit('update:modelValue', false)
  emit('cancel')
}
</script>

<template>
  <BaseModal :model-value="modelValue" max-width="max-w-md" @update:model-value="emit('update:modelValue', $event)" @close="onCancel">
    <div class="p-6">
      <div class="flex items-center gap-2 mb-3">
        <AlertTriangle class="w-5 h-5 text-amber-300" />
        <h3 class="text-base font-semibold text-white">导出 {{ formatLabel }} 风险确认</h3>
      </div>
      <p class="text-sm text-gray-400 leading-relaxed mb-3">
        以下字段尚未补全,导出后简历可能存在空缺:
      </p>
      <ul class="export-risk__list">
        <li v-for="path in truncated.items" :key="path">{{ path }}</li>
        <li v-if="truncated.more > 0" class="export-risk__more">
          ……等其余 {{ truncated.more }} 项
        </li>
      </ul>
      <div class="flex gap-3 mt-5">
        <button type="button" class="export-risk__btn" @click="onCancel">
          返回补全
        </button>
        <button
          type="button"
          class="export-risk__btn export-risk__btn--danger"
          data-test="export-risk-continue"
          @click="onContinue"
        >
          忽略缺失继续导出
        </button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.export-risk__list {
  list-style: none;
  padding: 8px 10px;
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
}
.export-risk__more {
  color: rgba(156, 163, 175, 0.7);
  font-style: italic;
  padding-top: 4px;
  border-top: 1px dashed rgba(245, 158, 11, 0.2);
  margin-top: 4px;
}
.export-risk__btn {
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
.export-risk__btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.export-risk__btn--danger {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(245, 158, 11, 0.15));
  border-color: rgba(245, 158, 11, 0.4);
  color: rgb(252, 211, 77);
}
.export-risk__btn--danger:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.28), rgba(245, 158, 11, 0.28));
  color: #fff;
}
</style>
