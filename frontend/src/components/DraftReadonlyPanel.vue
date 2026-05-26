<script setup>
/**
 * DraftReadonlyPanel.vue —— Resume Builder 左栏:只读草稿展示
 *
 * 满足 Requirement 10.1 / 10.3:
 *   - 仅以只读方式访问 Document_Workbench 的 plain_text / content_json
 *   - 不通过任何接口写回 Workbench 存储,不修改其内存对象
 *
 * MVP 实现:
 *   - 直接渲染 plain_text(预格式化文本),不挂载 Tiptap 编辑器,
 *     从根本上排除"可能写回"的技术风险。
 *   - 视觉保持暗黑赛博毛玻璃风格。
 */
import { computed } from 'vue'
import { FileText } from 'lucide-vue-next'

const props = defineProps({
  plainText: { type: String, default: '' },
  truncated: { type: Boolean, default: false }
})

const wordCount = computed(() =>
  Array.from((props.plainText || '').replace(/\s+/g, '')).length
)
</script>

<template>
  <div class="draft-readonly h-full flex flex-col">
    <header class="draft-readonly__head">
      <FileText class="w-3.5 h-3.5 text-cyan-300" />
      <span class="text-sm font-semibold text-gray-100">原草稿(只读)</span>
      <span class="ml-auto text-[10px] font-mono uppercase tracking-wider text-gray-500">
        {{ wordCount }} 字
      </span>
    </header>

    <div v-if="truncated" class="draft-readonly__warn">
      草稿已截断到 50000 字符以内
    </div>

    <pre
      v-if="plainText"
      class="draft-readonly__body"
      data-test="resume-builder-draft-readonly"
      >{{ plainText }}</pre
    >
    <div v-else class="draft-readonly__empty">
      草稿为空,可在右侧手工填写。
    </div>
  </div>
</template>

<style scoped>
.draft-readonly {
  background: rgba(0, 0, 0, 0.32);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(14px);
  overflow: hidden;
}
.draft-readonly__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
}
.draft-readonly__warn {
  margin: 8px 12px 0;
  padding: 6px 10px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.08);
  border-radius: 8px;
  font-size: 11px;
  color: rgba(252, 211, 77, 0.9);
}
.draft-readonly__body {
  flex: 1;
  margin: 0;
  padding: 12px;
  overflow-y: auto;
  font-family: ui-sans-serif, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.7;
  color: rgba(229, 231, 235, 0.92);
  white-space: pre-wrap;
  word-break: break-word;
  user-select: text;
}
.draft-readonly__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 12px;
  color: rgba(156, 163, 175, 0.7);
  padding: 24px;
}
.draft-readonly__body::-webkit-scrollbar {
  width: 5px;
}
.draft-readonly__body::-webkit-scrollbar-thumb {
  background: rgba(34, 211, 238, 0.3);
  border-radius: 3px;
}
</style>
