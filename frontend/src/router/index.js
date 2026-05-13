import { createRouter, createWebHistory } from 'vue-router'
import Landing from '@/Landing.vue'
import Dashboard from '@/Dashboard.vue'
import ResumeDiagnosis from '@/ResumeDiagnosis.vue'
import PremiumInterview from '@/PremiumInterview.vue'
import GlobalSetup from '@/GlobalSetup.vue'
import CareerPlanning from '@/CareerPlanning.vue'
import HistoryArchive from '@/HistoryArchive.vue'
import SavedChats from '@/SavedChats.vue'
import KnowledgeBase from '@/KnowledgeBase.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: Landing
  },
  {
    path: '/auth',
    name: 'Auth',
    component: () => import('../Auth.vue')
  },
  {
    path: '/setup',
    name: 'GlobalSetup',
    component: GlobalSetup
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/resume-diagnosis',
    name: 'ResumeDiagnosis',
    component: ResumeDiagnosis
  },
  {
    path: '/interview',
    name: 'Interview',
    component: PremiumInterview
  },
  {
    path: '/premium-interview',
    redirect: '/interview'
  },
  {
    path: '/mock-interview',
    redirect: '/interview'
  },
  {
    path: '/career-planning',
    name: 'CareerPlanning',
    component: CareerPlanning
  },
  {
    path: '/history-archive',
    name: 'HistoryArchive',
    component: HistoryArchive
  },
  {
    path: '/saved-chats',
    name: 'SavedChats',
    component: SavedChats
  },
  {
    path: '/files',
    name: 'KnowledgeBase',
    component: KnowledgeBase
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from) => {
  // 无需认证的页面直接放行
  if (!to.meta.requiresAuth) {
    return true
  }

  // 需要认证的页面：检查 token 或 guest 角色
  try {
    const token = localStorage.getItem('token')
    // token 非空且非纯空白字符串时放行
    if (token && token.trim().length > 0) {
      return true
    }

    // guest 角色放行
    const userRole = localStorage.getItem('userRole')
    if (userRole === 'guest') {
      return true
    }
  } catch (e) {
    // localStorage 不可用时（如浏览器隐私模式）默认放行
    console.warn('[Router Guard] localStorage 不可用，默认放行:', e)
    return true
  }

  // 两者均不满足，重定向至首页
  return '/'
})

export default router
