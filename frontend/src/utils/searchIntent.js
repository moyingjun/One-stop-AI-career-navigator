/**
 * searchIntent.js —— Dashboard 今日建议 → 快捷搜索关键词生成
 *
 * 用途:
 *   把一条「今日建议」(简历优化建议已就绪 / 面试模拟热度 TOP1 / 院校政策更新 ... )
 *   按主题归类后,拼接成可直接打开 Bing 搜索的 URL。
 *
 * 不引入第三方依赖,只用 URL/encodeURIComponent。
 * 不做联网抓取、不接 RAG、不做摘要。
 */

const SEARCH_BASE = 'https://cn.bing.com/search?q='

/** 简历类关键词 */
const RESUME_KEYWORDS    = ['简历', 'resume', 'cv']
/** 面试类关键词 */
const INTERVIEW_KEYWORDS = ['面试', 'interview']
/** 职业规划类关键词 */
const CAREER_KEYWORDS    = ['职业规划', '规划', '路线', '发展路径', '学习路线', 'career path', 'roadmap']
/** 院校 / 升学类关键词 */
const SCHOOL_KEYWORDS    = ['院校', '高校', '升学', '专业', '分数线', '招生', '考研', '志愿']

function lower(text) {
  return String(text || '').toLowerCase()
}

function hasAny(haystack, needles) {
  const t = lower(haystack)
  if (!t) return false
  return needles.some((kw) => t.includes(lower(kw)))
}

/**
 * 推断建议主题。
 * @param {{type?: string, title?: string, text?: string}} suggestion
 * @returns {'resume' | 'interview' | 'career' | 'school' | 'fallback'}
 */
export function inferIntent(suggestion) {
  if (!suggestion || typeof suggestion !== 'object') return 'fallback'
  const haystack = [suggestion.type, suggestion.title, suggestion.text].filter(Boolean).join(' ')
  if (hasAny(haystack, RESUME_KEYWORDS))    return 'resume'
  if (hasAny(haystack, INTERVIEW_KEYWORDS)) return 'interview'
  if (hasAny(haystack, CAREER_KEYWORDS))    return 'career'
  if (hasAny(haystack, SCHOOL_KEYWORDS))    return 'school'
  return 'fallback'
}

/**
 * 取建议的"主标题"用于兜底搜索词。
 * 优先 title → text → type → 空串。
 */
function pickTitle(suggestion) {
  if (!suggestion) return ''
  return (suggestion.title || suggestion.text || suggestion.type || '').trim()
}

/**
 * 把 string[] 拼接成搜索关键字(去空 + 去重 + 单空格分隔)。
 */
function joinKeywords(parts) {
  const out = []
  const seen = new Set()
  for (const p of parts) {
    const v = String(p || '').trim()
    if (!v) continue
    if (seen.has(v)) continue
    seen.add(v)
    out.push(v)
  }
  return out.join(' ')
}

/**
 * 根据建议 + 目标岗位生成 Bing 搜索 URL。
 *
 * 规则:
 *   - 简历类  → "<目标岗位> 简历优化 项目经验怎么写"
 *   - 面试类  → "<目标岗位> 面试高频题 回答技巧"
 *   - 规划类  → "<目标岗位> 学习路线 职业发展"
 *   - 院校类  → "<原标题> 招生政策 分数线"
 *   - 兜底    → "<目标岗位> <原标题>" 或仅 "<原标题>"
 *
 * @param {{type?: string, title?: string, text?: string}} suggestion
 * @param {string} [targetJob] 当前用户目标岗位(可空)
 * @returns {string} Bing 搜索 URL,已对查询参数做 encodeURIComponent
 */
export function buildSearchUrl(suggestion, targetJob = '') {
  const job = String(targetJob || '').trim()
  const title = pickTitle(suggestion)
  const intent = inferIntent(suggestion)

  let parts = []
  switch (intent) {
    case 'resume':
      parts = [job, '简历优化', '项目经验怎么写']
      break
    case 'interview':
      parts = [job, '面试高频题', '回答技巧']
      break
    case 'career':
      parts = [job, '学习路线', '职业发展']
      break
    case 'school':
      parts = [title, '招生政策', '分数线']
      break
    default:
      parts = [job, title]
  }

  let q = joinKeywords(parts)
  // 极端兜底:连标题/岗位都没有,用 type 字段或空串
  if (!q) q = pickTitle(suggestion) || (suggestion?.type || '').toString()

  return SEARCH_BASE + encodeURIComponent(q)
}

/**
 * 在新标签页安全打开 URL(rel=noopener,noreferrer)。
 * 失败时返回 false,调用方可以 toast 提示。
 */
export function openInNewTab(url) {
  if (!url) return false
  try {
    window.open(url, '_blank', 'noopener,noreferrer')
    return true
  } catch (e) {
    console.warn('[searchIntent] window.open 失败:', e)
    return false
  }
}
