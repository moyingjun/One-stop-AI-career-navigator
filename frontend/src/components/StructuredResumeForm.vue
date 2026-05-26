<script setup>
/**
 * StructuredResumeForm.vue —— 结构化简历表单(Workspace 中栏)
 *
 * 满足 Requirement 6.1 / 6.2 / 6.3 / 6.5 / 6.6:
 *   - 按 basics → education → skills → projects → experience → awards → certificates 顺序渲染
 *   - 每个字段携带 Field_Status 角标 + 警示色边框
 *   - 编辑触发 store.patchField,内部维护 Field_Status / missingFields
 *   - 数组型 Section 提供新增 / 删除条目
 *
 * Beta 收口约束(本轮):
 *   - 内容优化建议 targetPath 在 missingQuestions 引用变化时一次性解析并缓存,
 *     用户填写字段不会让定位漂移到另一字段。
 *   - 采纳定位 + 已处理判断使用同一份 targetPath 缓存。
 *   - 仅写 store,不直接命中 HTTP
 *   - 不 import 任何 RAG / Diagnosis / Interview / Career 服务
 */
import { computed, nextTick, ref, watch } from 'vue'
import {
  Plus,
  Trash2,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  CheckCircle2
} from 'lucide-vue-next'
import { useResumeBuilderStore } from '@/stores/resumeBuilderStore.js'
import {
  BASICS_FIELDS,
  ITEM_FIELDS,
  FIELD_STATUS,
  ARRAY_SECTION_MAX,
  SKILLS_GROUP_MAX,
  SKILLS_ITEM_MAX
} from '@/utils/resumeJsonSchema.js'
import MissingQuestionsCard from './MissingQuestionsCard.vue'
import ConfirmResumeButton from './ConfirmResumeButton.vue'
import { showToast } from '@/utils/uiFallbacks.js'

const store = useResumeBuilderStore()

const resumeJson = computed(() => store.resumeJson)

// 中文字段名映射
const FIELD_LABELS = {
  // basics
  name: '姓名',
  targetRole: '目标岗位',
  email: '邮箱',
  phone: '手机',
  city: '城市',
  websiteOrRepo: '个人主页 / 仓库',
  // education
  school: '学校',
  degree: '学历',
  major: '专业',
  startDate: '开始时间',
  endDate: '结束时间',
  gpa: 'GPA',
  highlights: '亮点 / 课程',
  // projects
  role: '角色',
  stack: '技术栈',
  summary: '描述',
  link: '链接',
  // experience
  company: '公司',
  title: '职位',
  location: '城市',
  // awards
  issuer: '颁发方',
  date: '时间',
  // certificates
  issueDate: '发证时间',
  expireDate: '失效时间',
  credentialId: '证书编号'
}

const SECTION_LABELS = {
  basics: '基础信息',
  education: '教育经历',
  skills: '技能',
  projects: '项目经历',
  experience: '工作经历',
  awards: '获奖',
  certificates: '证书'
}

const STATUS_TIP = {
  missing: 'AI 未在草稿中找到该字段',
  needs_confirmation: '需要你确认',
  inferred_from_text: 'AI 根据上下文推断,请复核',
  confirmed: '已确认'
}

const STATUS_LABEL = {
  missing: '缺失',
  needs_confirmation: '待确认',
  inferred_from_text: '推断',
  confirmed: '已填'
}

const labelOf = (key) => FIELD_LABELS[key] || key

// ─── basics ──
const onBasicsEdit = (field, value) => {
  store.patchField(`basics.${field}`, value)
}

// ─── 数组 Section ──
const onItemEdit = (section, idx, field, value) => {
  store.patchField(`${section}.items[${idx}].${field}`, value)
}

const onArrayEdit = (section, idx, field, rawValue) => {
  // highlights / stack:从 textarea 字符串拆分
  store.patchField(`${section}.items[${idx}].${field}`, rawValue)
}

const onAddItem = (section) => {
  store.addArrayItem(`${section}.items`)
}

const onRemoveItem = (section, idx) => {
  store.removeArrayItem(`${section}.items`, idx)
}

// ─── skills ──
const onSkillCategoryEdit = (gIdx, value) => {
  store.patchField(`skills.items[${gIdx}].category`, value)
}

const onSkillNameEdit = (gIdx, sIdx, value) => {
  store.patchField(`skills.items[${gIdx}].items[${sIdx}].name`, value)
}

const onAddSkillGroup = () => {
  store.addArrayItem('skills.items')
}

