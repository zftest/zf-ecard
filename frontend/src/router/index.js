import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由。
 *
 * history 模式需要服务端配合：任何 /app/xxx 都要回落到 index.html，
 * 否则用户刷新 /app/words 会拿到 404。Flask 侧的 spa.py 已经处理了。
 *
 * 全部页面懒加载：首屏只需要首页那几个 chunk，
 * 把 8 个页面打成一个包会让首屏白等 200KB 用不到的词库页代码。
 */

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '学习首页' },
  },
  {
    path: '/words',
    name: 'words',
    component: () => import('@/views/WordsView.vue'),
    meta: { title: '单词库' },
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('@/views/ConfigView.vue'),
    meta: { title: '分类默写' },
  },
  {
    path: '/practice',
    name: 'practice',
    component: () => import('@/views/PracticeView.vue'),
    meta: { title: '默写作答', focus: true },
  },
  {
    path: '/result',
    name: 'result',
    component: () => import('@/views/ResultView.vue'),
    meta: { title: '练习结果', focus: true },
  },
  {
    path: '/wrongbook',
    name: 'wrongbook',
    component: () => import('@/views/WrongbookView.vue'),
    meta: { title: '错词复习' },
  },
  {
    path: '/import',
    name: 'import',
    component: () => import('@/views/ImportView.vue'),
    meta: { title: '词库导入' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '学习设置' },
  },
  {
    // 兜底：未匹配的路径回首页，而不是留一个空白页
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 浏览器前进/后退时还原原位置，正常跳转回到顶部
    return savedPosition || { top: 0 }
  },
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · 词练` : '词练 · 初中英语单词'
})

export default router
