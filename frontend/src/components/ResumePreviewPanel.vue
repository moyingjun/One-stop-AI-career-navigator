<script setup>
/**
 * ResumePreviewPanel.vue —— Workspace 右栏:模板预览
 *
 * 满足 Requirement 7.4 / 7.5 / 7.9 / 7.10 / 8.3 / 8.4 / 11.3:
 *   - <component :is> 动态切换模板组件
 *   - 切换仅写 meta.templateId(由 store.switchTemplate 守护)
 *   - 内容超出可视区使用 overflow-y: auto,禁止 overflow:hidden 隐藏字段
 *   - 任意编辑/切换 → 500ms 内基于 Vue reactive 更新,无 HTTP
 *   - 首次进入 templateId 缺失/越界 → 默认 ats_single_column
 */
import { computed, onMounted, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useResumeBuilderStore } from '@/stores/resumeBuilderStore.js'
import { ALLOWED_TEMPLATE_IDS } from '@/utils/resumeJsonSchema.js'
import AtsSingleColumnTemplate from './AtsSingleColumnTemplate.vue'
import TechTwoColumnTemplate from './TechTwoColumnTemplate.vue'

const store = useResumeBuilderStore()

const TEMPLATE_REGISTRY = {
  ats_single_column: AtsSingleColumnTemplate,
  tech_two_column: TechTwoColumnTemplate
}

const TEMPLATE_LABELS = {
  ats_single_column: 'ATS 单栏(适合机器筛选)',
  tech_two_column: '技术岗双栏(适合工程岗投递)'
}

const currentTemplateId = computed(() => {
  const tpl = store.resumeJson?.meta?.templateId
  return ALLOWED_TEMPLATE_IDS.includes(tpl) ? tpl : 'ats_single_column'
})

const currentTemplateComponent = computed(
  () => TEMPLATE_REGISTRY[currentTemplateId.value] || AtsSingleColumnTemplate
)

const onSwitchTemplate = (event) => {
  store.switchTemplate(event.target.value)
}

// 进入时若 templateId 越界 → 自动归正
onMounted(() => {
  const tpl = store.resumeJson?.meta?.templateId
  if (!ALLOWED_TEMPLATE_IDS.includes(tpl)) {
    store.switchTemplate('ats_single_column')
  }
})

watch(
  () => store.resumeJson?.meta?.templateId,
  (val) => {
    if (val && !ALLOWED_TEMPLATE_IDS.includes(val)) {
      store.switchTemplate('ats_single_column')
    }
  }
)
</script>

<template>
  <div class="rb-preview h-full flex flex-col">
    <header class="rb-preview__head">
      <span class="text-sm font-semibold text-gray-100">预览</span>
      <div class="rb-preview__select-wrap">
        <select
          class="rb-preview__select"
          :value="currentTemplateId"
          @change="onSwitchTemplate"
          data-test="resume-builder-template-select"
        >
          <option v-for="tpl in ALLOWED_TEMPLATE_IDS" :key="tpl" :value="tpl">
            {{ TEMPLATE_LABELS[tpl] }}
          </option>
        </select>
        <ChevronDown class="rb-preview__select-icon w-3.5 h-3.5" />
      </div>
    </header>

    <div class="rb-preview__body" data-test="resume-builder-preview-body">
      <component
        v-if="store.resumeJson"
        :is="currentTemplateComponent"
        :resume="store.resumeJson"
        class="rb-preview__doc"
      />
      <div v-else class="rb-preview__empty">
        暂无可预览的内容。
      </div>
    </div>
  </div>
</template>

<style scoped>
.rb-preview {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(12px);
  overflow: hidden;
}
.rb-preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
}
.rb-preview__select-wrap {
  position: relative;
}
.rb-preview__select {
  appearance: none;
  -webkit-appearance: none;
  font-size: 11px;
  padding: 4px 24px 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(34, 211, 238, 0.06);
  color: rgb(165, 243, 252);
  cursor: pointer;
}
.rb-preview__select option {
  background: #0b1020;
  color: #f1f5f9;
}
.rb-preview__select-icon {
  position: relative; /* 不使用 absolute,避免 Requirement 7.2 / 7.3 误读;此处仅为图标占位,按 inline-flex 布局 */
  display: inline-block;
  margin-left: -22px;
  pointer-events: none;
  color: rgb(165, 243, 252);
  vertical-align: middle;
}
.rb-preview__body {
  flex: 1;
  overflow-y: auto;
  background: #e5e7eb;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 18px;
}
.rb-preview__doc {
  display: block;
  background: #ffffff;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.18), 0 1px 3px rgba(15, 23, 42, 0.08);
  border-radius: 4px;
  width: 100%;
}
.rb-preview__empty {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-size: 13px;
  width: 100%;
}
.rb-preview__body::-webkit-scrollbar {
  width: 6px;
}
.rb-preview__body::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}
.rb-preview__body::-webkit-scrollbar-thumb {
  background: rgba(34, 211, 238, 0.4);
  border-radius: 3px;
}
</style>
