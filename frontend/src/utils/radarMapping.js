/**
 * radarMapping.js — Radar 数据构建器
 *
 * 设计原则：每类业务（简历 / 面试）使用各自原始六维，不再强行合成"通用 6 维"。
 *
 * 提供：
 *   - RESUME_INDICATORS / INTERVIEW_INDICATORS：原始维度定义（中文标签 + 英文 key 顺序）
 *   - buildResumeRadarData(scores)    → 简历诊断雷达数据
 *   - buildInterviewRadarData(scores) → 模拟面试雷达数据
 *   - emptyResumeRadar() / emptyInterviewRadar() → 空态数据
 *
 * 历史保留：
 *   - mapResumeScores / mapInterviewScores 暂时保留供旧调用方使用（已废弃，逐步迁移）
 */

// ─────────────────────────────────────────────
// 原始维度定义
// ─────────────────────────────────────────────

/**
 * 简历诊断原始六维。
 * 来自 ResumeDiagnosis.vue 的 DIAGNOSIS_LABELS（英文 key）+ DIAGNOSIS_LABEL_CN（中文标签）。
 * indicators[i].name 与 valueKeys[i] 严格对齐。
 */
export const RESUME_INDICATORS = [
  { name: '关键词匹配', max: 100, key: 'keywordMatch' },
  { name: '经历含金量', max: 100, key: 'experienceQuality' },
  { name: '数据化程度', max: 100, key: 'dataDriven' },
  { name: '技能完整性', max: 100, key: 'skillCompleteness' },
  { name: '逻辑排版',   max: 100, key: 'layoutLogic' },
  { name: '核心竞争力', max: 100, key: 'coreCompetitiveness' }
]

/**
 * 模拟面试原始六维。
 * 来自 PremiumInterview.vue 的 RADAR_LABELS（英文 key）。
 */
export const INTERVIEW_INDICATORS = [
  { name: '专业技能', max: 100, key: 'professional' },
  { name: '逻辑分析', max: 100, key: 'logic' },
  { name: '沟通表达', max: 100, key: 'communication' },
  { name: '问题解决', max: 100, key: 'problemSolving' },
  { name: '综合潜力', max: 100, key: 'potential' },
  { name: '抗压韧性', max: 100, key: 'resilience' }
]

// ─────────────────────────────────────────────
// 工具
// ─────────────────────────────────────────────

function clampScore(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 0
  return Math.max(0, Math.min(100, num))
}

function safeParseScores(scores) {
  if (!scores) return null
  if (typeof scores === 'object') return scores
  if (typeof scores === 'string') {
    try { return JSON.parse(scores) } catch { return null }
  }
  return null
}

// ─────────────────────────────────────────────
// 公开构建器
// ─────────────────────────────────────────────

/**
 * 构建简历诊断雷达数据。
 *
 * @param {object|string|null} scores - 原始 scores 对象或 JSON 字符串
 * @returns {{ indicators: Array, values: number[] }}
 */
export function buildResumeRadarData(scores) {
  const parsed = safeParseScores(scores) || {}
  return {
    indicators: RESUME_INDICATORS.map(i => ({ name: i.name, max: i.max })),
    values: RESUME_INDICATORS.map(i => clampScore(parsed[i.key]))
  }
}

/**
 * 构建模拟面试雷达数据。
 *
 * @param {object|string|null} scores - 原始 scores 对象或 JSON 字符串
 * @returns {{ indicators: Array, values: number[] }}
 */
export function buildInterviewRadarData(scores) {
  const parsed = safeParseScores(scores) || {}
  return {
    indicators: INTERVIEW_INDICATORS.map(i => ({ name: i.name, max: i.max })),
    values: INTERVIEW_INDICATORS.map(i => clampScore(parsed[i.key]))
  }
}

/** 空态：简历六维 indicators + 全 0 values */
export function emptyResumeRadar() {
  return {
    indicators: RESUME_INDICATORS.map(i => ({ name: i.name, max: i.max })),
    values: [0, 0, 0, 0, 0, 0]
  }
}

/** 空态：面试六维 indicators + 全 0 values */
export function emptyInterviewRadar() {
  return {
    indicators: INTERVIEW_INDICATORS.map(i => ({ name: i.name, max: i.max })),
    values: [0, 0, 0, 0, 0, 0]
  }
}

/**
 * 判断 scores 对象是否包含至少一个非 0 评分（用于"该记录暂无评分数据"提示）
 */
export function hasNonZeroScores(scores) {
  const parsed = safeParseScores(scores)
  if (!parsed) return false
  return Object.values(parsed).some(v => {
    const n = Number(v)
    return Number.isFinite(n) && n > 0
  })
}

// ─────────────────────────────────────────────
// 历史兼容（已废弃，保留供 userStore 旧调用方）
// ─────────────────────────────────────────────

export const RADAR_DIMENSIONS = [
  '技术能力', '沟通表达', '项目经验', '学习能力', '团队协作', '职业规划'
]

const RESUME_TO_RADAR = {
  skillCompleteness:   '技术能力',
  layoutLogic:         '沟通表达',
  experienceQuality:   '项目经验',
  keywordMatch:        '学习能力',
  coreCompetitiveness: '团队协作',
  dataDriven:          '职业规划'
}

const INTERVIEW_TO_RADAR = {
  professional:   '技术能力',
  communication:  '沟通表达',
  problemSolving: '项目经验',
  logic:          '学习能力',
  resilience:     '团队协作',
  potential:      '职业规划'
}

function mapScoresWithTable(rawScores, mapping) {
  const out = {}
  if (!rawScores || typeof rawScores !== 'object') return out
  for (const [enKey, cnKey] of Object.entries(mapping)) {
    if (enKey in rawScores) {
      out[cnKey] = clampScore(rawScores[enKey])
    }
  }
  return out
}

/** @deprecated 改用 buildResumeRadarData */
export function mapResumeScores(rawScores) {
  return mapScoresWithTable(rawScores, RESUME_TO_RADAR)
}

/** @deprecated 改用 buildInterviewRadarData */
export function mapInterviewScores(rawScores) {
  return mapScoresWithTable(rawScores, INTERVIEW_TO_RADAR)
}
