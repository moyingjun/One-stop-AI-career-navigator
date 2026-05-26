/**
 * stripUnicodeWhitespace.js — 去除字符串中所有 Unicode 空白字符
 *
 * 满足 Requirement 1.4:
 *   - 「生成简历预览」按钮启用条件:剥离全部 Unicode 空白后剩余可见字符 ≥ 10
 *
 * 处理范围:
 *   - 标准空白:\s(空格、制表符、换行、回车等)
 *   - 全角空格 U+3000
 *   - 零宽空格 U+200B、零宽连接 U+200C / U+200D、零宽 NBSP U+FEFF
 *   - 行内分隔符 U+2028 / U+2029
 *   - 蒙古语元音分隔符 U+180E
 *
 * 纯函数,不读 DOM、不发 HTTP、不依赖任何全局状态。
 */

const UNICODE_WHITESPACE_RE = /[\s\u3000\u200B\u200C\u200D\u2028\u2029\u180E\uFEFF]+/g

/**
 * @param {unknown} value
 * @returns {string}
 */
export function stripUnicodeWhitespace(value) {
  if (typeof value !== 'string') return ''
  return value.replace(UNICODE_WHITESPACE_RE, '')
}

/**
 * 「生成简历预览」按钮的启用判定。
 * 满足 Requirement 1.4:剩余可见字符 ≥ 10 时返回 true。
 *
 * @param {unknown} value
 * @returns {boolean}
 */
export function canOpenWorkspace(value) {
  return stripUnicodeWhitespace(value).length >= 10
}
