import { createRouter, createWebHistory } from 'vue-router'

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
 * 全局路由守卫（Requirements 6.1 ~ 6.4）
 *
 * 访问控制逻辑：
 * 1. 已有有效 token 且目标为 /auth → 重定向至 /dashboard（避免已登录用户看到登录页）
 * 2. 目标路由不需要鉴权（meta.requiresAuth 为 falsy）→ 直接放行（包括 / 和 /auth）
 * 3. 有效 token（非空且非纯空白）→ 放行所有受保护路由（Requirements 6.3）
 * 4. guest 模式（userRole === 'guest'）→ 仅允许访问 / 和 /auth，
 *    其余受保护路由一律重定向至 /auth（Requirements 6.1, 6.2）
 * 5. 无有效 token 且非 guest 模式 → 重定向至 /auth（Requirements 6.4）
 */
router.beforeEach((to) => {
  try {
    const token = localStorage.getItem('token')
    const userRole = localStorage.getItem('userRole')
    const hasValidToken = Boolean(token && token.trim().length > 0)

    // 已登录用户访问 /auth 时，直接跳转到工作台，避免重复登录
    if (to.path === '/auth' && hasValidToken) {
      return '/dashboard'
    }

    // 目标路由不需要鉴权，直接放行（包括 / 和 /auth）
    if (!to.meta.requiresAuth) {
      return true
    }

    // 有效 token（非空且非纯空白）时放行所有受保护路由（Requirements 6.3）
    if (hasValidToken) {
      return true
    }

    // guest 模式：受保护路由一律重定向至 /auth（Requirements 6.1, 6.2）
    // 公开路由（/ 和 /auth）已在上方 !requiresAuth 分支放行，
    // 此处只处理 guest 访问受保护路由的情况
    if (userRole === 'guest') {
      return '/auth'
    }

    // 无有效 token 且非 guest 模式：重定向至 /auth（Requirements 6.4）
    return '/auth'
  } catch (e) {
    // localStorage 不可用时（如浏览器隐私模式严格限制）仅放行公开路由
    console.warn('[Router Guard] localStorage 不可用:', e)
    return '/auth'
  }
})

export default router