const onRemoveSkillGroup = (gIdx) => {
  store.removeArrayItem('skills.items', gIdx)
}

const onAddSkillItem = (gIdx) => {
  store.addArrayItem(`skills.items[${gIdx}].items`)
}

const onRemoveSkillItem = (gIdx, sIdx) => {
  store.removeArrayItem(`skills.items[${gIdx}].items`, sIdx)
}

// ─── 数组上限提示 ──
const arraySectionFull = (section) => {
  return (resumeJson.value?.[section]?.items?.length || 0) >= ARRAY_SECTION_MAX
}
const skillsGroupFull = computed(
  () => (resumeJson.value?.skills?.items?.length || 0) >= SKILLS_GROUP_MAX
)
const skillsItemFull = (gIdx) =>
  (resumeJson.value?.skills?.items?.[gIdx]?.items?.length || 0) >= SKILLS_ITEM_MAX

// ─── missing_questions 「采纳」交互(Beta 收口版) ──
//
// 设计要点:
//   1. 每条建议的 idx → targetPath 在 missingQuestions 引用变化(=重新抽取)时一次性解析并缓存。
//   2. 缓存 entry 形如 { kind: 'field'|'section'|'unresolvable', path: string|null, section: string|null }。
//   3. 用户填写字段后 resolver 不会重新跑,定位不会漂移到另一字段(避免 Beta 收口前的"漂移"现象)。
//   4. 「采纳」按钮:
//        - kind=field 且字段为空 → 滚动 + 闪光 + focus
//        - kind=field 且字段已填 → 仍然滚动 + 闪光 + focus,toast「该字段已有内容,可继续修改」
//        - kind=section(命中 section 但暂无 items)→ 滚动到 section 头 / 新增按钮,toast「请先新增一条内容」
//        - kind=unresolvable → toast「请在相关字段中手动补充」
//   5. 「已处理」判断:用同一份 targetPath 缓存读 cell,避免与定位规则不一致。

const FIELD_KEYWORDS = {
  // basics
  name: ['姓名', '名字', 'name'],
  targetRole: ['目标岗位', '目标职位', '岗位', '求职岗位', '职位方向', 'target role', 'role'],
  email: ['邮箱', '电子邮件', '邮件', 'email', 'mail'],
  phone: ['手机', '电话', '联系电话', 'phone', 'mobile'],
  city: ['所在城市', '城市', '所在地', '居住地', 'city', 'location'],
  websiteOrRepo: ['个人主页', '主页', '仓库', '代码仓库', '链接', 'github', 'repo', 'website', 'homepage'],
  // education
  school: ['学校', '院校', '大学', 'school'],
  degree: ['学历', '学位', 'degree'],
  major: ['专业', '主修', 'major'],
  startDate: ['开始时间', '起始时间', '入学时间', '入职时间', '起始日期', 'start'],
  endDate: ['结束时间', '终止时间', '毕业时间', '离职时间', '在校时间', '工作时间', 'end'],
  gpa: ['gpa', '成绩', '绩点'],
  highlights: ['亮点', '课程', '成就', '关键描述', 'highlights'],
  // projects
  role: ['角色', '担任', '职责', 'role'],
  stack: ['技术栈', '技术', '使用技术', 'stack', 'tech'],
  summary: ['描述', '简介', '介绍', '摘要', 'summary', 'description'],
  link: ['项目链接', '链接', 'link', 'url'],
  // experience
  company: ['公司', '雇主', 'company', 'employer'],
  title: ['职位', '岗位', '职称', 'title'],
  location: ['工作城市', '所在城市', '工作地点', 'location'],
  // awards
  issuer: ['颁发方', '颁发机构', '发证机构', 'issuer'],
  date: ['获奖时间', '时间', '日期', 'date'],
  // certificates
  issueDate: ['发证时间', '颁发时间', '取得时间'],
  expireDate: ['失效时间', '过期时间', '到期'],
  credentialId: ['证书编号', '编号', 'id', 'credential'],
}

const SECTION_KEYWORDS = {
  education:    ['教育', '学校', '院校', '大学', 'education'],
  projects:     ['项目', '仓库', 'project'],
  experience:   ['工作经历', '实习', '工作', 'experience', 'intern'],
  awards:       ['获奖', '奖项', 'award'],
  certificates: ['证书', 'certificate', 'cert'],
}

