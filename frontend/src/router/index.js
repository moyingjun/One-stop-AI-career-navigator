import { createRouter, createWebHistory } from 'vue-router'

// ─────────────────────────────────────────────
// JWT 过期检查（不依赖 Pinia，避免循环依赖）
// ─────────────────────────────────────────────

/**
 * 解析 JWT Payload，失败返回 null
 * @param {string} token
 * @returns {object|null}
 */
function parseJwtPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

/**
 * 判断 localStorage 中的 token 是否有效（存在且未过期）
 * 提前 60 秒视为过期，给刷新留出窗口
 * @returns {boolean}
 */
function hasValidToken() {
  try {
    const token = localStorage.getItem('token')
    if (!token || token.trim().length === 0) return false

    const payload = parseJwtPayload(token)
    if (!payload || typeof payload.exp !== 'number') return false

    const nowSeconds = Math.floor(Date.now() / 1000)
    return nowSeconds < payload.exp - 60
  } catch {
    return false
  }
}

const routes = [
  // ── 公开路由（无需鉴权）──────────────────────────────────────────
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/Landing.vue')
  },
  {
    path: '/auth',
    name: 'Auth',
    component: () => import('@/Auth.vue')
  },

  // ── 受保护路由（requiresAuth: true）────────────────────────────────
  // 所有需要登录或完成 Setup 才能访问的页面均标记 requiresAuth
  {
    path: '/setup',
    name: 'GlobalSetup',
    component: () => import('@/GlobalSetup.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/resume-diagnosis',
    name: 'ResumeDiagnosis',
    component: () => import('@/ResumeDiagnosis.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/interview',
    name: 'Interview',
    component: () => import('@/PremiumInterview.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/career-planning',
    name: 'CareerPlanning',
    component: () => import('@/CareerPlanning.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history-archive',
    name: 'HistoryArchive',
    component: () => import('@/HistoryArchive.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/files',
    name: 'KnowledgeBase',
    component: () => import('@/KnowledgeBase.vue'),
    meta: { requiresAuth: true }
  },

  // ── 重定向路由 ──────────────────────────────────────────────────
  {
    path: '/premium-interview',
    redirect: '/interview'
  },
  {
    path: '/mock-interview',
    redirect: '/interview'
  },
  {
    path: '/saved-chats',
    redirect: '/history-archive'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 全局路由守卫
 *
 * 访问控制逻辑：
 * 1. 目标路由不需要鉴权（/ 和 /auth）→ 直接放行
 * 2. 已有有效 token（存在且 JWT exp 未过期）且目标为 /auth → 重定向至 /dashboard
 * 3. 有效 token → 放行所有受保护路由
 * 4. 无有效 token → 重定向至 /auth
 *
 * ⚠️  token 有效性基于 JWT Payload 的 exp 字段判断（提前 60 秒视为过期），
 *     不依赖 Pinia Store，避免路由守卫与 Store 的循环依赖。
 */
router.beforeEach((to) => {
  try {
    const validToken = hasValidToken()

    // 已登录用户访问 /auth 时，直接跳转到工作台
    if (to.path === '/auth' && validToken) {
      return '/dashboard'
    }

    // 目标路由不需要鉴权，直接放行（包括 / 和 /auth）
    if (!to.meta.requiresAuth) {
      return true
    }

    // 有效 token → 放行受保护路由
    if (validToken) {
      return true
    }

    // 无有效 token → 重定向至 /auth
    return '/auth'
  } catch (e) {
    console.warn('[Router Guard] 异常:', e)
    return '/auth'
  }
})

export default router
