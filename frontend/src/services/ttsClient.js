/**
 * ttsClient.js — 后端 TTS 接口客户端
 *
 * 单一入口:synthesizeAudio({ text, voice?, style?, format?, signal? }) → Promise<Blob>
 *
 * 设计:
 *   - 走 /api/tts/synthesize,带 getAuthHeaders 的 Authorization
 *   - 直接返回 Blob(后端用 Response 透传 audio/mpeg 字节,不再走 base64 JSON 中转)
 *   - 调用方自行 URL.createObjectURL(blob) 喂给 <audio>,自行 revoke
 *   - 支持 AbortSignal:外部按钮重复点击/卸载时可中止
 */

import { getAuthHeaders } from '@/services/authService.js'

const API_BASE_URL = '/api'

/** 与后端 Settings.TTS_MAX_TEXT_LEN 同步,避免无谓打到后端再被拒 */
export const TTS_MAX_TEXT_LEN = 3000

/**
 * 朗读前清理 Markdown 标记。
 *
 * 仅用于送给 TTS 的文本,不影响页面展示。处理项:
 *   - 代码围栏 ```lang ... ```                整段剔除
 *   - 行内 `code` 反引号                       去围,保留内容
 *   - 图片 ![alt](url)                         保留 alt
 *   - 链接 [text](url) / [text][ref]           保留 text
 *   - 标题  #..######                          去掉前缀井号
 *   - 加粗 **x** / __x__,斜体 *x* / _x_        去围
 *   - 列表  - / * / +,有序 1.                  去前缀
 *   - 引用  > quote                            去前缀
 *   - 水平线 --- *** ___                       整行删除
 *   - 表格管道 |                               转空格
 *   - HTML 标签                                直接剥离
 *   - 多余空白/空行压缩                        统一为单空格 + 双换行
 *
 * @param {string} text  原始 Markdown 文本
 * @returns {string}     适合 TTS 朗读的纯文本
 */
export function cleanTtsText(text) {
  if (!text) return ''
  let out = String(text)

  // 1. 代码围栏(整段剔除,避免读出大段代码)
  out = out.replace(/```[\s\S]*?```/g, ' ')
  // 2. 行内 `code` —— 仅去围
  out = out.replace(/`([^`\n]+)`/g, '$1')
  // 3. 图片 ![alt](url) → alt(图片需先于链接处理,前缀含 ! 区分)
  out = out.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
  // 4. 链接 [text](url) → text
  out = out.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  // 5. 标题前缀  ##... 
  out = out.replace(/^\s{0,3}#{1,6}\s+/gm, '')
  // 6. 加粗(双星/双下划线)
  out = out.replace(/\*\*([^*\n]+)\*\*/g, '$1')
  out = out.replace(/__([^_\n]+)__/g, '$1')
  // 7. 斜体(单星/单下划线,要求两侧非字母数字以避免误伤 file_name 之类)
  out = out.replace(/(^|[^\w*])\*([^*\n]+)\*(?=[^\w*]|$)/g, '$1$2')
  out = out.replace(/(^|[^\w_])_([^_\n]+)_(?=[^\w_]|$)/g, '$1$2')
  // 8. 列表项前缀:无序 - / * / +
  out = out.replace(/^\s{0,3}[-*+]\s+/gm, '')
  // 9. 列表项前缀:有序 1. 2.
  out = out.replace(/^\s{0,3}\d+\.\s+/gm, '')
  // 10. 引用块 >
  out = out.replace(/^\s{0,3}>\s?/gm, '')
  // 11. 水平线 整行
  out = out.replace(/^\s*(?:[-*_]\s*){3,}$/gm, '')
  // 12. 表格管道转空格(简化处理,不重建表格语义)
  out = out.replace(/\|/g, ' ')
  // 13. 残留 HTML 标签(marked 渲染前文本里偶尔会有)
  out = out.replace(/<\/?[a-zA-Z][^>]*>/g, '')
  // 14. 压缩水平空白 + 三连及以上空行 → 双换行 + 行首尾 trim
  out = out.replace(/[ \t]+/g, ' ')
  out = out.replace(/\n{3,}/g, '\n\n')
  out = out.replace(/^[ \t]+|[ \t]+$/gm, '')

  return out.trim()
}

/**
 * 合成语音。
 *
 * @param {object} options
 * @param {string} options.text     待朗读文本(必填)
 * @param {string} [options.voice]  预置音色名(可选)
 * @param {string} [options.style]  自然语言风格指令(可选)
 * @param {('mp3'|'wav')} [options.format] 输出格式(可选,默认后端走 mp3)
 * @param {AbortSignal} [options.signal]   AbortController.signal,用于主动取消
 * @returns {Promise<Blob>} 音频 Blob,可直接 URL.createObjectURL 播放
 * @throws {Error} 文本超长或后端 4xx/5xx 时抛出,error.message 是后端 detail
 */
export async function synthesizeAudio({ text, voice, style, format, signal } = {}) {
  const trimmed = String(text || '').trim()
  if (!trimmed) throw new Error('文本不能为空')
  if (trimmed.length > TTS_MAX_TEXT_LEN) {
    throw new Error(`文本过长(>${TTS_MAX_TEXT_LEN} 字),请缩短后再试`)
  }

  const body = { text: trimmed }
  if (voice)  body.voice  = voice
  if (style)  body.style  = style
  if (format) body.format = format

  const resp = await fetch(`${API_BASE_URL}/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
    signal
  })

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const err = await resp.json()
      if (err?.detail) detail = err.detail
    } catch {
      /* 响应体不是 JSON */
    }
    throw new Error(detail)
  }

  // 后端直接返回 audio/mpeg 字节流
  return await resp.blob()
}