/**
 * 一次性解析 question text → 目标(field 路径 / section 路径 / 不可解析)。
 * 仅在 missingQuestions 引用变更时调用,后续不再重跑(避免漂移)。
 *
 * 评分策略:
 *   - 关键字命中加分:取「命中关键字中最长那条」的字符长度作为命中权重(specificity)。
 *     这样 `'目标岗位'`(4) 命中 targetRole 时压过 `'岗位'`(2) 命中 experience.title,
 *     避免短关键字 + idx 加分把更精确的字段挤掉。
 *   - missing/needs_confirmation 字段额外 +10(LLM 追问通常针对未填字段)
 *   - section 关键字命中再加一份 specificity(同样按最长匹配长度计权)
 *   - 数组首项轻微偏置 +1
 *
 * @returns {{kind: 'field', path: string} | {kind: 'section', section: string} | {kind: 'unresolvable'}}
 */
const resolveTargetForQuestion = (questionText, snapshot) => {
  const text = String(questionText || '').toLowerCase()
  if (!text || !snapshot) return { kind: 'unresolvable' }

  /** 取命中关键字中最长那条的长度;未命中返回 0。 */
  const bestKeywordLen = (keywords) => {
    let best = 0
    for (const kw of keywords) {
      const k = String(kw || '').toLowerCase()
      if (k && text.includes(k) && k.length > best) best = k.length
    }
    return best
  }

  const candidates = []

  // basics
  for (const f of BASICS_FIELDS) {
    const cell = snapshot.basics?.[f]
    if (!cell) continue
    const keywords = FIELD_KEYWORDS[f] || [f]
    const kwLen = bestKeywordLen(keywords)
    if (kwLen > 0) {
      const isMissing = cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION
      const score = (isMissing ? 10 : 1) + kwLen
      candidates.push({ path: `basics.${f}`, score })
    }
  }

  // 数组型 Section 字段
  // 仅当 question 中明确出现该 section 的关键字(工作/项目/教育/获奖/证书)时,才允许 array 候选参与排序;
  // 否则像「请提供所在城市」这类 basics 问题会被 experience.location 等同义字段拐跑。
  for (const sec of Object.keys(ITEM_FIELDS)) {
    const items = snapshot[sec]?.items || []
    const sectionKwLen = bestKeywordLen(SECTION_KEYWORDS[sec] || [])
    if (sectionKwLen === 0) continue
    items.forEach((item, idx) => {
      ITEM_FIELDS[sec].forEach((f) => {
        const cell = item?.[f]
        if (!cell) return
        const keywords = FIELD_KEYWORDS[f] || [f]
        const kwLen = bestKeywordLen(keywords)
        if (kwLen === 0) return
        const isMissing = cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION
        let score = (isMissing ? 10 : 1) + kwLen + sectionKwLen
        if (idx === 0) score += 1
        candidates.push({ path: `${sec}.items[${idx}].${f}`, score })
      })
    })
  }

  if (candidates.length > 0) {
    candidates.sort((a, b) => b.score - a.score)
    return { kind: 'field', path: candidates[0].path }
  }

  // 没有命中具体字段:看看是否命中"空 section"(此时引导用户先点新增)
  for (const sec of Object.keys(SECTION_KEYWORDS)) {
    const kws = SECTION_KEYWORDS[sec]
    const hit = kws.some((kw) => text.includes(String(kw).toLowerCase()))
    const items = snapshot[sec]?.items || []
    if (hit && items.length === 0) {
      return { kind: 'section', section: sec }
    }
  }

  return { kind: 'unresolvable' }
}

/**
 * idx → 目标路径缓存。引用变化时(=新一轮 extract 抽取替换 missingQuestions 数组),
 * 整张 Map 重建一次,后续用户 patchField 不会改变它,从根本上消除漂移。
 */
const targetCache = ref(new Map())

watch(
  () => store.missingQuestions,
  (list) => {
    const next = new Map()
    const snapshot = resumeJson.value
    const arr = Array.isArray(list) ? list : []
    arr.forEach((text, idx) => {
      next.set(idx, resolveTargetForQuestion(text, snapshot))
    })
    targetCache.value = next
  },
  { immediate: true }
)

const getTargetForIdx = (idx) => {
  return targetCache.value.get(idx) || { kind: 'unresolvable' }
}

