/**
 * authService.js — 前端鉴权服务
 *
 * 提供：
 *   - axios 实例（全局请求/响应拦截器）
 *   - sendCode()       — 发送邮箱验证码
 *   - registerWithCode() — 验证码注册
 *   - loginUser()      — 邮箱密码登录
 *   - logout()         — 登出并清除状态
 *   - getAuthHeaders() — 获取 Authorization 请求头
 *
 * ⚠️  循环依赖防御：
 *     userStore 在拦截器函数体内部按需获取（useUserStore()），
 *     而非在模块顶层 import 时立即调用，避免 Pinia 未初始化时的循环依赖。
 */

import axios from 'axios'

/** 后端 API 基础路径（通过 Vite proxy 转发） */
const API_BASE = '/api'

// ─────────────────────────────────────────────
// axios 实例
// ─────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// ── 请求拦截器：自动注入 Authorization Header ──
apiClient.interceptors.request.use(
  (config) => {
    // 登录/注册/发码接口不需要 token
    const publicPaths = ['/auth/login', '/auth/register', '/auth/send-code']
    const isPublic = publicPaths.some((p) => config.url?.includes(p))

    if (!isPublic) {
      try {
        const token = localStorage.getItem('token')
        if (token && token.trim().length > 0) {
          config.headers['Authorization'] = `Bearer ${token}`
        }
      } catch {
        // localStorage 不可用时静默处理
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── 响应拦截器：401 自动登出并跳转 /auth ──
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // ⚠️  在函数体内部按需获取 userStore，避免顶层循环依赖
      try {
        // 直接操作 localStorage（不依赖 Pinia）
        localStorage.removeItem('token')
        localStorage.removeItem('user_id')
        localStorage.removeItem('user_email')

        // 按需获取 userStore 实例并重置状态
        import('@/stores/userStore').then(({ useUserStore }) => {
          try {
            const userStore = useUserStore()
            userStore.logout()
          } catch {
            // Store 不可用时静默处理
          }
        })

        // 跳转到登录页（使用 window.location 避免循环依赖 router）
        if (window.location.pathname !== '/auth') {
          window.location.href = '/auth'
        }
      } catch {
        // 清理失败时静默处理
      }
    }
    return Promise.reject(error)
  }
)

// ─────────────────────────────────────────────
// 内部工具
// ─────────────────────────────────────────────

/**
 * 统一提取 axios 错误中的 detail 消息
 * @param {any} error
 * @param {string} fallback
 * @returns {string}
 */
function extractErrorMessage(error, fallback = '请求失败，请稍后重试') {
  return error?.response?.data?.detail || error?.message || fallback
}

// ─────────────────────────────────────────────
// 公开 API
// ─────────────────────────────────────────────

/**
 * 发送邮箱验证码
 *
 * @param {string} email          — 目标邮箱
 * @param {string} captchaToken   — Cloudflare Turnstile token（开发环境传 'mock_token'）
 * @returns {Promise<{ msg: string }>}
 */
export async function sendCode(email, captchaToken) {
  try {
    const { data } = await apiClient.post('/auth/send-code', {
      email,
      captcha_token: captchaToken
    })
    return data
  } catch (error) {
    throw new Error(extractErrorMessage(error, '验证码发送失败，请稍后重试'))
  }
}

/**
 * 邮箱验证码注册
 *
 * @param {string} email    — 注册邮箱
 * @param {string} password — 密码（≥8 字符）
 * @param {string} code     — 6 位数字验证码
 * @returns {Promise<{ access_token: string, user_id: number, email: string }>}
 */
export async function registerWithCode(email, password, code) {
  try {
    const { data } = await apiClient.post('/auth/register', { email, password, code })
    return data
  } catch (error) {
    throw new Error(extractErrorMessage(error, '注册失败，请稍后重试'))
  }
}

/**
 * 邮箱密码登录
 *
 * 成功后由调用方（组件）调用 userStore.login() 持久化 token。
 *
 * @param {string} email    — 登录邮箱
 * @param {string} password — 密码
 * @returns {Promise<{ access_token: string, user_id: number, email: string }>}
 */
export async function loginUser(email, password) {
  try {
    const { data } = await apiClient.post('/auth/login', { email, password })
    return data
  } catch (error) {
    throw new Error(extractErrorMessage(error, '邮箱或密码错误'))
  }
}

/**
 * 登出
 *
 * 清除 localStorage 凭据，并通过 userStore.logout() 重置 Pinia 状态。
 * 不负责路由跳转，由调用方决定跳转目标。
 */
export function logout() {
  try {
    localStorage.removeItem('token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('user_email')
  } catch {
    // 静默处理
  }

  // 按需获取 userStore，避免顶层循环依赖
  try {
    import('@/stores/userStore').then(({ useUserStore }) => {
      try {
        const userStore = useUserStore()
        userStore.logout()
      } catch {
        // Store 不可用时静默处理
      }
    })
  } catch {
    // 静默处理
  }
}

/**
 * 获取 Authorization 请求头对象
 *
 * 供原生 fetch 调用（SSE 流式请求）使用，不经过 axios 拦截器。
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
    // 静默处理
  }
  return {}
}
