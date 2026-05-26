/**
 * resumeJsonSchema.js — Resume_JSON 前端纯函数操作层
 *
 * 满足 Requirements:
 *   - 3.5 / 6.5 / 6.6: missingFields ↔ Field_Status 互蕴
 *   - 7.5 / 7.6 / 7.10: switchTemplate 仅写 meta.templateId,其他字段零变更
 *   - 8.3 / 10.1 / 10.2 / 10.4 / 11.5: 编辑/切换不触发 HTTP
 *
 * 全部为纯函数,不读 store / 不读 DOM / 不发 HTTP。
 *
 * 字段路径示例:
 *   - basics.name
 *   - education.items[0].school
 *   - skills.items[1].items[3].name
 *   - skills.items[1].category(纯字符串,不带 status)
 */

// ─────────────────────────────────────────────
// 常量
// ─────────────────────────────────────────────

export const FIELD_STATUS = Object.freeze({
  CONFIRMED: 'confirmed',
  INFERRED: 'inferred_from_text',
  MISSING: 'missing',
  NEEDS_CONFIRMATION: 'needs_confirmation'
})

export const ALLOWED_TEMPLATE_IDS = Object.freeze(['ats_single_column', 'tech_two_column'])

export const TOP_LEVEL_SECTIONS = Object.freeze([
  'basics',
  'education',
  'skills',
  'projects',
  'experience',
  'awards',
  'certificates',
  'meta'
])

export const BASICS_FIELDS = Object.freeze([
  'name',
  'targetRole',
  'email',
  'phone',
  'city',
  'websiteOrRepo'
])

export const ITEM_FIELDS = Object.freeze({
  education: ['school', 'degree', 'major', 'startDate', 'endDate', 'gpa', 'highlights'],
  projects: ['name', 'role', 'stack', 'startDate', 'endDate', 'summary', 'highlights', 'link'],
  experience: ['company', 'title', 'startDate', 'endDate', 'location', 'summary', 'highlights'],
  awards: ['name', 'issuer', 'date', 'summary'],
  certificates: ['name', 'issuer', 'issueDate', 'expireDate', 'credentialId']
})

const ARRAY_FIELDS_PER_ITEM = new Set(['highlights', 'stack'])

export const ARRAY_SECTION_MAX = 50
export const SKILLS_GROUP_MAX = 10
export const SKILLS_ITEM_MAX = 30

// ─────────────────────────────────────────────
// 辅助
// ─────────────────────────────────────────────

/** 判断字段值是否"空"。Requirement 6.5 / 6.6 互斥。 */
export function isEmptyValue(v) {
  if (v == null) return true
  if (typeof v === 'string') return v.trim() === ''
  if (typeof v === 'number') return !Number.isFinite(v)
  if (Array.isArray(v)) return v.length === 0
  if (typeof v === 'object') return Object.keys(v).length === 0
  return false
}

/** 是否为合法 Field 单元(标量字段携带的 {value, status})。 */
export function isFieldCell(cell) {
  return (
    cell != null &&
    typeof cell === 'object' &&
    !Array.isArray(cell) &&
    Object.prototype.hasOwnProperty.call(cell, 'value') &&
    Object.prototype.hasOwnProperty.call(cell, 'status') &&
    Object.values(FIELD_STATUS).includes(cell.status)
  )
}

/** 深克隆(只用于配置安全骨架,避免外部 mutate 影响)。 */
function cloneDeep(value) {
  if (value == null) return value
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(value)
    } catch {
      // 部分环境不支持就降级到 JSON
    }
  }
  return JSON.parse(JSON.stringify(value))
}

// ─────────────────────────────────────────────
// 安全骨架 / 默认条目模板
// ─────────────────────────────────────────────

function emptyCell() {
  return { value: '', status: FIELD_STATUS.MISSING }
}

function emptyArrayCell() {
  return { value: [], status: FIELD_STATUS.MISSING }
}

function buildEmptyEducationItem() {
  return {
    school: emptyCell(),
    degree: emptyCell(),
    major: emptyCell(),
    startDate: emptyCell(),
    endDate: emptyCell(),
    gpa: emptyCell(),
    highlights: emptyArrayCell()
  }
}

function buildEmptyProjectItem() {
  return {
    name: emptyCell(),
    role: emptyCell(),
    stack: emptyArrayCell(),
    startDate: emptyCell(),
    endDate: emptyCell(),
    summary: emptyCell(),
    highlights: emptyArrayCell(),
    link: emptyCell()
  }
}