/** 滚动 + 高亮 + 聚焦字段。 */
const focusFieldByPath = async (path) => {
  if (!path) return false
  await nextTick()
  const el = document.querySelector(`[data-rb-field="${path}"]`)
  if (!el) return false
  const fieldBox = el.closest('.rb-field') || el.closest('.rb-skill__row') || el
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  fieldBox.classList.remove('rb-field--highlight')
  void fieldBox.offsetWidth
  fieldBox.classList.add('rb-field--highlight')
  setTimeout(() => fieldBox.classList.remove('rb-field--highlight'), 3000)
  setTimeout(() => {
    if (typeof el.focus === 'function') {
      try { el.focus({ preventScroll: true }) } catch { el.focus() }
    }
  }, 200)
  return true
}

/** 滚动到 section 头(命中空 section 时引导用户先点新增)。 */
const focusSection = async (section) => {
  if (!section) return false
  await nextTick()
  const addBtn = document.querySelector(`[data-test="rb-${section}-add"]`)
  const target = addBtn || document.querySelector(`[data-test="resume-builder-form"]`)
  if (!target) return false
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  // 给新增按钮一次性闪光提示(不复用 rb-field--highlight 以免与字段语义混淆)
  if (addBtn) {
    addBtn.classList.remove('rb-section__add--blink')
    void addBtn.offsetWidth
    addBtn.classList.add('rb-section__add--blink')
    setTimeout(() => addBtn.classList.remove('rb-section__add--blink'), 2400)
  }
  return true
}

