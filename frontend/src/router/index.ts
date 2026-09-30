import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { playPageSound } from '@/sounds/soundEffects'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/pages/RegisterPage.vue'),
    meta: { public: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/pages/HomePage.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/pages/SettingsPage.vue'),
  },
  {
    path: '/study',
    name: 'study',
    component: () => import('@/pages/TodayStudyPage.vue'),
  },
  {
    path: '/quiz',
    name: 'quiz',
    component: () => import('@/pages/TodayQuizPage.vue'),
  },
  {
    path: '/wrong-words',
    name: 'wrong-words',
    component: () => import('@/pages/WrongWordsPage.vue'),
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('@/pages/ReviewQuizPage.vue'),
  },
  {
    path: '/archive',
    name: 'archive',
    component: () => import('@/pages/ArchiveQuizPage.vue'),
  },
  {
    path: '/summary',
    name: 'summary',
    component: () => import('@/pages/SummaryPage.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!to.meta.public && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.public && auth.isAuthenticated) {
    return { path: '/home' }
  }

  return true
})

// 进入白名单页面时播放对应开场语音（/review、/archive 等不在白名单，进入无声）
router.afterEach((to) => {
  playPageSound(to.path)
})

export default router
