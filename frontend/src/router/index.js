import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes = [
  { path: '/', redirect: '/overview' },
  {
    path: '/overview',
    name: 'overview',
    component: () => import('../pages/OverviewPage.vue'),
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('../pages/UsersPage.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/classes',
    name: 'classes',
    component: () => import('../pages/ClassesPage.vue'),
  },
  {
    path: '/coursewares',
    name: 'coursewares',
    component: () => import('../pages/CoursewaresPage.vue'),
  },
  {
    path: '/evaluations',
    name: 'evaluations',
    component: () => import('../pages/EvaluationsPage.vue'),
    meta: { roles: ['teacher'] },
  },
  {
    path: '/survey',
    name: 'survey',
    component: () => import('../pages/SurveyPage.vue'),
    meta: { roles: ['student'] },
  },
  {
    path: '/discussions',
    name: 'discussions',
    component: () => import('../pages/DiscussionsPage.vue'),
  },
  {
    path: '/messages',
    name: 'messages',
    component: () => import('../pages/MessagesPage.vue'),
  },
  {
    path: '/rag',
    name: 'rag',
    component: () => import('../pages/RagPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (!auth.isLoggedIn) {
    await auth.bootstrap()
  }

  if (!auth.isLoggedIn && to.name !== 'overview') {
    next({ name: 'overview' })
    return
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    next({ name: 'overview' })
    return
  }

  next()
})

export default router
