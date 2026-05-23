/**
 * llm_service.js — LLM / Agent API 调用与 SSE 流式通信服务
 *
 * 核心函数：
 *   - streamChat(payload, onMessage, onDone, onError)
 *     强制使用原生 fetch + ReadableStream，严格处理：
 *       1. TextDecoder("utf-8") + { stream: true } 防止中文多字节截断
 *       2. 按 \n\n 缓冲拼接完整 SSE 事件块后再解析
 *       3. 严格匹配后端事件类型：reply / meta / done / error
 *
 * ⚠️  UI 性能铁律（打字机流式输出）：
 *     onMessage 回调只追加增量内容（delta），不传完整字符串。
 *     Vue 组件层面应将 rawContent 作为 ref，每次 += delta，
 *     Markdown 渲染（marked.js）使用 computed 懒计算，
 *     避免每个 chunk 触发全量 DOM 重绘导致页面闪烁或滚动条乱跳。
 */

import { getAuthHeaders } from '@/services/authService'

// API 基础路径（通过 Vite proxy 转发，无需硬编码端口）
const API_BASE_URL = '/api'

// ─────────────────────────────────────────────
// 核心：SSE 流式通信
// ─────────────────────────────────────────────

/**
 * 通用 SSE 流式聊天函数
 *
 * @param {object} options
 * @param {string}   options.endpoint  — API 端点路径，如 '/agent/chat'
 * @param {object}   options.payload   — 请求体（user_query, history, 等）
 * @param {Function} options.onMessage — 收到 event:reply 时调用，参数为增量内容字符串（delta）
 * @param {Function} options.onMeta    — 收到 event:meta 时调用，参数为解析后的 meta 对象
 * @param {Function} options.onDone    — 收到 event:done 时调用，参数为 done payload（含 record_id）
 * @param {Function} options.onError   — 收到 event:error 或网络异常时调用，参数为错误消息字符串
 * @returns {Promise<void>}
 */
export async function streamChat({ endpoint, payload, onMessage, onMeta, onDone, onError }) {
  // 确保回调函数存在（防御性默认值）
  const _onMessage = onMessage || (() => {})
  const _onMeta    = onMeta    || (() => {})
  const _onDone    = onDone    || (() => {})
  const _onError   = onError   || (() => {})

  let errorFired = false  // 确保 onError 最多触发一次

  const fireError = (msg) => {
    if (!errorFired) {
      errorFired = true
      _onError(msg)
    }
  }

  let reader = null

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      // 尝试解析后端错误 detail
      let detail = `请求失败（HTTP ${response.status}）`
      try {
        const body = await response.json()
        if (body?.detail) detail = body.detail
      } catch { /* 响应体非 JSON */ }
      fireError(detail)
      return
    }

    reader = response.body.getReader()

    // ⚠️  TextDecoder 必须在循环外创建，保持跨 chunk 的解码状态
    //     { stream: true } 确保多字节中文字符不会在 chunk 边界处被截断
    const decoder = new TextDecoder('utf-8')

    // SSE 缓冲区：按 \n\n 分隔完整事件块
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        // 流正常结束（服务端关闭连接）
        // 若还有未处理的缓冲内容，尝试处理一次
        if (buffer.trim()) {
          processBlock(buffer.trim(), _onMessage, _onMeta, _onDone, fireError)
        }
        break
      }

      // ⚠️  { stream: true } 是防止中文乱码的关键
      buffer += decoder.decode(value, { stream: true })

      // 按 \n\n 切割完整 SSE 事件块
      // 最后一个可能不完整，留到下次迭代继续拼接
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''  // 保留末尾不完整片段

      for (const block of blocks) {
        const trimmed = block.trim()
        if (!trimmed) continue  // 跳过空块（心跳）

        const isDone = processBlock(trimmed, _onMessage, _onMeta, _onDone, fireError)
        if (isDone) {
          // 收到 done 事件，主动取消读取，释放连接
          try { reader.cancel() } catch { /* 忽略取消错误 */ }
          return
        }
      }
    }

  } catch (err) {
    // 网络层异常（断网、AbortError 等）
    if (err?.name === 'AbortError') return  // 主动取消，不触发 onError
    fireError(err?.message || '网络连接异常，请重试')
  } finally {
    // 确保 reader 被释放
    try { reader?.releaseLock?.() } catch { /* 忽略 */ }
  }
}

