/**
 * historyRecordTypes.js —— 历史记录 record_type / category 兼容层(单一事实源)
 *
 * 背景:
 *   后端目前优先字段 record_type(新),旧记录还有 category(旧)。
 *   Dashboard / HistoryArchive / 三功能页等多处都在做兼容判断,容易出现:
 *     - 同义类型在不同页面 label/icon/color 不一致
 *     - career_plan 在某处被识别,在另一处落到默认未知样式
 *     - 旧 category 分支重复粘贴导致维护偏差
 *
 *   本模块统一收敛,所有页面只允许通过 normalizeRecordType(record) 取值。
 *
 * 不改动:
 *   - 后端 / 数据库 / record_type 枚举
 *   - 历史保存上限、收藏、删除、过滤的业务规则
 *   - upsertSession / loadRecordById 等 API 客户端
 */

/**
 * 标准类型常量(只增不减,新类型加常量后再加映射)。
 */
export const RECORD_TYPES = Object.freeze({
  RESUME_DIAGNOSIS: 'resume_diagnosis',
  CAREER_PLAN:      'career_plan',
  INTERVIEW:        'interview_session',
  DASHBOARD_CHAT:   'dashboard_chat',
  LEGACY_CHAT:      'legacy_chat',   // 旧 agent_* / general_chat 的归一化类型
  UNKNOWN:          'unknown'
})

/**
 * (record_type, category) → 标准类型。
 * 优先级:record.record_type > record.category > 启发式前缀匹配 > UNKNOWN
 */
function resolveType(record) {
  if (!record || typeof record !== 'object') return RECORD_TYPES.UNKNOWN

  const rt = (record.record_type || '').toString().trim()
  const cat = (record.category || '').toString().trim()

  // 1. 优先 record_type 完整匹配
  switch (rt) {
    case 'resume_diagnosis':  return RECORD_TYPES.RESUME_DIAGNOSIS
    case 'career_plan':
    case 'career_planning':   return RECORD_TYPES.CAREER_PLAN
    case 'interview_session': return RECORD_TYPES.INTERVIEW
    case 'dashboard_chat':    return RECORD_TYPES.DASHBOARD_CHAT
    case 'general_chat':      return RECORD_TYPES.LEGACY_CHAT
    default: break
  }
  // record_type 形如 interview_xxx 也归为面试
  if (rt.startsWith('interview')) return RECORD_TYPES.INTERVIEW
  if (rt.startsWith('agent_'))    return RECORD_TYPES.LEGACY_CHAT

  // 2. 兼容旧 category
  switch (cat) {
    case 'resume_diagnosis':  return RECORD_TYPES.RESUME_DIAGNOSIS
    case 'career_plan':
    case 'career_planning':
    case '职业规划':           return RECORD_TYPES.CAREER_PLAN
    case 'dashboard_chat':    return RECORD_TYPES.DASHBOARD_CHAT
    case 'general_chat':      return RECORD_TYPES.LEGACY_CHAT
    case 'interview_evaluate':return RECORD_TYPES.INTERVIEW
    default: break
  }
  if (cat.startsWith('interview')) return RECORD_TYPES.INTERVIEW
  if (cat.startsWith('agent_'))    return RECORD_TYPES.LEGACY_CHAT

  return RECORD_TYPES.UNKNOWN
}

/**
 * 标准元信息:label / icon key / color key / route 行为 / 分组判断。
 *
 * iconKey 与 colorKey 是字符串而非具体组件,
 * 因为不同页面使用的图标库可能不同(lucide-vue-next 的 FileText / Bot / Compass 等),
 * 由调用方拿 key 自行映射,避免在 utils 里耦合 Vue 组件依赖。
 */
const META = Object.freeze({
  [RECORD_TYPES.RESUME_DIAGNOSIS]: {
    label: '简历诊断',
    routeType: 'resume_diagnosis',
    iconKey:  'file-text',
    colorKey: 'purple',
    isFeature: true,
    isChat:    false
  },
  [RECORD_TYPES.CAREER_PLAN]: {
    label: '职业规划',
    routeType: 'career_plan',
    iconKey:  'compass',
    colorKey: 'cyan',
    isFeature: true,
    isChat:    false
  },
  [RECORD_TYPES.INTERVIEW]: {
    label: '模拟面试',
    routeType: 'interview_session',
    iconKey:  'bot',
    colorKey: 'pink',
    isFeature: true,
    isChat:    false
  },
  [RECORD_TYPES.DASHBOARD_CHAT]: {
    label: 'Agent 对话',
    routeType: 'dashboard_chat',
    iconKey:  'message-square',
    colorKey: 'emerald',
    isFeature: false,
    isChat:    true
  },
  [RECORD_TYPES.LEGACY_CHAT]: {
    label: 'Agent 对话',          // 老记录沿用同一标签,避免双标
    routeType: 'legacy_chat',
    iconKey:  'bookmark',
    colorKey: 'emerald',
    isFeature: false,
    isChat:    true
  },
  [RECORD_TYPES.UNKNOWN]: {
    label: '未知记录',
    routeType: 'unknown',
    iconKey:  'history',
    colorKey: 'gray',
    isFeature: false,
    isChat:    false
  }
})

