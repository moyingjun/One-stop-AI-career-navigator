const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

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
    headers: { 'Content-Type': 'application/json' },
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

export { API_BASE_URL, ensureUUID, callAgent, callAgentAsync, llmService }