const onAdoptQuestion = async (q) => {
  const target = getTargetForIdx(q.idx)
  if (target.kind === 'field' && target.path) {
    const cell = readCellByPath(resumeJson.value, target.path)
    const ok = await focusFieldByPath(target.path)
    if (!ok) {
      // DOM 还没渲染到该字段(理论上不发生,因为 path 是从 snapshot 解析来的) → 兜底
      showToast('请在相关字段中手动补充', { type: 'success' })
      return
    }
    if (cell && isCellFilled(cell)) {
      // 字段已有内容:仍闪光 + focus,但提示用户去修改而不是空填
      showToast('该字段已有内容,可继续修改', { type: 'success' })
    }
    return
  }
  if (target.kind === 'section' && target.section) {
    await focusSection(target.section)
    showToast('请先新增一条内容', { type: 'success' })
    return
  }
  // unresolvable
  showToast('请在相关字段中手动补充', { type: 'success' })
  const formEl = document.querySelector('[data-test="resume-builder-form"]')
  if (formEl) formEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const onDismissQuestion = (q) => {
  store.dismissQuestion(q.idx)
}

/**
 * 已处理建议集合 — 当 idx 缓存的 path 对应字段已被填写(value 非空且 status 不是 missing/needs_confirmation)
 * 时,该条建议视为「已处理」,卡片中显示灰色 已处理 tag,排到末尾。
 *
 * 这是收口层的"自动已处理"规则:
 *   - 不修改 Resume_JSON
 *   - 不修改 store.missingQuestions(后端原文保留,便于审计)
 *   - 复用 targetCache,与采纳定位严格一致,避免规则双标
 */
const resolvedQuestionIds = computed(() => {
  const set = new Set()
  if (!resumeJson.value) return set
  const list = store.missingQuestions || []
  list.forEach((_, idx) => {
    const target = getTargetForIdx(idx)
    if (target.kind !== 'field' || !target.path) return
    const cell = readCellByPath(resumeJson.value, target.path)
    if (cell && isCellFilled(cell)) set.add(idx)
  })
  return set
})

/** 沿 path 取字段 cell。支持:basics.X / skills.items[g].items[s].name / sec.items[i].field */
const readCellByPath = (json, path) => {
  if (!json || !path) return null
  // 解析 token: word | [number]
  const tokens = []
  const re = /([a-zA-Z_][a-zA-Z0-9_]*)|\[(\d+)\]/g
  let m
  while ((m = re.exec(path)) !== null) {
    if (m[1] != null) tokens.push({ key: m[1] })
    else tokens.push({ idx: Number(m[2]) })
  }
  let cur = json
  for (const t of tokens) {
    if (cur == null) return null
    cur = t.key != null ? cur[t.key] : cur[t.idx]
  }
  return cur
}

/** 判断字段单元是否已被填(string 非空 / 数组非空 / status 非 missing 系列)。 */
const isCellFilled = (cell) => {
  if (!cell || typeof cell !== 'object') return false
  // skills.items[g].items[s] 是 {name, status},不是标准 cell
  const value = 'value' in cell ? cell.value : ('name' in cell ? cell.name : undefined)
  const status = cell.status
  if (status === FIELD_STATUS.MISSING || status === FIELD_STATUS.NEEDS_CONFIRMATION) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some((v) => typeof v === 'string' && v.trim())
  if (typeof value === 'number') return Number.isFinite(value)
  return false
}

// ─── 确认 ──
const onConfirm = () => store.confirmResume(false)
const onForceConfirm = () => store.confirmResume(true)

const missingPaths = computed(() => {
  if (!resumeJson.value) return []
  // 复用 store 的 listMissingPaths 计算逻辑
  const paths = []
  // basics
  for (const f of BASICS_FIELDS) {
    const cell = resumeJson.value.basics?.[f]
    if (cell && (cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION)) {
      paths.push(`${SECTION_LABELS.basics} · ${labelOf(f)}`)
    }
  }
  for (const sec of Object.keys(ITEM_FIELDS)) {
    const items = resumeJson.value[sec]?.items || []
    items.forEach((item, idx) => {
      ITEM_FIELDS[sec].forEach((f) => {
        const cell = item?.[f]
        if (cell && (cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION)) {
          paths.push(`${SECTION_LABELS[sec]} #${idx + 1} · ${labelOf(f)}`)
        }
      })
    })
  }
  const skillsItems = resumeJson.value.skills?.items || []
  skillsItems.forEach((g, gIdx) => {
    ;(g?.items || []).forEach((s, sIdx) => {
      if (s && (s.status === FIELD_STATUS.MISSING || s.status === FIELD_STATUS.NEEDS_CONFIRMATION)) {
        paths.push(`技能分组 #${gIdx + 1} · 项 #${sIdx + 1}`)
      }
    })
  })
  return paths
})

// 字段单元状态 → CSS class
const cellClass = (cell) => {
  if (!cell) return 'rb-cell--missing'
  switch (cell.status) {
    case FIELD_STATUS.MISSING:
      return 'rb-cell--missing'
    case FIELD_STATUS.NEEDS_CONFIRMATION:
      return 'rb-cell--need-confirm'
    case FIELD_STATUS.INFERRED:
      return 'rb-cell--inferred'
    case FIELD_STATUS.CONFIRMED:
      return 'rb-cell--confirmed'
    default:
      return 'rb-cell--missing'
  }
}

// 数组型字段值 → textarea 字符串(用换行分隔)
const arrayValueToText = (cell) => {
  if (!cell) return ''
  if (Array.isArray(cell.value)) return cell.value.join('\n')
  if (typeof cell.value === 'string') return cell.value
  return ''
}
</script>

<template>
  <div v-if="resumeJson" class="rb-form" data-test="resume-builder-form">
    <!-- AI 警告横幅 -->
    <div
      v-if="store.showFabricationBanner"
      class="rb-banner rb-banner--danger"
      data-test="resume-builder-fabrication-banner"
    >
      <AlertTriangle class="w-4 h-4 flex-shrink-0" />
      <span>AI 可能编造内容,请逐项核对</span>
      <button
        type="button"
        class="rb-banner__close"
        @click="store.dismissFabricationBanner()"
        aria-label="关闭警告"
      >
        ×
      </button>
    </div>

    <!-- 内容优化建议(收口版) -->
    <MissingQuestionsCard
      :questions="store.missingQuestions"
      :dismissed="store.dismissedQuestions"
      :resolved="resolvedQuestionIds"
      @adopt="onAdoptQuestion"
      @dismiss="onDismissQuestion"
    />

    <!-- 基础信息 -->
    <section class="rb-section">
      <header class="rb-section__head">
        <span class="rb-section__title">{{ SECTION_LABELS.basics }}</span>
      </header>
      <div class="rb-section__body grid grid-cols-1 md:grid-cols-2 gap-2">
        <label
          v-for="f in BASICS_FIELDS"
          :key="f"
          class="rb-field"
          :class="cellClass(resumeJson.basics[f])"
        >
          <span class="rb-field__label">
            <span class="rb-field__label-text">{{ labelOf(f) }}</span>
            <span class="rb-field__badge" :title="STATUS_TIP[resumeJson.basics[f]?.status]">
              <CheckCircle2 v-if="resumeJson.basics[f]?.status === FIELD_STATUS.CONFIRMED" class="w-3 h-3" />
              <Sparkles v-else-if="resumeJson.basics[f]?.status === FIELD_STATUS.INFERRED" class="w-3 h-3" />
              <HelpCircle v-else-if="resumeJson.basics[f]?.status === FIELD_STATUS.NEEDS_CONFIRMATION" class="w-3 h-3" />
              <AlertTriangle v-else class="w-3 h-3" />
              {{ STATUS_LABEL[resumeJson.basics[f]?.status] || '缺失' }}
            </span>
          </span>
          <input
            type="text"
            class="rb-field__input"
            :value="resumeJson.basics[f]?.value || ''"
            :placeholder="labelOf(f)"
            @input="onBasicsEdit(f, $event.target.value)"
            :data-test="`rb-basics-${f}`"
            :data-rb-field="`basics.${f}`"
          />
        </label>
      </div>
    </section>

    <!-- 教育 / 工作 / 项目 / 奖项 / 证书:数组型 Section -->
    <template v-for="sec in ['education', 'projects', 'experience', 'awards', 'certificates']" :key="sec">
      <section class="rb-section">
        <header class="rb-section__head">
          <span class="rb-section__title">{{ SECTION_LABELS[sec] }}</span>
          <span class="rb-section__count">{{ resumeJson[sec]?.items?.length || 0 }} 条</span>
          <button
            type="button"
            class="rb-section__add"
            :disabled="arraySectionFull(sec)"
            @click="onAddItem(sec)"
            :data-test="`rb-${sec}-add`"
          >
            <Plus class="w-3 h-3" />
            新增
          </button>
        </header>
        <div class="rb-section__body flex flex-col gap-2">
          <p
            v-if="(resumeJson[sec]?.items?.length || 0) === 0"
            class="rb-section__empty"
          >
            暂无内容,点击「新增」添加。
          </p>
          <div
            v-for="(item, idx) in resumeJson[sec]?.items || []"
            :key="`${sec}-${idx}`"
            class="rb-item"
          >
            <header class="rb-item__head">
              <span class="rb-item__index">#{{ idx + 1 }}</span>
              <button
                type="button"
                class="rb-item__remove"
                @click="onRemoveItem(sec, idx)"
                :data-test="`rb-${sec}-remove-${idx}`"
                aria-label="删除"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </header>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <label
                v-for="f in ITEM_FIELDS[sec]"
                :key="f"
                class="rb-field"
                :class="cellClass(item[f])"
              >
                <span class="rb-field__label">
                  <span class="rb-field__label-text">{{ labelOf(f) }}</span>
                  <span class="rb-field__badge" :title="STATUS_TIP[item[f]?.status]">
                    <CheckCircle2 v-if="item[f]?.status === FIELD_STATUS.CONFIRMED" class="w-3 h-3" />
                    <Sparkles v-else-if="item[f]?.status === FIELD_STATUS.INFERRED" class="w-3 h-3" />
                    <HelpCircle v-else-if="item[f]?.status === FIELD_STATUS.NEEDS_CONFIRMATION" class="w-3 h-3" />
                    <AlertTriangle v-else class="w-3 h-3" />
                    {{ STATUS_LABEL[item[f]?.status] || '缺失' }}
                  </span>
                </span>
                <textarea
                  v-if="f === 'highlights' || f === 'stack' || f === 'summary'"
                  class="rb-field__textarea"
                  :value="f === 'summary' ? (item[f]?.value || '') : arrayValueToText(item[f])"
                  :placeholder="f === 'highlights' || f === 'stack' ? '每行一项,或用逗号分隔' : labelOf(f)"
                  rows="3"
                  @input="onArrayEdit(sec, idx, f, $event.target.value)"
                  :data-rb-field="`${sec}.items[${idx}].${f}`"
                />
                <input
                  v-else
                  type="text"
                  class="rb-field__input"
                  :value="item[f]?.value || ''"
                  :placeholder="labelOf(f)"
                  @input="onItemEdit(sec, idx, f, $event.target.value)"
                  :data-rb-field="`${sec}.items[${idx}].${f}`"
                />
              </label>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- 技能 Section(分组 + 子项) -->
    <section class="rb-section">
      <header class="rb-section__head">
        <span class="rb-section__title">{{ SECTION_LABELS.skills }}</span>
        <span class="rb-section__count">{{ resumeJson.skills?.items?.length || 0 }} 个分组</span>
        <button
          type="button"
          class="rb-section__add"
          :disabled="skillsGroupFull"
          @click="onAddSkillGroup"
          data-test="rb-skills-add-group"
        >
          <Plus class="w-3 h-3" />
          新增分组
        </button>
      </header>
      <div class="rb-section__body flex flex-col gap-2">
        <p
          v-if="(resumeJson.skills?.items?.length || 0) === 0"
          class="rb-section__empty"
        >
          暂无技能分组,点击「新增分组」添加。
        </p>
        <div
          v-for="(group, gIdx) in resumeJson.skills?.items || []"
          :key="`skill-group-${gIdx}`"
          class="rb-item"
        >
          <header class="rb-item__head">
            <input
              type="text"
              class="rb-skill__category"
              :value="group.category || ''"
              placeholder="分组名,如「编程语言」"
              @input="onSkillCategoryEdit(gIdx, $event.target.value)"
              :data-test="`rb-skills-category-${gIdx}`"
              :data-rb-field="`skills.items[${gIdx}].category`"
            />
            <button
              type="button"
              class="rb-item__remove"
              @click="onRemoveSkillGroup(gIdx)"
              aria-label="删除分组"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </header>
          <div class="rb-skill__items">
            <div
              v-for="(skill, sIdx) in group.items || []"
              :key="`skill-${gIdx}-${sIdx}`"
              class="rb-skill__row"
              :class="cellClass(skill)"
            >
              <input
                type="text"
                class="rb-field__input"
                :value="skill.name || ''"
                placeholder="技能,如 Vue 3"
                @input="onSkillNameEdit(gIdx, sIdx, $event.target.value)"
                :data-test="`rb-skills-item-${gIdx}-${sIdx}`"
                :data-rb-field="`skills.items[${gIdx}].items[${sIdx}].name`"
              />
              <button
                type="button"
                class="rb-skill__remove"
                @click="onRemoveSkillItem(gIdx, sIdx)"
                aria-label="删除技能"
              >
                <Trash2 class="w-3 h-3" />
              </button>
            </div>
            <button
              type="button"
              class="rb-skill__add"
              :disabled="skillsItemFull(gIdx)"
              @click="onAddSkillItem(gIdx)"
            >
              <Plus class="w-3 h-3" />
              添加技能
            </button>
          </div>
        </div>
      </div>
    </section>

    <ConfirmResumeButton
      :has-missing="store.stillHasMissing"
      :missing-paths="missingPaths"
      :already-confirmed="store.isConfirmedByUser"
      @confirm="onConfirm"
      @force-confirm="onForceConfirm"
    />
  </div>

  <div v-else class="rb-form rb-form--empty">
    <p class="text-sm text-gray-500 text-center py-8">
      暂无 Resume_JSON。请回到上一步重新生成。
    </p>
  </div>
</template>

<style scoped>
.rb-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  height: 100%;
  overflow-y: auto;
}
.rb-form::-webkit-scrollbar {
  width: 6px;
}
.rb-form::-webkit-scrollbar-thumb {
  background: rgba(168, 85, 247, 0.25);
  border-radius: 3px;
}