function buildEmptyExperienceItem() {
  return {
    company: emptyCell(),
    title: emptyCell(),
    startDate: emptyCell(),
    endDate: emptyCell(),
    location: emptyCell(),
    summary: emptyCell(),
    highlights: emptyArrayCell()
  }
}

function buildEmptyAwardItem() {
  return {
    name: emptyCell(),
    issuer: emptyCell(),
    date: emptyCell(),
    summary: emptyCell()
  }
}

function buildEmptyCertificateItem() {
  return {
    name: emptyCell(),
    issuer: emptyCell(),
    issueDate: emptyCell(),
    expireDate: emptyCell(),
    credentialId: emptyCell()
  }
}

function buildEmptySkillGroup() {
  return { category: '', items: [] }
}

function buildEmptySkillItem() {
  return { name: '', status: FIELD_STATUS.MISSING }
}

const ITEM_FACTORIES = Object.freeze({
  education: buildEmptyEducationItem,
  projects: buildEmptyProjectItem,
  experience: buildEmptyExperienceItem,
  awards: buildEmptyAwardItem,
  certificates: buildEmptyCertificateItem
})

/**
 * 生成一份所有 Section 全 missing 的安全骨架 Resume_JSON。
 * 用于:
 *   - extract API 失败兜底
 *   - 「从当前文档生成」之前的空状态
 */
export function buildSafeSkeleton(documentId = '', templateId = 'ats_single_column') {
  const safeTpl = ALLOWED_TEMPLATE_IDS.includes(templateId)
    ? templateId
    : 'ats_single_column'

  const basics = {}
  for (const f of BASICS_FIELDS) basics[f] = emptyCell()
  basics.missingFields = [...BASICS_FIELDS]

  return {
    basics,
    education: { items: [], missingFields: [] },
    skills: { items: [], missingFields: [] },
    projects: { items: [], missingFields: [] },
    experience: { items: [], missingFields: [] },
    awards: { items: [], missingFields: [] },
    certificates: { items: [], missingFields: [] },
    meta: {
      confirmedByUser: false,
      templateId: safeTpl,
      generatedAt: new Date().toISOString(),
      sourceDocumentId: documentId || ''
    }
  }
}

/**
 * 检查是否是合法的 Resume_JSON 顶层结构(用于客户端兜底前的前置校验)。
 * 不做完整契约校验(那归后端);只做"形态足以渲染"的判定。
 */
export function isValidResumeJson(json) {
  if (!json || typeof json !== 'object') return false
  for (const key of TOP_LEVEL_SECTIONS) {
    if (!Object.prototype.hasOwnProperty.call(json, key)) return false
  }
  if (!json.basics || typeof json.basics !== 'object') return false
  for (const sec of ['education', 'skills', 'projects', 'experience', 'awards', 'certificates']) {
    if (!json[sec] || !Array.isArray(json[sec].items)) return false
  }
  if (!json.meta || typeof json.meta !== 'object') return false
  return true
}

// ─────────────────────────────────────────────
// 字段路径解析
// ─────────────────────────────────────────────

/**
 * 解析路径字符串为操作步骤数组。
 * 支持:
 *   - "basics.name"
 *   - "education.items[0].school"
 *   - "education.items[0].highlights"
 *   - "skills.items[1].items[3].name"
 *   - "skills.items[1].category"
 */
function parsePath(path) {
  if (typeof path !== 'string' || !path) {
    throw new Error(`非法字段路径: ${path}`)
  }
  const tokens = []
  const re = /([a-zA-Z_][a-zA-Z0-9_]*)|\[(\d+)\]/g
  let m
  while ((m = re.exec(path)) !== null) {
    if (m[1] != null) tokens.push({ type: 'key', key: m[1] })
    else tokens.push({ type: 'index', index: Number(m[2]) })
  }
  if (tokens.length === 0) {
    throw new Error(`无法解析字段路径: ${path}`)
  }
  return tokens
}

/**
 * 沿路径取节点。返回 undefined 表示路径不存在。
 */
export function readField(json, path) {
  if (!json) return undefined
  const tokens = parsePath(path)
  let cur = json
  for (const t of tokens) {
    if (cur == null) return undefined
    if (t.type === 'key') cur = cur[t.key]
    else cur = cur[t.index]
  }
  return cur
}

/**
 * 取路径的"父对象"+ 末位 key/index,用于赋值/删除。
 */
