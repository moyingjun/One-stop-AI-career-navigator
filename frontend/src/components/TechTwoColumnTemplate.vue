<script setup>
/**
 * TechTwoColumnTemplate.vue —— 技术岗双栏模板
 *
 * 满足 Requirement 7.1 / 7.3 / 7.6 / 7.7 / 7.8 / 8.1 / 8.2 / 8.5:
 *   - CSS Grid 双栏:左 240px(基础信息 + 技能 + 证书),右 1fr(项目 + 工作 + 教育)
 *   - 同一字段值不同时出现在左右两栏
 *   - 仅只读消费 Resume_JSON,无 v-html / eval / position: absolute|fixed
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

const basics = computed(() => props.resume?.basics || {})
const hasBasicsLeft = computed(() => {
  return ['name', 'targetRole', 'email', 'phone', 'city', 'websiteOrRepo'].some(
    (f) => cellText(basics.value[f])
  )
})

const skillGroups = computed(() =>
  (props.resume?.skills?.items || []).filter((g) => {
    if (!g) return false
    const cat = (g.category || '').trim()
    const subs = (g.items || []).filter((s) => s && (s.name || '').trim())
    return cat || subs.length > 0
  })
)

const certificateItems = computed(() =>
  (props.resume?.certificates?.items || []).filter((i) =>
    itemHasContent(i, ['name', 'issuer', 'issueDate', 'expireDate', 'credentialId'])
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
const educationItems = computed(() =>
  (props.resume?.education?.items || []).filter((i) =>
    itemHasContent(i, ['school', 'degree', 'major', 'startDate', 'endDate', 'gpa', 'highlights'])
  )
)
const awardItems = computed(() =>
  (props.resume?.awards?.items || []).filter((i) =>
    itemHasContent(i, ['name', 'issuer', 'date', 'summary'])
  )
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
  <article class="tech-tpl">
    <!-- 左栏:基础信息 + 技能 + 证书 -->
    <aside class="tech-tpl__left">
      <section v-if="hasBasicsLeft" class="tech-tpl__block">
        <h2>基本信息</h2>
        <p v-if="cellText(basics.name)" class="tech-tpl__name">{{ cellText(basics.name) }}</p>
        <p v-if="cellText(basics.targetRole)" class="tech-tpl__role">{{ cellText(basics.targetRole) }}</p>
        <ul class="tech-tpl__contact">
          <li v-if="cellText(basics.email)">📧 {{ cellText(basics.email) }}</li>
          <li v-if="cellText(basics.phone)">📱 {{ cellText(basics.phone) }}</li>
          <li v-if="cellText(basics.city)">📍 {{ cellText(basics.city) }}</li>
          <li v-if="cellText(basics.websiteOrRepo)">🔗 {{ cellText(basics.websiteOrRepo) }}</li>
        </ul>
      </section>

      <section v-if="skillGroups.length > 0" class="tech-tpl__block">
        <h2>技能</h2>
        <div v-for="(g, gIdx) in skillGroups" :key="`skg-${gIdx}`" class="tech-tpl__skill-group">
          <p v-if="g.category" class="tech-tpl__skill-category">{{ g.category }}</p>
          <ul>
            <li v-for="(s, sIdx) in (g.items || []).filter((x) => x && (x.name || '').trim())" :key="sIdx">
              {{ s.name }}
            </li>
          </ul>
        </div>
      </section>

      <section v-if="certificateItems.length > 0" class="tech-tpl__block">
        <h2>证书</h2>
        <ul>
          <li v-for="(item, idx) in certificateItems" :key="`cert-${idx}`">
            <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
            <span v-if="cellText(item.issuer)"> · {{ cellText(item.issuer) }}</span>
            <span v-if="cellText(item.issueDate)" class="tech-tpl__muted"> · {{ cellText(item.issueDate) }}</span>
          </li>
        </ul>
      </section>
    </aside>

    <!-- 右栏:项目 + 工作 + 教育 + 获奖 -->
    <main class="tech-tpl__right">
      <section v-if="experienceItems.length > 0" class="tech-tpl__section">
        <h2>工作经历</h2>
        <div v-for="(item, idx) in experienceItems" :key="`exp-${idx}`" class="tech-tpl__item">
          <p class="tech-tpl__item-head">
            <strong v-if="cellText(item.title)">{{ cellText(item.title) }}</strong>
            <span v-if="cellText(item.company)"> · {{ cellText(item.company) }}</span>
            <span v-if="dateRange(item)" class="tech-tpl__muted"> · {{ dateRange(item) }}</span>
            <span v-if="cellText(item.location)"> · {{ cellText(item.location) }}</span>
          </p>
          <p v-if="cellText(item.summary)" class="tech-tpl__summary">{{ cellText(item.summary) }}</p>
          <ul v-if="cellList(item.highlights).length > 0">
            <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
          </ul>
        </div>
      </section>

      <section v-if="projectItems.length > 0" class="tech-tpl__section">
        <h2>项目经历</h2>
        <div v-for="(item, idx) in projectItems" :key="`proj-${idx}`" class="tech-tpl__item">
          <p class="tech-tpl__item-head">
            <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
            <span v-if="cellText(item.role)"> · {{ cellText(item.role) }}</span>
            <span v-if="dateRange(item)" class="tech-tpl__muted"> · {{ dateRange(item) }}</span>
          </p>
          <p v-if="cellList(item.stack).length > 0" class="tech-tpl__summary">
            <strong class="tech-tpl__label">技术栈:</strong>
            <span>{{ cellList(item.stack).join(', ') }}</span>
          </p>
          <p v-if="cellText(item.link)" class="tech-tpl__muted">{{ cellText(item.link) }}</p>
          <p v-if="cellText(item.summary)" class="tech-tpl__summary">{{ cellText(item.summary) }}</p>
          <ul v-if="cellList(item.highlights).length > 0">
            <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
          </ul>
        </div>
      </section>

      <section v-if="educationItems.length > 0" class="tech-tpl__section">
        <h2>教育经历</h2>
        <div v-for="(item, idx) in educationItems" :key="`edu-${idx}`" class="tech-tpl__item">
          <p class="tech-tpl__item-head">
            <strong v-if="cellText(item.school)">{{ cellText(item.school) }}</strong>
            <span v-if="cellText(item.degree)"> · {{ cellText(item.degree) }}</span>
            <span v-if="cellText(item.major)"> · {{ cellText(item.major) }}</span>
            <span v-if="dateRange(item)" class="tech-tpl__muted"> · {{ dateRange(item) }}</span>
          </p>
          <p v-if="cellText(item.gpa)" class="tech-tpl__muted">GPA {{ cellText(item.gpa) }}</p>
          <ul v-if="cellList(item.highlights).length > 0">
            <li v-for="(h, i) in cellList(item.highlights)" :key="i">{{ h }}</li>
          </ul>
        </div>
      </section>

      <section v-if="awardItems.length > 0" class="tech-tpl__section">
        <h2>获奖</h2>
        <ul>
          <li v-for="(item, idx) in awardItems" :key="`award-${idx}`">
            <strong v-if="cellText(item.name)">{{ cellText(item.name) }}</strong>
            <span v-if="cellText(item.issuer)"> · {{ cellText(item.issuer) }}</span>
            <span v-if="cellText(item.date)" class="tech-tpl__muted"> · {{ cellText(item.date) }}</span>
          </li>
        </ul>
      </section>
    </main>
  </article>
</template>

<style scoped>
.tech-tpl {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 28px;
  background: #ffffff;
  color: #111;
  padding: 36px;
  font-family: ui-sans-serif, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.65;
  user-select: text;
  pointer-events: auto;
  min-height: 100%;
  box-sizing: border-box;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
}

.tech-tpl__left {
  background: #f3f6f9;
  border-radius: 6px;
  padding: 18px;
  border-right: 0;
}
.tech-tpl__right {
  padding: 0;
}

.tech-tpl__block {
  margin-bottom: 20px;
}
.tech-tpl__block h2,
.tech-tpl__section h2 {
  font-size: 13.5px;
  font-weight: 700;
  border-bottom: 1.5px solid #1f2937;
  padding-bottom: 4px;
  margin: 0 0 8px;
  color: #1f2937;
  letter-spacing: 0.2px;
}

.tech-tpl__name {
  font-size: 19px;
  font-weight: 700;
  margin: 4px 0 2px;
  color: #0f172a;
}
.tech-tpl__role {
  font-size: 12.5px;
  color: #475569;
  margin: 0 0 10px;
}
.tech-tpl__contact {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 12px;
  color: #334155;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tech-tpl__skill-group {
  margin-bottom: 10px;
}
.tech-tpl__skill-category {
  font-size: 12px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 3px;
}
.tech-tpl__skill-group ul {
  list-style: disc;
  margin: 0 0 0 18px;
  padding: 0;
  font-size: 12px;
  color: #334155;
  line-height: 1.55;
}

.tech-tpl__section {
  margin-bottom: 20px;
}
.tech-tpl__item {
  margin-bottom: 12px;
}
.tech-tpl__item-head {
  margin: 0 0 3px;
  font-size: 13.5px;
}
.tech-tpl__label {
  font-weight: 600;
  color: #1f2937;
  margin-right: 4px;
}
.tech-tpl__summary {
  margin: 4px 0;
  font-size: 12.75px;
  color: #1f2937;
  line-height: 1.6;
  white-space: pre-wrap;
}
.tech-tpl__muted {
  color: #64748b;
  font-size: 12px;
}
.tech-tpl__section ul,
.tech-tpl__block ul {
  margin: 6px 0 6px 22px;
  padding: 0;
}
.tech-tpl__section ul li,
.tech-tpl__block ul li {
  margin: 3px 0;
  line-height: 1.55;
}
</style>
