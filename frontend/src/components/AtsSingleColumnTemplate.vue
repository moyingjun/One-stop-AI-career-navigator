<script setup>
/**
 * AtsSingleColumnTemplate.vue —— ATS 单栏模板
 *
 * 满足 Requirement 7.1 / 7.2 / 7.6 / 7.7 / 7.8 / 8.1 / 8.2 / 8.5:
 *   - 单栏 <section>+<h2>+<ul> 布局
 *   - 不使用多栏 / 嵌套表格 / <textarea> / fixed 页眉页脚 / position: absolute|fixed
 *   - 仅以只读方式消费 Resume_JSON
 *   - 不使用 v-html / eval / new Function
 *   - 字段值通过 DOM 文字节点输出,可拖选可复制
 *   - 空 Section 整体隐藏
 */
import { computed } from 'vue'

const props = defineProps({
  resume: { type: Object, required: true }
})

const cellText = (cell) => {
  if (!cell) return ''
  if (typeof cell.value === 'string') return cell.value.trim()
  if (Array.isArray(cell.value)) return cell.value.filter(Boolean).join(', ')
  if (typeof cell.value === 'number') return String(cell.value)
  return ''
}

const cellList = (cell) => {
  if (!cell) return []
  if (Array.isArray(cell.value)) return cell.value.filter((v) => typeof v === 'string' && v.trim())
  if (typeof cell.value === 'string' && cell.value.trim()) return [cell.value.trim()]
  return []
}

const itemHasContent = (item, fields) => {
  if (!item) return false
  for (const f of fields) {
    if (cellText(item[f])) return true
    if (cellList(item[f]).length > 0) return true
  }
  return false
}

// ─── basics ──
const basicsLines = computed(() => {
  const b = props.resume?.basics || {}
  const out = []
  const name = cellText(b.name)
  if (name) out.push({ key: 'name', value: name, prominent: true })
  const role = cellText(b.targetRole)
  if (role) out.push({ key: 'targetRole', value: role })
  const contactBits = []
  for (const f of ['email', 'phone', 'city', 'websiteOrRepo']) {
    const v = cellText(b[f])
    if (v) contactBits.push(v)
  }
  if (contactBits.length > 0) out.push({ key: 'contact', value: contactBits.join(' · ') })
  return out
})

// ─── 通用数组 Section ──
const educationItems = computed(() =>
  (props.resume?.education?.items || []).filter((i) =>
    itemHasContent(i, ['school', 'degree', 'major', 'startDate', 'endDate', 'gpa', 'highlights'])
  )
)
const projectItems = computed(() =>
  (props.resume?.projects?.items || []).filter((i) =>
    itemHasContent(i, ['name', 'role', 'stack', 'startDate', 'endDate', 'summary', 'highlights', 'link'])
  )
)
const experienceItems = computed(() =>
  (props.resume?.experience?.items || []).filter((i) =>
    itemHasContent(i, ['company', 'title', 'startDate', 'endDate', 'location', 'summary', 'highlights'])
  )
)
const awardItems = computed(() =>
  (props.resume?.awards?.items || []).filter((i) =>
    itemHasContent(i, ['name', 'issuer', 'date', 'summary'])
  )
)
const certificateItems = computed(() =>
  (props.resume?.certificates?.items || []).filter((i) =>
    itemHasContent(i, ['name', 'issuer', 'issueDate', 'expireDate', 'credentialId'])
  )
)
const skillGroups = computed(() =>
  (props.resume?.skills?.items || []).filter((g) => {
    if (!g) return false
    const cat = (g.category || '').trim()
    const subs = (g.items || []).filter((s) => s && (s.name || '').trim())
    return cat || subs.length > 0
  })
)

const dateRange = (item) => {
  const a = cellText(item?.startDate)
  const b = cellText(item?.endDate)
  if (a && b) return `${a} — ${b}`
  if (a) return a
  if (b) return b
  return ''
}
</script>