/**
 * Tailwind 颜色 token → 实际 className 三件套(text / border / bg)。
 * 单点维护,避免每个页面再各自拼一遍。
 */
const COLOR_CLASS = Object.freeze({
  purple:  'text-purple-400 border-purple-500/30 bg-purple-500/5',
  cyan:    'text-cyan-400 border-cyan-500/30 bg-cyan-500/5',
  pink:    'text-pink-400 border-pink-500/30 bg-pink-500/5',
  emerald: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5',
  gray:    'text-gray-400 border-gray-500/30 bg-gray-500/5'
})

/**
 * 把任意一条 history record 归一化为标准元信息。
 *
 * @param {object} record 后端返回的历史记录(含 record_type / category / id / session_id 等)
 * @returns {{type: string, label: string, routeType: string, iconKey: string, colorKey: string, isFeature: boolean, isChat: boolean}}
 */
export function normalizeRecordType(record) {
  const type = resolveType(record)
  const meta = META[type] || META[RECORD_TYPES.UNKNOWN]
  return {
    type,
    label:     meta.label,
    routeType: meta.routeType,
    iconKey:   meta.iconKey,
    colorKey:  meta.colorKey,
    isFeature: meta.isFeature,
    isChat:    meta.isChat
  }
}

/**
 * 取标准 label。等价于 normalizeRecordType(record).label,但避免一些调用点要解构。
 */
export function getRecordLabel(record) {
  return normalizeRecordType(record).label
}

/**
 * 取标准颜色三件套 className。
 */
export function getRecordColorClass(record) {
  const { colorKey } = normalizeRecordType(record)
  return COLOR_CLASS[colorKey] || COLOR_CLASS.gray
}

/**
 * 计算从历史列表跳到具体页面的目标路径。
 *
 * @param {object} record
 * @returns {{ name: 'route', path: string } | { name: 'preview' } | null}
 *   - route:   外部用 router.push(path) 跳转
 *   - preview: 历史预览弹窗(legacy chat 仅在 Dashboard 内部展示)
 *   - null:    UNKNOWN 类型,调用方自行兜底
 */
export function resolveHistoryRoute(record) {
  if (!record) return null
  const { routeType } = normalizeRecordType(record)
  switch (routeType) {
    case 'resume_diagnosis':
      return { name: 'route', path: `/resume-diagnosis?id=${record.id}` }
    case 'career_plan':
      return { name: 'route', path: `/career-planning?id=${record.id}` }
    case 'interview_session':
      return { name: 'route', path: `/interview?id=${record.id}` }
    case 'dashboard_chat':
      // dashboard_chat 必须用 session_id 才能稳定恢复 ChatDock(record_id 不稳定)。
      // 缺 session_id 兜底为 chat_id 路径(走旧 agent 预览链路)。
      if (record.session_id) {
        return { name: 'route', path: `/dashboard?session_id=${record.session_id}` }
      }
      return { name: 'route', path: `/dashboard?chat_id=${record.id}` }
    case 'legacy_chat':
      return { name: 'route', path: `/dashboard?chat_id=${record.id}` }
    default:
      return null
  }
}

/**
 * 通用过滤判断:用于 HistoryArchive 的下拉过滤等场景。
 *
 * @param {object} record
 * @param {string} filterValue HistoryArchive 下拉里的 value('all' / 'resume_diagnosis' /
 *                              'career_plan' / 'interview' / 'dashboard_chat' / 'general_chat')
 * @returns {boolean}
 */
export function matchesFilter(record, filterValue) {
  if (!filterValue || filterValue === 'all') return true
  const t = normalizeRecordType(record).type
  switch (filterValue) {
    case 'resume_diagnosis': return t === RECORD_TYPES.RESUME_DIAGNOSIS
    case 'career_plan':      return t === RECORD_TYPES.CAREER_PLAN
    case 'interview':        return t === RECORD_TYPES.INTERVIEW
    case 'dashboard_chat':   return t === RECORD_TYPES.DASHBOARD_CHAT
    case 'general_chat':     return t === RECORD_TYPES.LEGACY_CHAT
    default:                 return t === filterValue
  }
}

/** 暴露颜色 className 表,允许调用方自定义渲染。 */
export const RECORD_COLOR_CLASS = COLOR_CLASS