/**
 * 处理单个完整的 SSE 事件块
 *
 * @param {string}   block      — 一个完整的 SSE 事件块（\n\n 之间的内容）
 * @param {Function} onMessage  — reply 回调
 * @param {Function} onMeta     — meta 回调
 * @param {Function} onDone     — done 回调
 * @param {Function} fireError  — error 回调（最多触发一次）
 * @returns {boolean} — true 表示收到 done，调用方应停止读取
 */
function processBlock(block, onMessage, onMeta, onDone, fireError) {
  // 忽略 SSE 注释行（心跳，如 ": ping"）
  if (block.startsWith(':')) return false

  const lines = block.split('\n')
  let eventName = ''
  let dataStr = ''

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataStr = line.slice(5).trim()
    }
  }

  // 忽略无事件名或无数据的块
  if (!eventName || !dataStr) return false

  // 解析 JSON data
  let parsed = null
  try {
    parsed = JSON.parse(dataStr)
  } catch {
    // data 非 JSON（如纯文本），包装为 { content: dataStr }
    parsed = { content: dataStr }
  }

  switch (eventName) {
    case 'reply':
    case 'message': {
      // ⚠️  只传增量内容（delta），不传完整字符串
      //     Vue 组件层面 rawContent += delta，避免全量重绘
      //     'message' 是 interview_agent 使用的事件名，兼容处理
      const delta = parsed?.payload?.content ?? parsed?.content ?? ''
      if (delta) onMessage(delta)
      break
    }

    case 'meta': {
      const meta = parsed?.payload ?? parsed ?? {}
      onMeta(meta)
      break
    }

    case 'done': {
      const donePayload = parsed?.payload ?? parsed ?? {}
      onDone(donePayload)
      return true  // 通知调用方停止读取
    }

    case 'error': {
      const errMsg = parsed?.payload?.message ?? parsed?.message ?? parsed?.content ?? '服务端发生错误'
      fireError(errMsg)
      break
    }

    case 'warning': {
      // warning 事件：非致命，记录到 console，不中断流
      console.warn('[SSE warning]', parsed?.payload?.message ?? parsed?.message ?? dataStr)
      break
    }

    default:
      // 未知事件类型，静默忽略
      break
  }

  return false
}

// ─────────────────────────────────────────────
// 兼容层：保留旧接口，内部委托给 streamChat
// ─────────────────────────────────────────────

/**
 * @deprecated 请使用 streamChat()
 * 保留此函数以兼容现有组件调用，后续逐步迁移
 */
export async function callAgentAsync(endpoint, userMessage, history = [], onChunk, extraParams = {}) {
  await streamChat({
    endpoint,
    payload: { user_query: userMessage, history, ...extraParams },
    onMessage: onChunk,
    onError: (msg) => console.error('[callAgentAsync error]', msg)
  })
}

/**
 * @deprecated 请使用 streamChat()
 * 保留此函数以兼容 PremiumInterview.vue 等现有组件
 */
export async function streamInterviewChat(endpoint, payload, onChunk, onError) {
  await streamChat({
    endpoint,
    payload,
    onMessage: onChunk,
    onError
  })
}

// ─────────────────────────────────────────────
// 工具函数
// ─────────────────────────────────────────────

export async function ensureUUID() {
  try {
    if (crypto.randomUUID) return crypto.randomUUID()
  } catch {}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Date.now() + Math.random() * 16) % 16 | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

/**
 * 非流式 Agent 调用（用于需要完整响应的场景）
 */
export async function callAgent(endpoint, userMessage, history = [], extraParams = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ user_query: userMessage, history, ...extraParams })
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || errorData.message || `请求失败 (HTTP ${response.status})`)
  }

  return response
}

export const llmService = {
  async diagnoseResume(file, userId) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId || 'anonymous')
    const resp = await fetch(`${API_BASE_URL}/resume/diagnose-upload`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
      body: formData
    })
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}))
      throw new Error(errData.detail || '诊断请求失败')
    }
    return resp.json()
  }
}

export { API_BASE_URL }
