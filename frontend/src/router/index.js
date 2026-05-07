import { createRouter, createWebHistory } from 'vue-router'
import Landing from '@/Landing.vue'
import Dashboard from '@/Dashboard.vue'
import ResumeDiagnosis from '@/ResumeDiagnosis.vue'
import PremiumInterview from '@/PremiumInterview.vue'
import GlobalSetup from '@/GlobalSetup.vue'
import CareerPlanning from '@/CareerPlanning.vue'
import HistoryArchive from '@/HistoryArchive.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: Landing
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
    meta: { requiresSetup: true }
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from) => {
  if (to.meta.requiresSetup) {
    const candidateName = localStorage.getItem('candidate_name')
    const resumeText = localStorage.getItem('resume_text')

    // 拦截：如果没有姓名或简历，强制打回 setup
    if (!candidateName || !resumeText) {
      return '/setup' 
    }
  }

  // 放行：条件都满足，或者是不需要校验的页面，直接 return true
  return true 
})

export default router