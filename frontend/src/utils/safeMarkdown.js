/**
 * safeMarkdown.js —— 聊天消息 Markdown 安全渲染
 *
 * 目标:
 *   - LLM / RAG 输出的内容里可能混入 raw HTML(包括 <img onerror>、<script>、<iframe> 等),
 *     之前直接 marked.parse 后 v-html 渲染存在 XSS 风险。
 *   - 本工具对 marked 做受限配置 + 输出层正则二次清洗,得到「只允许 Markdown 渲染产物,
 *     不允许任何 raw HTML」的安全字符串。
 *
 * 安全策略:
 *   1. 构建一个私有 Marked 实例,自定义 token 渲染器:
 *      - html token(包括 inline 与 block):直接返回空字符串,不输出任何原始 HTML。
 *      - link.href / image.src 通过 URL 协议白名单拦截 javascript: / data:text/html 等。
 *   2. 渲染结果再做一道正则清洗:
 *      - 剔除任何 on* 事件处理器属性(如 onerror= / onclick=)。
 *      - 剔除以 javascript: 或 data:text/html 开头的 href/src 值。
 *      - 剔除 <script> / <iframe> / <object> / <embed> 等危险标签(即便从转义里漏出来)。
 *   3. 不引入新依赖(已有 marked@18),保持构建轻量。
 *
 * 注意:
 *   - 仅供聊天消息显示使用,不要替换 Resume Builder / 系统知识库等其它需要 raw HTML 的场景。
 *   - 该方案只清洗"渲染层",不影响后端日志或 RAG 召回内容本身。
 */

import { Marked } from 'marked'

/** 允许出现在 href / src 协议的小写白名单。 */
const SAFE_URL_PROTOCOLS = ['http:', 'https:', 'mailto:', 'tel:', '#']

/**
 * 校验 URL 协议是否安全。
 * - 相对路径(不含协议)默认放行。
 * - 锚点(#xxx)放行。
 * - 显式 javascript: / data: / vbscript: 等一律拦截。
 */
function isSafeUrl(url) {
  if (typeof url !== 'string') return false
  const trimmed = url.trim()
  if (!trimmed) return false
  if (trimmed.startsWith('#')) return true
  // 没有协议头,视为相对路径,放行
  if (!/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) return true
  const lower = trimmed.toLowerCase()
  return SAFE_URL_PROTOCOLS.some((p) => lower.startsWith(p))
}

/** HTML 转义,用于拼接文本。 */
function escapeHtml(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 自定义 marked renderer:
 *   - html token(块级 / 内联):全部丢弃,确保任何 raw HTML 都不进入 DOM。
 *   - link / image:对 href / src 做协议白名单校验。
 */
const safeRenderer = {
  // marked@18 的 renderer 接口:返回字符串即用作渲染结果,返回 false 则走默认。
  html() {
    return ''
  },
  link({ href, title, tokens }) {
    const text = this.parser.parseInline(tokens || [])
    if (!isSafeUrl(href)) {
      // 不安全的链接,降级为纯文本
      return text
    }
    const safeHref = escapeHtml(href)
    const safeTitle = title ? ` title="${escapeHtml(title)}"` : ''
    return `<a href="${safeHref}"${safeTitle} rel="noopener noreferrer nofollow" target="_blank">${text}</a>`
  },
  image({ href, title, text }) {
    if (!isSafeUrl(href)) {
      return escapeHtml(text || '')
    }
    const safeHref = escapeHtml(href)
    const safeAlt = escapeHtml(text || '')
    const safeTitle = title ? ` title="${escapeHtml(title)}"` : ''
    return `<img src="${safeHref}" alt="${safeAlt}"${safeTitle} loading="lazy" />`
  },
}

const safeMarkedInstance = new Marked({
  gfm: true,
  breaks: true,
  // 注意:marked 在 token 解析阶段仍会识别 <html> 块,只要 renderer.html 返回空,就不会输出。
  renderer: safeRenderer,
})

/**
 * 二次正则清洗:覆盖极端边界情况(例如 marked 升级后 renderer 漏过的 raw HTML 片段)。
 *   - 移除 <script> / <iframe> / <object> / <embed> / <link> / <meta> / <style> 等危险标签
 *     (含开闭、自闭合形式)。
 *   - 移除任何 on* 事件处理器属性。
 *   - 把 javascript:/data:text/html 协议的 href/src 替换为 #。
 */
function stripDangerousHtml(html) {
  if (typeof html !== 'string' || !html) return ''
  let out = html
  // 1. 危险标签(及其内容,贪婪到对应闭合标签;无闭合的自闭合也一并删除)
  const dangerousTags = ['script', 'iframe', 'object', 'embed', 'style', 'link', 'meta', 'form', 'input', 'button', 'textarea', 'select', 'option']
  for (const tag of dangerousTags) {
    const blockRe = new RegExp(`<${tag}\\b[^>]*>[\\s\\S]*?</${tag}>`, 'gi')
    out = out.replace(blockRe, '')
    const selfRe = new RegExp(`<${tag}\\b[^>]*/?>`, 'gi')
    out = out.replace(selfRe, '')
  }
  // 2. on* 事件处理器(双引号 / 单引号 / 无引号三种形式)
  out = out.replace(/\son[a-z]+\s*=\s*"[^"]*"/gi, '')
  out = out.replace(/\son[a-z]+\s*=\s*'[^']*'/gi, '')
  out = out.replace(/\son[a-z]+\s*=\s*[^\s>]+/gi, '')
  // 3. 危险协议 href/src
  out = out.replace(/(href|src)\s*=\s*"\s*(javascript|vbscript|data\s*:\s*text\/html)[^"]*"/gi, '$1="#"')
  out = out.replace(/(href|src)\s*=\s*'\s*(javascript|vbscript|data\s*:\s*text\/html)[^']*'/gi, "$1='#'")
  return out
}

/**
 * 将 Markdown 文本渲染为「禁止 raw HTML」的安全 HTML 字符串。
 * 错误情况下回退为原文本的转义版本,绝不抛错也绝不返回原始 HTML。
 */
export function renderSafeMarkdown(text) {
  if (text == null) return ''
  const input = String(text)
  if (!input) return ''
  try {
    const rendered = safeMarkedInstance.parse(input)
    return stripDangerousHtml(rendered)
  } catch (e) {
    // 任何异常都退化成纯文本,绝不向 DOM 输出未受控字符串
    return escapeHtml(input)
  }
}

export default renderSafeMarkdown