.rb-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
}
.rb-banner--danger {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: rgb(252, 165, 165);
}
.rb-banner__close {
  margin-left: auto;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
}
.rb-banner__close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.rb-section {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(10px);
}
.rb-section__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.rb-section__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(229, 231, 235, 0.95);
}
.rb-section__count {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(156, 163, 175, 0.7);
}
.rb-section__add {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(34, 211, 238, 0.06);
  color: rgb(165, 243, 252);
  cursor: pointer;
  transition: all 0.18s ease;
}
.rb-section__add:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.14);
  color: #fff;
}
.rb-section__add:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
/* 采纳命中空 section 时给「新增」按钮一次短暂闪光,引导用户新增条目。
   不复用 rb-field--highlight 的青蓝色样式,避免与字段语义混淆;改用更柔和的紫色脉冲。 */
.rb-section__add--blink {
  animation: rb-section-add-blink 2.4s ease-out;
  border-color: rgba(168, 85, 247, 0.7) !important;
  background: rgba(168, 85, 247, 0.16) !important;
  color: #fff !important;
}
@keyframes rb-section-add-blink {
  0%   { box-shadow: 0 0 0 0 rgba(168, 85, 247, 0.55), 0 0 18px rgba(168, 85, 247, 0.45); }
  50%  { box-shadow: 0 0 0 4px rgba(168, 85, 247, 0.1), 0 0 8px rgba(168, 85, 247, 0.2); }
  100% { box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.4), 0 0 14px rgba(168, 85, 247, 0.3); }
}
.rb-section__body {
  padding: 10px 12px;
}
.rb-section__empty {
  text-align: center;
  font-size: 12px;
  color: rgba(156, 163, 175, 0.7);
  padding: 6px 8px;
  margin: 0;
}

