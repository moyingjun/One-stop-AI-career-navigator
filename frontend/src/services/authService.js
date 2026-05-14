/**
 * authService.js — 前端鉴权服务
 *
 * 封装注册、登录、登出及鉴权请求头逻辑，供各组件统一调用。
 * 永远不在 localStorage 中存储明文密码（Requirements 16.4）。
 *
 * 依赖：
 *   - userStore（Pinia）：登出时重置用户画像
 *   - vue-router：401 自动跳转 /auth
 */

import { useUserStore } from '@/stores/userStore'
import router from '@/router/index.js'

/** 后端 API 基础路径 */
const API_BASE = '/api'

// ─────────────────────────────────────────────
// 内部工具函数
// ─────────────────────────────────────────────

/**
 * 统一处理 API 响应：
 *   - 2xx → 返回解析后的 JSON
 *   - 401 → 自动登出并跳转 /auth，再抛出错误
 *   - 其他非 2xx → 抛出含 detail 消息的 Error，供组件展示
 *
 * @param {Response} response - fetch 返回的 Response 对象
 * @returns {Promise<any>} 解析后的响应体
 */
async function handleResponse(response) {
  if (response.ok) {
    return response.json()
  }

  // 尝试解析后端返回的 detail 字段
  let detail = `请求失败（HTTP ${response.status}）`
  try {
    const body = await response.json()
    if (body && body.detail) {
      detail = body.detail
    }
  } catch {
    // 响应体非 JSON，保留默认 detail
  }

  // 401：清除凭据并跳转登录页（Requirements 3.4, 7.5）
  if (response.status === 401) {
    _clearCredentials()
    router.push('/auth')
  }

  throw new Error(detail)
}

/**
 * 从 localStorage 清除 token 和 user_id（不触发 userStore 重置）
 * 仅供内部 401 自动处理使用。
 */
function _clearCredentials() {
  try {
    localStorage.removeItem('token')
    localStorage.removeItem('user_id')
  } catch {
    // localStorage 不可用时静默处理
  }
}

// ─────────────────────────────────────────────
// 公开 API
// ─────────────────────────────────────────────

/**
 * 注册新用户
 *
 * 调用 POST /api/auth/register，返回 { access_token, user_id, username }。
 * 非 2xx 响应时抛出含 detail 消息的 Error（Requirements 7.1, 7.6）。
 *
 * @param {string} username - 用户名（1-50 字符，字母数字下划线）
 * @param {string} password - 密码（≥8 字符），永远不写入 localStorage
 * @param {string} [email]  - 可选邮箱
 * @returns {Promise<{ access_token: string, user_id: number, username: string }>}
 */
export async function registerUser(username, password, email) {
  const payload = { username, password }
  if (email) {
    payload.email = email
  }

  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return handleResponse(response)
}

/**
 * 用户登录
 *
 * 调用 POST /api/auth/login，成功后将 access_token 写入 localStorage['token']、
 * user_id 写入 localStorage['user_id']（Requirements 2.5, 7.2）。
 * 失败时清除已有凭据并抛出含 detail 消息的 Error（Requirements 7.6）。
 *
 * @param {string} username - 用户名
 * @param {string} password - 密码，永远不写入 localStorage
 * @returns {Promise<{ access_token: string, user_id: number, username: string }>}
 */
export async function loginUser(username, password) {
  let response
  try {
    response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
  } catch (networkError) {
    // 网络层错误（断网、CORS 等）
    throw new Error('网络连接失败，请检查网络后重试')
  }

  if (!response.ok) {
    // 登录失败：清除旧凭据（Requirements 2.5）
    _clearCredentials()

    let detail = `登录失败（HTTP ${response.status}）`
    try {
      const body = await response.json()
      if (body && body.detail) {
        detail = body.detail
      }
    } catch {
      // 响应体非 JSON，保留默认 detail
    }
    throw new Error(detail)
  }

  const data = await response.json()

  // 写入凭据到 localStorage（明文密码永远不写入）
  try {
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user_id', String(data.user_id))
  } catch {
    // localStorage 写入失败时静默处理（隐私模式或存储已满）
  }

  return data
}

/**
 * 获取鉴权请求头
 *
 * 读取 localStorage 中的 token，返回 { Authorization: "Bearer <token>" }；
 * 若 token 不存在或为空，返回空对象（Requirements 7.3）。
 *
 * @returns {{ Authorization: string } | {}}
 */
export function getAuthHeaders() {
  try {
    const token = localStorage.getItem('token')
    if (token && token.trim().length > 0) {
      return { Authorization: `Bearer ${token}` }
    }
  } catch {
    // localStorage 不可用时静默处理
  }
  return {}
}

/**
 * 登出
 *
 * 清除 localStorage 中的 token 和 user_id，并通过 userStore.updateUserProfile({})
 * 将用户画像重置为默认空值（Requirements 7.4）。
 *
 * 注意：此函数不负责路由跳转，由调用方决定跳转目标。
 */
export function logout() {
  // 清除凭据
  _clearCredentials()

  // 重置 Pinia 用户画像（Requirements 7.4）
  try {
    const userStore = useUserStore()
    userStore.updateUserProfile({})
  } catch {
    // Store 不可用时（如测试环境）静默处理
  }
}