<template>
  <article class="ats-tpl">
    <!-- basics -->
    <header class="ats-tpl__header" v-if="basicsLines.length > 0">
      <h1 v-if="basicsLines[0]?.key === 'name'" class="ats-tpl__name">
        {{ basicsLines[0].value }}
      </h1>
      <p
        v-for="line in basicsLines.filter((l) => l.key !== 'name')"
        :key="line.key"
        class="ats-tpl__contact"
      >
        {{ line.value }}
      </p>
    </header>

    <!-- experience -->
    <section v-if="experienceItems.length > 0" class="ats-tpl__section">
      <h2>工作经历</h2>
      <div v-for="(item, idx) in experienceItems" :key="`exp-${idx}`" class="ats-tpl__item">
        <p class="ats-tpl__item-head">
          <strong v-if="cellText(item.title)">{{ cellText(item.title) }}</strong>
          <span v-if="cellText(item.title) && cellText(item.company)"> · </span>
          <span v-if="cellText(item.company)">{{ cellText(item.company) }}</span>
          <span v-if="dateRange(item)" class="ats-tpl__date"> · {{ dateRange(item) }}</span>
          <span v-if="cellText(item.location)"> · {{ cellText(item.location) }}</span>
        </p>
        <p v-if="cellText(item.summary)" class="ats-tpl__summary">{{ cellText(item.summary) }}</p>
        <ul v-if="cellList(item.highlights).length > 0">
          <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
        </ul>
      </div>
    </section>

    <!-- projects -->
    <section v-if="projectItems.length > 0" class="ats-tpl__section">
      <h2>项目经历</h2>
      <div v-for="(item, idx) in projectItems" :key="`proj-${idx}`" class="ats-tpl__item">
        <p class="ats-tpl__item-head">
          <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
          <span v-if="cellText(item.role)"> · {{ cellText(item.role) }}</span>
          <span v-if="dateRange(item)" class="ats-tpl__date"> · {{ dateRange(item) }}</span>
          <span v-if="cellText(item.link)"> · {{ cellText(item.link) }}</span>
        </p>
        <p v-if="cellList(item.stack).length > 0" class="ats-tpl__summary">
          <strong class="ats-tpl__label">技术栈:</strong>
          <span>{{ cellList(item.stack).join(', ') }}</span>
        </p>
        <p v-if="cellText(item.summary)" class="ats-tpl__summary">{{ cellText(item.summary) }}</p>
        <ul v-if="cellList(item.highlights).length > 0">
          <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
        </ul>
      </div>
    </section>

    <!-- education -->
    <section v-if="educationItems.length > 0" class="ats-tpl__section">
      <h2>教育经历</h2>
      <div v-for="(item, idx) in educationItems" :key="`edu-${idx}`" class="ats-tpl__item">
        <p class="ats-tpl__item-head">
          <strong v-if="cellText(item.school)">{{ cellText(item.school) }}</strong>
          <span v-if="cellText(item.degree)"> · {{ cellText(item.degree) }}</span>
          <span v-if="cellText(item.major)"> · {{ cellText(item.major) }}</span>
          <span v-if="dateRange(item)" class="ats-tpl__date"> · {{ dateRange(item) }}</span>
          <span v-if="cellText(item.gpa)"> · GPA {{ cellText(item.gpa) }}</span>
        </p>
        <ul v-if="cellList(item.highlights).length > 0">
          <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
        </ul>
      </div>
    </section>

    <!-- skills -->
    <section v-if="skillGroups.length > 0" class="ats-tpl__section">
      <h2>技能</h2>
      <ul class="ats-tpl__skills">
        <li v-for="(g, gIdx) in skillGroups" :key="`skg-${gIdx}`">
          <strong v-if="g.category" class="ats-tpl__label">{{ g.category }}:</strong>
          <span>{{
            (g.items || [])
              .filter((s) => s && (s.name || '').trim())
              .map((s) => s.name)
              .join(', ')
          }}</span>
        </li>
      </ul>
    </section>

    <!-- awards -->
    <section v-if="awardItems.length > 0" class="ats-tpl__section">
      <h2>获奖</h2>
      <ul>
        <li v-for="(item, idx) in awardItems" :key="`award-${idx}`">
          <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
          <span v-if="cellText(item.issuer)"> · {{ cellText(item.issuer) }}</span>
          <span v-if="cellText(item.date)" class="ats-tpl__date"> · {{ cellText(item.date) }}</span>
          <span v-if="cellText(item.summary)"> · {{ cellText(item.summary) }}</span>
        </li>
      </ul>
    </section>

    <!-- certificates -->
    <section v-if="certificateItems.length > 0" class="ats-tpl__section">
      <h2>证书</h2>
      <ul>
        <li v-for="(item, idx) in certificateItems" :key="`cert-${idx}`">
          <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
          <span v-if="cellText(item.issuer)"> · {{ cellText(item.issuer) }}</span>
          <span v-if="cellText(item.issueDate)"> · {{ cellText(item.issueDate) }}</span>
          <span v-if="cellText(item.expireDate)"> ~ {{ cellText(item.expireDate) }}</span>
          <span v-if="cellText(item.credentialId)"> · 编号 {{ cellText(item.credentialId) }}</span>
        </li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.ats-tpl {
  background: #ffffff;
  color: #111;
  padding: 36px 44px;
  font-family: ui-sans-serif, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.65;
  user-select: text;
  pointer-events: auto;
  min-height: 100%;
  box-sizing: border-box;
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
}
.ats-tpl__header {
  border-bottom: 2px solid #1f2937;
  margin-bottom: 18px;
  padding-bottom: 12px;
}
.ats-tpl__name {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 6px;
  color: #0f172a;
  letter-spacing: 0.3px;
}
.ats-tpl__contact {
  font-size: 12.5px;
  color: #475569;
  margin: 2px 0;
}
.ats-tpl__section {
  margin: 18px 0;
}
.ats-tpl__section h2 {
  font-size: 14.5px;
  font-weight: 700;
  border-bottom: 1px solid #cbd5e1;
  padding-bottom: 4px;
  margin: 0 0 10px;
  color: #0f172a;
  letter-spacing: 0.2px;
  text-transform: none;
}
.ats-tpl__item {
  margin-bottom: 12px;
}
.ats-tpl__item-head {
  margin: 0 0 4px;
  color: #0f172a;
  font-size: 13.5px;
}
.ats-tpl__item-head strong {
  font-weight: 700;
}
.ats-tpl__date {
  color: #64748b;
  font-size: 12px;
}
.ats-tpl__label {
  font-weight: 600;
  color: #1f2937;
  margin-right: 4px;
}
.ats-tpl__summary {
  margin: 4px 0;
  color: #1f2937;
  font-size: 12.75px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.ats-tpl__section ul {
  margin: 6px 0 6px 24px;
  padding: 0;
}
.ats-tpl__section ul li {
  margin: 3px 0;
  color: #1f2937;
  line-height: 1.55;
}
.ats-tpl__skills li {
  list-style: disc;
  margin-left: 18px;
}
</style>
