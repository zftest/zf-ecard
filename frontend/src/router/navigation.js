/**
 * 导航配置。
 *
 * 集中定义的理由：侧栏、移动端底部标签、面包屑、页面标题都读同一份数据。
 * 分散在三个组件里各写一遍，加一个页面就会漏改其中一处，
 * 表现为"侧栏能点进去，但底部标签里没有"。
 */

export const NAV_ITEMS = [
  { name: 'dashboard', path: '/', label: '学习首页', index: '01', en: 'LEARNING DESK' },
  { name: 'words', path: '/words', label: '单词库', index: '02', en: 'WORD LIBRARY' },
  { name: 'config', path: '/config', label: '分类默写', index: '03', en: 'DICTATION SETUP' },
  { name: 'wrongbook', path: '/wrongbook', label: '错词复习', index: '04', en: 'MISTAKE NOTEBOOK' },
  { name: 'import', path: '/import', label: '词库导入', index: '05', en: 'IMPORT STUDIO' },
  { name: 'settings', path: '/settings', label: '学习设置', index: '06', en: 'SETTINGS' },
]

/**
 * 移动端底部标签只放 4 个主入口。
 * 6 个图标挤在 375px 宽的屏幕上，每个只剩 62px，手指一定会点错；
 * 导入和设置是低频操作，从首页的"更多"进即可。
 */
export const MOBILE_TAB_NAMES = ['dashboard', 'words', 'config', 'wrongbook']

export const MOBILE_TABS = NAV_ITEMS.filter((item) => MOBILE_TAB_NAMES.includes(item.name))

/** 练习结果页不在导航里（它属于一次会话的产物，不是常驻页面） */
export const PRACTICE_META = {
  practice: { label: '默写作答', en: 'DICTATION SESSION' },
  result: { label: '练习结果', en: 'SESSION RESULT' },
}

export function findNavItem(name) {
  return NAV_ITEMS.find((item) => item.name === name) || null
}