function resolveParent(json, path) {
  const tokens = parsePath(path)
  let cur = json
  for (let i = 0; i < tokens.length - 1; i++) {
    const t = tokens[i]
    if (cur == null) return null
    cur = t.type === 'key' ? cur[t.key] : cur[t.index]
  }
  if (cur == null) return null
  const last = tokens[tokens.length - 1]
  return { parent: cur, last }
}

/**
 * 推断该路径对应字段是否数组型(highlights / stack)。
 */
function isArrayValuePath(path) {
  const tokens = parsePath(path)
  const last = tokens[tokens.length - 1]
  if (last.type !== 'key') return false
  return ARRAY_FIELDS_PER_ITEM.has(last.key)
}

// ─────────────────────────────────────────────
// missingFields 同步
// ─────────────────────────────────────────────

function statusImpliesMissing(status) {
  return (
    status === FIELD_STATUS.MISSING ||
    status === FIELD_STATUS.NEEDS_CONFIRMATION ||
    status === FIELD_STATUS.INFERRED
  )
}

/**
 * 找到 path 所属 Section 的 missingFields 数组,以及在 missingFields 内使用的 key 形式。
 * 返回 { mfArray: string[], key: string } 或 null。
 *
 * 规则:
 *   - path = "basics.<field>" → basics.missingFields, key = "<field>"
 *   - path = "education.items[i].<field>" → education.missingFields, key = "items[i].<field>"
 *   - path = "skills.items[g].items[s].name" → skills.missingFields, key = "items[g].items[s].name"
 */
function resolveMissingFieldsRef(json, path) {
  if (path.startsWith('basics.')) {
    const field = path.slice('basics.'.length)
    if (!BASICS_FIELDS.includes(field)) return null
    if (!Array.isArray(json?.basics?.missingFields)) {
      if (json?.basics) json.basics.missingFields = []
    }
    return { mfArray: json.basics.missingFields, key: field }
  }
  for (const section of ['education', 'projects', 'experience', 'awards', 'certificates']) {
    const prefix = `${section}.`
    if (path.startsWith(prefix)) {
      const remainder = path.slice(prefix.length) // items[i].<field>
      if (!json?.[section]) return null
      if (!Array.isArray(json[section].missingFields)) json[section].missingFields = []
      return { mfArray: json[section].missingFields, key: remainder }
    }
  }
  if (path.startsWith('skills.')) {
    const remainder = path.slice('skills.'.length) // items[g].items[s].name
    if (!json?.skills) return null
    if (!Array.isArray(json.skills.missingFields)) json.skills.missingFields = []
    return { mfArray: json.skills.missingFields, key: remainder }
  }
  return null
}

function addMissingKey(mfArray, key) {
  if (!mfArray.includes(key)) mfArray.push(key)
}

function removeMissingKey(mfArray, key) {
  const idx = mfArray.indexOf(key)
  if (idx >= 0) mfArray.splice(idx, 1)
}

/** 该路径当前是否已记录于 missingFields。 */
export function containsMissing(json, path) {
  const ref = resolveMissingFieldsRef(json, path)
  if (!ref) return false
  return ref.mfArray.includes(ref.key)
}

// ─────────────────────────────────────────────
// 编辑操作(只编辑字段单元的 value/status,不动其他字段)
// ─────────────────────────────────────────────

/**
 * 对单个字段单元的"赋值 + 状态同步"——纯函数,接收 json,就地修改后返回 json。
 * Requirement 6.5 / 6.6:
 *   - 非空内容 → status 转 confirmed,从 missingFields 移除
 *   - 清空 → status 转 missing,加入 missingFields
 */