.rb-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 10px;
}
.rb-item__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.rb-item__index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: rgba(168, 85, 247, 0.85);
  font-weight: 600;
}
.rb-item__remove {
  margin-left: auto;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: transparent;
  color: rgba(239, 68, 68, 0.7);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.18s ease;
}
.rb-item__remove:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.5);
  color: rgb(252, 165, 165);
}

.rb-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  position: relative;
  border-radius: 8px;
  padding: 5px 8px 6px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.rb-field--missing {
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.06) inset;
}
.rb-field--need-confirm {
  border-color: rgba(245, 158, 11, 0.45);
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.06) inset;
}
.rb-field--inferred {
  border-color: rgba(234, 179, 8, 0.45);
  box-shadow: 0 0 12px rgba(234, 179, 8, 0.06) inset;
}
.rb-field--confirmed {
  border-color: rgba(34, 211, 238, 0.25);
}

/* 「采纳」点击后短暂高亮(3 秒,3 次脉冲) */
.rb-field--highlight,
.rb-skill__row.rb-field--highlight {
  animation: rb-field-pulse 3s ease-out;
  border-color: rgba(34, 211, 238, 0.85) !important;
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.45),
              0 0 18px rgba(34, 211, 238, 0.35) !important;
}
@keyframes rb-field-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.6),  0 0 22px rgba(34, 211, 238, 0.55); }
  16%  { box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.15), 0 0 12px rgba(34, 211, 238, 0.25); }
  33%  { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.6),  0 0 22px rgba(34, 211, 238, 0.55); }
  50%  { box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.15), 0 0 12px rgba(34, 211, 238, 0.25); }
  66%  { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.6),  0 0 22px rgba(34, 211, 238, 0.55); }
  83%  { box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.15), 0 0 12px rgba(34, 211, 238, 0.25); }
  100% { box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.45), 0 0 18px rgba(34, 211, 238, 0.35); }
}

