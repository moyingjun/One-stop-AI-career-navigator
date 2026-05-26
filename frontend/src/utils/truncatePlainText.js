/**
 * truncatePlainText.js — 草稿截断工具
 *
 * 满足 Requirement 1.2:
 *   - plain_text.length > 50000 时,截断到 50000 字符以内
 *   - s.length ≤ max 时,直接返回 s 本身
 *
 * 纯函数,不读 DOM、不发 HTTP。
 */

export const DEFAULT_PLAIN_TEXT_MAX = 50000

/**
 * @param {unknown} value
 * @param {number} [max=50000]
 * @returns {string}
 */
export function truncatePlainText(value, max = DEFAULT_PLAIN_TEXT_MAX) {
  if (typeof value !== 'string') return ''
  const limit = Number.isFinite(max) && max >= 0 ? Math.floor(max) : DEFAULT_PLAIN_TEXT_MAX
  if (value.length <= limit) return value
  return value.slice(0, limit)
}

/**
 * 判断当前字符串是否被截断后才能放进 workspace。
 *
 * @param {string} value
 * @param {number} [max=50000]
 */
export function isTextTruncated(value, max = DEFAULT_PLAIN_TEXT_MAX) {
  if (typeof value !== 'string') return false
  const limit = Number.isFinite(max) && max >= 0 ? Math.floor(max) : DEFAULT_PLAIN_TEXT_MAX
  return value.length > limit
}
