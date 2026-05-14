const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

/**
 * 从 localStorage 读取 JWT token 并返回 Authorization 请求头对象。
 * 不依赖 Vue/Pinia，可在任意模块中安全调用。
 */
function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function ensureUUID() {
  try {
    if (crypto.randomUUID) return crypto.randomUUID()
  } catch {}
  const crypto = await import('crypto').catch(() => null)
  if (crypto?.randomUUID) return crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Date.now() + Math.random() * 16) % 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

async function callAgent(endpoint, userMessage, history = [], extraParams = {}) {
  const requestBody = {
    user_query: userMessage,
    history: history,
    ...extraParams
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(requestBody)
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const errorMsg = errorData.detail || errorData.message || `请求失败 (HTTP ${response.status})`
    throw new Error(errorMsg)
  }

  return response
}

async function callAgentAsync(endpoint, userMessage, history = [], onChunk, extraParams = {}) {
  try {
    const response = await callAgent(endpoint, userMessage, history, extraParams)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim()
        } else if (line.startsWith('data:')) {
          const dataStr = line.substring(5).trim()
          if (!dataStr) continue

          if (currentEvent === 'reply') {
            try {
              const parsed = JSON.parse(dataStr)
              const content = parsed?.payload?.content || ''
              if (content && onChunk) onChunk(content)
            } catch {}
          }
        }
      }
    }
  } catch (err) {
    console.error('流式调用失败:', err)
    throw err
  }
}

/**
 * SSE 流式面试聊天消费函数
 *
 * @param {string} endpoint - API 端点路径，如 '/interview/chat'
 * @param {Object} payload - 请求体，包含 user_query, history, resume_text, jd_text, difficulty
 * @param {Function} onChunk - 每收到一个内容片段时调用，参数为内容字符串
 * @param {Function} onError - 流式传输失败时调用，参数为错误信息字符串（每次调用最多触发一次）
 * @returns {Promise<void>} - 流正常结束或发生错误后 resolve（不 reject）
 */
async function streamInterviewChat(endpoint, payload, onChunk, onError) {
  let errorFired = false  // 确保 onError 最多调用一次

  try {
    const response = await fetch(API_BASE_URL + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      if (!errorFired) {
        errorFired = true
        onError('[网络连接异常，请重试]')
      }
      return
    }

    const reader = response.body.getReader()
    // 每次调用创建一个 TextDecoder 实例（stream: true 防止 CJK 多字节字符截断）
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      // 解码字节块并追加到缓冲区
      buffer += decoder.decode(value, { stream: true })

      // 按 \n\n 切割完整 SSE 块，保留末尾不完整片段
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop()  // 最后一个可能不完整，留到下次迭代

      for (const block of blocks) {
        // 忽略心跳注释行（以 ': ' 开头）
        if (block.startsWith(': ')) continue

        const lines = block.split('\n')
        let eventName = ''
        let dataStr = ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventName = line.substring(6).trim()
          } else if (line.startsWith('data:')) {
            dataStr = line.substring(5).trim()
          }
        }

        // 忽略 ping 事件
        if (eventName === 'ping') continue

        // 流结束
        if (eventName === 'done') return

        // 解析 data 字段
        if (dataStr) {
          try {
            const parsed = JSON.parse(dataStr)
            const content = parsed.content || ''
            if (content) {
              // event: message 和 event: error 都通过 onChunk 追加到消息气泡
              onChunk(content)
            }
          } catch {
            // JSON 解析失败，静默跳过
          }
        }
      }
    }
  } catch (error) {
    if (!errorFired) {
      errorFired = true
      onError('[网络连接异常，请重试]')
    }
  }
}

const llmService = {
  async diagnoseResume(file, userId) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId || 'anonymous')
    const resp = await fetch(`${API_BASE_URL}/resume/diagnose-upload`, {
      method: 'POST',
      body: formData
    })
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}))
      throw new Error(errData.detail || '诊断请求失败')
    }
    return resp.json()
  }
}

export { API_BASE_URL, ensureUUID, callAgent, callAgentAsync, streamInterviewChat, llmService }
