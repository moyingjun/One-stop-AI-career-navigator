/**
 * resumeFilename.js — 简历导出文件名构造
 *
 * 满足 Requirement 9.7:
 *   - 默认格式:<姓名>_<目标岗位>_<时间戳>.<扩展名>
 *   - basics.name 为空 / null / 缺失时,前缀回落 `resume`
 *   - 替换跨平台非法字符 / \ : * ? " < > | 为 _
 *   - 不含扩展名部分截断到 100 字符以内
 *   - 扩展名严格匹配 pdf / docx,其他值兜底 pdf
 *
 * 纯函数,不读 DOM、不依赖时区配置(用 ISO 8601 UTC 时间戳)。
 */

const ILLEGAL_CHAR_RE = /[\\/:*?"<>|]/g
const ALLOWED_EXTS = new Set(['pdf', 'docx'])

/**
 * 把 basics 中的字段单元(可能是 {value, status} 形式或裸字符串)归一化为字符串。
 */
function readBasicsField(basics, key) {
  if (!basics || typeof basics !== 'object') return ''
  const cell = basics[key]
  if (cell == null) return ''
  if (typeof cell === 'string') return cell
  if (typeof cell === 'object' && typeof cell.value === 'string') return cell.value
  return ''
}

/**
 * 生成与时区无关的 ISO 8601 UTC 时间戳(秒精度,文件名安全)。
 * 形如 `20240101T120000Z`。
 */
function buildTimestamp(date = new Date()) {
  const iso = date.toISOString() // "2024-01-01T12:00:00.000Z"
  return iso.replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')
}

/**
 * @param {object} basics — Resume_JSON.basics(允许 null/undefined)
 * @param {string} ext — 期望扩展名(pdf | docx),其他值兜底 pdf
 * @param {Date} [now] — 可选注入时间(便于测试)
 * @returns {string} — 形如 `张三_前端工程师_20240101T120000Z.pdf`
 */
export function buildExportFilename(basics, ext, now = new Date()) {
  const name = readBasicsField(basics, 'name').trim()
  const role = readBasicsField(basics, 'targetRole').trim()
  const ts = buildTimestamp(now)

  const safeExt = ALLOWED_EXTS.has(ext) ? ext : 'pdf'
  const prefix = name || 'resume'
  const raw = role ? `${prefix}_${role}_${ts}` : `${prefix}_${ts}`

  // (a) 跨平台非法字符替换为 _
  let sanitized = raw.replace(ILLEGAL_CHAR_RE, '_')
  // 收敛连续下划线
  sanitized = sanitized.replace(/_{3,}/g, '__')
  // (b) 不含扩展名长度截断到 100 字符
  if (sanitized.length > 100) {
    sanitized = sanitized.slice(0, 100)
  }

  return `${sanitized}.${safeExt}`
}