export function applyFieldEdit(json, path, value) {
  if (!json) return json
  const resolved = resolveParent(json, path)
  if (!resolved) return json
  const { parent, last } = resolved
  if (last.type !== 'key') return json
  const key = last.key

  // skills.items[g].items[s].name 是裸字段(不是 cell)
  // skills.items[g].category 也是裸字符串
  // 判断方法:看父节点上原本是否是 Field 单元
  const cur = parent[key]

  if (key === 'category' && parent && Array.isArray(parent.items) && typeof parent.category === 'string') {
    // skills.items[g].category — 纯字符串,不携带 status,不参与 missingFields 同步
    parent.category = typeof value === 'string' ? value : ''
    return json
  }

  if (
    parent &&
    typeof parent === 'object' &&
    'name' in parent &&
    'status' in parent &&
    Object.values(FIELD_STATUS).includes(parent.status) &&
    key === 'name'
  ) {
    // skills.items[g].items[s] — 该对象本身就是 {name, status} 单元,
    // 但 path 末段是 "name",这里允许直接修改 name 并同步 status
    const newName = typeof value === 'string' ? value : ''
    parent.name = newName
    const empty = isEmptyValue(newName)
    parent.status = empty ? FIELD_STATUS.MISSING : FIELD_STATUS.CONFIRMED
    const ref = resolveMissingFieldsRef(json, path)
    if (ref) {
      if (empty) addMissingKey(ref.mfArray, ref.key)
      else removeMissingKey(ref.mfArray, ref.key)
    }
    return json
  }

  if (!isFieldCell(cur)) {
    // 路径不指向标准字段单元 — 直接赋值,但不参与 status 同步
    parent[key] = value
    return json
  }

  // 标准 FieldCell 编辑
  const isArrayField = ARRAY_FIELDS_PER_ITEM.has(key)
  let newValue
  if (isArrayField) {
    if (Array.isArray(value)) newValue = value.slice()
    else if (typeof value === 'string') {
      // 允许传入字符串,按换行 / 中英文逗号分割
      newValue = value
        .split(/[\n,，]/g)
        .map((s) => s.trim())
        .filter(Boolean)
    } else newValue = []
  } else if (typeof value === 'string' || typeof value === 'number' || value == null) {
    newValue = value == null ? '' : value
  } else {
    newValue = String(value)
  }

  const empty = isEmptyValue(newValue)
  cur.value = empty
    ? isArrayField
      ? []
      : ''
    : newValue
  cur.status = empty ? FIELD_STATUS.MISSING : FIELD_STATUS.CONFIRMED

  const ref = resolveMissingFieldsRef(json, path)
  if (ref) {
    if (empty) addMissingKey(ref.mfArray, ref.key)
    else removeMissingKey(ref.mfArray, ref.key)
  }

  return json
}

// 别名
export const patchField = applyFieldEdit

// ─────────────────────────────────────────────
// 模板切换
// ─────────────────────────────────────────────

/**
 * 切换模板 — 仅写 meta.templateId,严禁改动其他字段。
 * Requirement 7.5 / 7.6 / 7.10。
 *
 * @returns {object} — 同一份 json 引用(已就地修改),或 templateId 越界时的原引用。
 */
export function switchTemplate(json, templateId) {
  if (!json || typeof json !== 'object') return json
  if (!ALLOWED_TEMPLATE_IDS.includes(templateId)) return json
  if (!json.meta || typeof json.meta !== 'object') json.meta = {}
  json.meta.templateId = templateId
  return json
}

// ─────────────────────────────────────────────
// 数组操作
// ─────────────────────────────────────────────

/**
 * 在数组型 Section 末尾追加一条空条目。
 *
 * Requirement 3.3 / 3.4:数组上限校验
 */
export function addArrayItem(json, sectionPath, customTemplate) {
  if (!json) return json

  if (sectionPath === 'skills.items') {
    const skills = json.skills
    if (!skills || !Array.isArray(skills.items)) return json
    if (skills.items.length >= SKILLS_GROUP_MAX) return json
    skills.items.push(customTemplate ? cloneDeep(customTemplate) : buildEmptySkillGroup())
    return json
  }

  // skills.items[g].items 是技能项(不是分组)
  const skillSubMatch = sectionPath.match(/^skills\.items\[(\d+)\]\.items$/)
  if (skillSubMatch) {
    const gIdx = Number(skillSubMatch[1])
    const group = json?.skills?.items?.[gIdx]
    if (!group || !Array.isArray(group.items)) return json
    if (group.items.length >= SKILLS_ITEM_MAX) return json
    group.items.push(customTemplate ? cloneDeep(customTemplate) : buildEmptySkillItem())
    return json
  }

  for (const section of Object.keys(ITEM_FACTORIES)) {
    if (sectionPath === `${section}.items`) {
      const sec = json[section]
      if (!sec || !Array.isArray(sec.items)) return json
      if (sec.items.length >= ARRAY_SECTION_MAX) return json
      const factory = ITEM_FACTORIES[section]
      sec.items.push(customTemplate ? cloneDeep(customTemplate) : factory())
      return json
    }
  }
  return json
}

/**
 * 删除数组型 Section 的某条目。
 */
