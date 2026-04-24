import { createRouter, createWebHistory } from 'vue-router'
import Landing from '@/Landing.vue'
import Dashboard from '@/Dashboard.vue'
import ResumeDiagnosis from '@/ResumeDiagnosis.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: Landing
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/resume-diagnosis',
    name: 'ResumeDiagnosis',
    component: ResumeDiagnosis
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
