import { createRouter, createWebHistory } from 'vue-router'
import store from '@/store'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guestOnly: true } },
  { path: '/signup', name: 'signup', component: () => import('@/views/SignupView.vue'), meta: { guestOnly: true } },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { requiresAuth: true } },
  { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { requiresAuth: true } },
  { path: '/transfer', name: 'transfer', component: () => import('@/views/TransferView.vue'), meta: { requiresAuth: true } },
  { path: '/transactions', name: 'transactions', component: () => import('@/views/TransactionHistoryView.vue'), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const isAuthenticated = store.getters['auth/isAuthenticated']

  if (to.meta.requiresAuth && !isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.guestOnly && isAuthenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