export function removeArrayItem(json, sectionPath, index) {
  if (!json) return json
  if (typeof index !== 'number' || index < 0) return json

  if (sectionPath === 'skills.items') {
    const skills = json.skills
    if (!skills || !Array.isArray(skills.items)) return json
    if (index >= skills.items.length) return json
    skills.items.splice(index, 1)
    return json
  }

  const skillSubMatch = sectionPath.match(/^skills\.items\[(\d+)\]\.items$/)
  if (skillSubMatch) {
    const gIdx = Number(skillSubMatch[1])
    const group = json?.skills?.items?.[gIdx]
    if (!group || !Array.isArray(group.items)) return json
    if (index >= group.items.length) return json
    group.items.splice(index, 1)
    return json
  }

  for (const section of Object.keys(ITEM_FACTORIES)) {
    if (sectionPath === `${section}.items`) {
      const sec = json[section]
      if (!sec || !Array.isArray(sec.items)) return json
      if (index >= sec.items.length) return json
      sec.items.splice(index, 1)
      return json
    }
  }
  return json
}

// ─────────────────────────────────────────────
// 遍历:用于「是否含 missing/needs_confirmation」判定
// ─────────────────────────────────────────────

/**
 * 遍历所有标量字段单元,yield {path, cell}
 */
export function* iterAtomicFields(json) {
  if (!json) return
  if (json.basics) {
    for (const f of BASICS_FIELDS) {
      const cell = json.basics[f]
      if (isFieldCell(cell)) yield { path: `basics.${f}`, cell }
    }
  }
  for (const section of Object.keys(ITEM_FIELDS)) {
    const sec = json[section]
    if (!sec || !Array.isArray(sec.items)) continue
    for (let idx = 0; idx < sec.items.length; idx++) {
      const item = sec.items[idx]
      if (!item) continue
      for (const f of ITEM_FIELDS[section]) {
        const cell = item[f]
        if (isFieldCell(cell)) {
          yield { path: `${section}.items[${idx}].${f}`, cell }
        }
      }
    }
  }
  if (json.skills && Array.isArray(json.skills.items)) {
    for (let gIdx = 0; gIdx < json.skills.items.length; gIdx++) {
      const group = json.skills.items[gIdx]
      if (!group || !Array.isArray(group.items)) continue
      for (let sIdx = 0; sIdx < group.items.length; sIdx++) {
        const skill = group.items[sIdx]
        if (skill && Object.values(FIELD_STATUS).includes(skill.status)) {
          yield {
            path: `skills.items[${gIdx}].items[${sIdx}].name`,
            cell: { value: skill.name, status: skill.status }
          }
        }
      }
    }
  }
}

/**
 * 当前 Resume_JSON 中所有"待补全"字段的人类可读路径列表。
 * 含 missing / needs_confirmation,不含 inferred_from_text(后者属于"复核"而非"补全")。
 */
export function listMissingPaths(json) {
  const out = []
  for (const { path, cell } of iterAtomicFields(json)) {
    if (cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION) {
      out.push(path)
    }
  }
  return out
}

/**
 * Resume_JSON 中是否存在 missing / needs_confirmation 字段。
 */
export function hasMissingFields(json) {
  for (const { cell } of iterAtomicFields(json)) {
    if (cell.status === FIELD_STATUS.MISSING || cell.status === FIELD_STATUS.NEEDS_CONFIRMATION) {
      return true
    }
  }
  return false
}

/**
 * Resume_JSON 中是否含 inferred_from_text 字段(用于 UI 提示)。
 */
export function hasInferredFields(json) {
  for (const { cell } of iterAtomicFields(json)) {
    if (cell.status === FIELD_STATUS.INFERRED) return true
  }
  return false
}

// ─────────────────────────────────────────────
// 比较:用于「模板切换非法字段变更」检测
// ─────────────────────────────────────────────

/**
 * 浅比较两份 Resume_JSON 除 meta.templateId 外的所有字段是否深相等。
 * 返回 true 表示相等。
 */
export function deepEqualExceptTemplateId(a, b) {
  if (a === b) return true
  if (!a || !b) return false
  const aClone = cloneDeep(a)
  const bClone = cloneDeep(b)
  if (aClone?.meta) aClone.meta.templateId = '__'
  if (bClone?.meta) bClone.meta.templateId = '__'
  return JSON.stringify(aClone) === JSON.stringify(bClone)
}
