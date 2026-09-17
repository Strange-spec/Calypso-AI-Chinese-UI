import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '态势大屏' }
  },
  {
    path: '/guardrails',
    name: 'GuardrailsCenter',
    component: () => import('../views/GuardrailsCenter.vue'),
    meta: { title: '安全护栏运营中心' }
  },
  {
    path: '/playground',
    redirect: '/guardrails?tab=playground'
  },
  {
    path: '/redteam',
    name: 'RedTeam',
    component: () => import('../views/RedTeam.vue'),
    meta: { title: '红队任务与报告' }
  },
  {
    path: '/audit',
    name: 'AuditLogs',
    component: () => import('../views/AuditLogs.vue'),
    meta: { title: '安全审计日志' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { title: '系统与连接配置' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  if (to.meta && to.meta.title) {
    document.title = `${to.meta.title} - Calypso AI 中文运营控制台`
  }
})

export default router
