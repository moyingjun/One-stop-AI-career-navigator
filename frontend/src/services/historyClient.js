/**
 * historyClient.js — 历史记录 API 客户端
 *
 * 封装所有与 /api/history 相关的 HTTP 调用。
 * 统一处理 auth headers、错误、JSON 解析。
 *
 * 命名规范（record_type 枚举）：
 *   - resume_diagnosis    — 简历诊断
 *   - career_plan         — 职业规划
 *   - interview_session   — 模拟面试
 *   - dashboard_chat      — Dashboard ChatDock 归档对话
 */

import { getAuthHeaders } from './authService.js'

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

/**
 * 生成稳定的 session_id（前端 UUID）。
 * 用于三功能页和 ChatDock 的会话级幂等保存。
 */
export function generateSessionId(prefix = 'sess') {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}_${crypto.randomUUID()}`
  }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
}

/**
 * 通用 session upsert：所有自动保存场景的统一入口。
 *
 * @param {string} sessionId — 前端生成的稳定 session_id
 * @param {{
 *   record_type: 'resume_diagnosis' | 'career_plan' | 'interview_session' | 'dashboard_chat',
 *   user_input?: string,
 *   ai_result?: string,
 *   chat_history?: Array<{role: string, content: string}>,
 *   scores?: object,
 *   extra_data?: object
 * }} payload
 * @returns {Promise<{ success: boolean, record_id: number, session_id: string, updated_at: string, data: object }>}
 */
export async function upsertSession(sessionId, payload) {
  const body = {
    session_id: sessionId,
    record_type: payload.record_type,
    user_input: payload.user_input || '',
    ai_result: payload.ai_result || '',
    chat_history: payload.chat_history || [],
    scores: payload.scores || {},
    extra_data: payload.extra_data || {}
  }

  const response = await fetch(`${API_BASE_URL}/history/session/${sessionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * 兼容旧调用：归档 Dashboard ChatDock 对话。
 * 内部走 upsertSession，record_type 固定为 dashboard_chat。
 */
export async function archiveDashboardChat(session) {
  const { sessionId, messages, userInput, aiResult } = session
  const firstUserMsg = messages.find(m => m.role === 'user')
  const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai')
  const title = userInput || (firstUserMsg?.content || '').slice(0, 200)
  const summary = aiResult || (lastAiMsg?.content || '').slice(0, 500)

  return upsertSession(sessionId, {
    record_type: 'dashboard_chat',
    user_input: title,
    ai_result: summary,
    chat_history: messages,
    scores: {},
    extra_data: { message_count: messages.length }
  })
}

/**
 * 按 session_id 加载会话记录
 *
 * @param {string} sessionId
 * @returns {Promise<object|null>} 完整记录对象，404 时返回 null
 */
export async function loadSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/history/session/${sessionId}`, {
    headers: { ...getAuthHeaders() }
  })

  if (!response.ok) {
    if (response.status === 404) return null
    throw new Error(`HTTP ${response.status}`)
  }

  const data = await response.json()
  return data.data || null
}

/**
 * 列出当前用户的历史记录
 *
 * @param {{ limit?: number, has_scores?: boolean }} params
 * @returns {Promise<Array<object>>}
 */
export async function listHistory(params = {}) {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.has_scores) qs.set('has_scores', 'true')
  const url = `${API_BASE_URL}/history${qs.toString() ? '?' + qs.toString() : ''}`

  const response = await fetch(url, { headers: { ...getAuthHeaders() } })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const data = await response.json()
  return data.records || []
}

/**
 * 按 record_id 加载单条记录
 */
export async function loadRecordById(recordId) {
  const response = await fetch(`${API_BASE_URL}/history/${recordId}`, {
    headers: { ...getAuthHeaders() }
  })
  if (!response.ok) {
    if (response.status === 404) return null
    throw new Error(`HTTP ${response.status}`)
  }
  const data = await response.json()
  return data.data || null
}

/**
 * 切换收藏状态
 */
export async function toggleSave(recordId, isSaved) {
  const response = await fetch(`${API_BASE_URL}/history/${recordId}/save`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ is_saved: isSaved })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

/**
 * 删除单条记录
 */
export async function deleteRecord(recordId) {
  const response = await fetch(`${API_BASE_URL}/history/${recordId}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() }
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