.rb-field__label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: rgba(229, 231, 235, 0.92);
  font-family: ui-sans-serif, "PingFang SC", system-ui, sans-serif;
  letter-spacing: 0.01em;
  font-weight: 500;
}
.rb-field__badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(229, 231, 235, 0.7);
}
.rb-field--missing .rb-field__badge {
  color: rgb(252, 165, 165);
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.06);
}
.rb-field--need-confirm .rb-field__badge {
  color: rgb(252, 211, 77);
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.08);
}
.rb-field--inferred .rb-field__badge {
  color: rgb(254, 240, 138);
  border-color: rgba(234, 179, 8, 0.4);
  background: rgba(234, 179, 8, 0.08);
}
.rb-field--confirmed .rb-field__badge {
  color: rgb(165, 243, 252);
  border-color: rgba(34, 211, 238, 0.35);
  background: rgba(34, 211, 238, 0.08);
}

.rb-field__input,
.rb-field__textarea {
  width: 100%;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 13px;
  color: rgba(229, 231, 235, 0.95);
  font-family: ui-sans-serif, "PingFang SC", system-ui, sans-serif;
  transition: border-color 0.18s ease;
  line-height: 1.4;
}
.rb-field__input::placeholder,
.rb-field__textarea::placeholder {
  color: rgba(156, 163, 175, 0.55);
}
.rb-field__textarea {
  resize: vertical;
  min-height: 48px;
  font-family: ui-sans-serif, "PingFang SC", system-ui, sans-serif;
}
.rb-field__input:focus,
.rb-field__textarea:focus {
  outline: none;
  border-color: rgba(34, 211, 238, 0.5);
}

/* skills */
.rb-skill__category {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: rgb(216, 180, 254);
}
.rb-skill__items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rb-skill__row {
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
  padding: 4px 6px;
  border: 1px solid transparent;
}
.rb-skill__row.rb-cell--missing {
  border-color: rgba(239, 68, 68, 0.3);
}
.rb-skill__row.rb-cell--confirmed {
  border-color: rgba(34, 211, 238, 0.2);
}
.rb-skill__remove {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: transparent;
  border-radius: 6px;
  color: rgba(239, 68, 68, 0.7);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.rb-skill__remove:hover {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(252, 165, 165);
}
.rb-skill__add {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px dashed rgba(34, 211, 238, 0.3);
  background: transparent;
  color: rgba(165, 243, 252, 0.85);
  cursor: pointer;
  margin-top: 4px;
}
.rb-skill__add:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.08);
  border-style: solid;
}
.rb-skill__add:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
