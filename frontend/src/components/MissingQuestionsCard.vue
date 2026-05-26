<script setup>
/**
 * MissingQuestionsCard.vue —— 内容优化建议(Beta 收口版)
 *
 * 设计:
 *   - 标题统一为「内容优化建议」(不再叫 AI 追问)
 *   - 最多展示 3 条;超出的折叠为单行注脚「还有 N 条建议待处理」
 *   - 已处理(对应字段已填)的建议排到末尾,按钮收起,显示「已处理」灰色 tag
 *   - 「采纳」/「忽略」按钮仅在未处理建议上出现
 *   - 不再有内部小滚动条:身体高度天然短(MAX_VISIBLE=3 + 单行注脚)
 *
 * Beta 收口约束:
 *   - 不做复杂智能填表
 *   - 不修改 Resume_JSON
 *   - 仅触发外层组件 emit:adopt/dismiss
 */
import { computed } from 'vue'
import { HelpCircle, Check, X, CheckCircle2 } from 'lucide-vue-next'

const props = defineProps({
  questions: { type: Array, default: () => [] },
  dismissed: { type: Set, default: () => new Set() },
  /** 已被用户手动填满字段而判定为「已处理」的 idx 集合 */
  resolved: { type: Set, default: () => new Set() }
})

const emit = defineEmits(['adopt', 'dismiss'])

const MAX_VISIBLE = 3

/** 全部未忽略的问题(包含已处理的)。 */
const allQuestions = computed(() =>
  (props.questions || [])
    .map((text, idx) => ({ idx, text, resolved: props.resolved.has(idx) }))
    .filter((q) => !props.dismissed.has(q.idx))
)

/** 排序:未处理在前,已处理在后,稳定排序保留原始 idx 顺序。 */
const sortedQuestions = computed(() => {
  const list = allQuestions.value.slice()
  list.sort((a, b) => {
    if (a.resolved === b.resolved) return a.idx - b.idx
    return a.resolved ? 1 : -1
  })
  return list
})

/** 实际渲染的前 3 条。 */
const visibleQuestions = computed(() => sortedQuestions.value.slice(0, MAX_VISIBLE))

/** 折叠掉的剩余条数。 */
const overflowCount = computed(
  () => Math.max(0, sortedQuestions.value.length - MAX_VISIBLE)
)

const onAdopt = (q) => {
  if (q.resolved) return
  emit('adopt', q)
}
const onDismiss = (q) => emit('dismiss', q)
</script>

<template>
  <div v-if="sortedQuestions.length > 0" class="missing-questions" data-test="missing-questions-card">
    <header class="missing-questions__head">
      <HelpCircle class="w-3.5 h-3.5 text-purple-300" />
      <span class="text-sm font-semibold text-gray-100">内容优化建议</span>
      <span class="ml-auto text-[10px] font-mono uppercase tracking-wider text-gray-500">
        {{ sortedQuestions.length }} 项
      </span>
    </header>
    <ul class="missing-questions__body">
      <li
        v-for="q in visibleQuestions"
        :key="q.idx"
        class="missing-questions__item"
        :class="{ 'is-resolved': q.resolved }"
      >
        <p class="missing-questions__text">{{ q.text }}</p>
        <div class="missing-questions__actions">
          <span v-if="q.resolved" class="missing-questions__resolved-tag">
            <CheckCircle2 class="w-3 h-3" />
            已处理
          </span>
          <template v-else>
            <button
              type="button"
              class="missing-questions__btn missing-questions__btn--primary"
              @click="onAdopt(q)"
            >
              <Check class="w-3 h-3" />
              采纳
            </button>
            <button
              type="button"
              class="missing-questions__btn"
              @click="onDismiss(q)"
            >
              <X class="w-3 h-3" />
              忽略
            </button>
          </template>
        </div>
      </li>
      <li v-if="overflowCount > 0" class="missing-questions__overflow">
        还有 {{ overflowCount }} 条建议待处理
      </li>
    </ul>
  </div>
</template>

<style scoped>
.missing-questions {
  background: rgba(168, 85, 247, 0.04);
  border: 1px solid rgba(168, 85, 247, 0.25);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  overflow: hidden;
}
.missing-questions__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(168, 85, 247, 0.18);
}

/* Beta 收口:面板自然高度,不再做内部滚动。
   MAX_VISIBLE=3 + 单行 overflow 注脚使总高度可控,无需 max-height/overflow-y/自定义 scrollbar。
   外层 Workspace 中栏已经有自己的滚动容器(.rb-form),内部不再叠一层小滚动条,
   避免「滚动条套滚动条」、按钮被裁、长建议触发误滚动等问题。 */
.missing-questions__body {
  list-style: none;
  margin: 0;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.missing-questions__item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  transition: opacity 0.18s ease, background 0.18s ease;
}
.missing-questions__item.is-resolved {
  opacity: 0.6;
  background: rgba(16, 185, 129, 0.05);
  border-color: rgba(16, 185, 129, 0.18);
}
.missing-questions__item.is-resolved .missing-questions__text {
  text-decoration: line-through;
  color: rgba(229, 231, 235, 0.55);
}
.missing-questions__text {
  flex: 1;
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: rgba(229, 231, 235, 0.9);
}
.missing-questions__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.missing-questions__btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(229, 231, 235, 0.7);
  background: transparent;
  cursor: pointer;
  transition: all 0.18s ease;
}
.missing-questions__btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.missing-questions__btn--primary {
  border-color: rgba(168, 85, 247, 0.4);
  color: rgb(216, 180, 254);
  background: rgba(168, 85, 247, 0.1);
}
.missing-questions__btn--primary:hover {
  background: rgba(168, 85, 247, 0.18);
}
.missing-questions__resolved-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: rgb(110, 231, 183);
  background: rgba(16, 185, 129, 0.1);
}
.missing-questions__overflow {
  list-style: none;
  text-align: center;
  font-size: 11px;
  color: rgba(156, 163, 175, 0.7);
  padding: 4px 6px;
  font-style: italic;
}
</style>
