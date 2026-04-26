import { createRouter, createWebHistory } from 'vue-router'
import Landing from '@/Landing.vue'
import Dashboard from '@/Dashboard.vue'
import ResumeDiagnosis from '@/ResumeDiagnosis.vue'
import PremiumInterview from '@/PremiumInterview.vue'
import GlobalSetup from '@/GlobalSetup.vue'
import CareerPlanning from '@/CareerPlanning.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresSetup) {
    const candidateName = localStorage.getItem('candidate_name')
    const targetRole = localStorage.getItem('target_role')
    const resumeText = localStorage.getItem('resume_text')

    if (!candidateName || !targetRole || !resumeText) {
      next('/setup')
      return
    }
  }

  next()
})

export default router