import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getLearner, getStatsOverview } from '@/api/learners'
import { errorOf } from '@/api/client'

/**
 * 学习者 store。
 *
 * MVP 只有一个孩子用，所以 learner_id 固定为 'default'。
 * 但仍然存进 localStorage 而不是硬编码常量 ——
 * 下一步要做多孩子/多账号时，只需要在这里换 id，其他页面零改动。
 */

const STORAGE_KEY = 'zf-ecard:learner_id'
const DEFAULT_LEARNER = 'default'

/**
 * 读持久化的 learner_id。
 *
 * 必须包 try/catch：Safari 无痕模式、Chrome 禁用第三方 Cookie 时，
 * 访问 localStorage 会直接抛 SecurityError。
 * 不接这个异常，整个应用会在启动瞬间白屏，而错误信息只有一行
 * "Failed to read the 'localStorage' property"，完全看不出是持久化的问题。
 */
function readLearnerId() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved || DEFAULT_LEARNER
  } catch {
    return DEFAULT_LEARNER
  }
}

function writeLearnerId(id) {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    // 存不下就算了，本次会话内仍然可用
  }
}

export const useLearnerStore = defineStore('learner', () => {
  const learnerId = ref(readLearnerId())
  const profile = ref(null)
  const stats = ref(null)
  const loading = ref(false)
  const error = ref('')

  const displayName = computed(() => profile.value?.nickname || '同学')
  const today = computed(() => profile.value?.today || null)
  const todayDone = computed(() => today.value?.done ?? 0)
  const todayGoal = computed(() => today.value?.goal ?? 20)
  const todayAccuracy = computed(() => today.value?.accuracy ?? null)
  const streakDays = computed(() => today.value?.streak_days ?? 0)
  const totals = computed(() => profile.value?.totals || {})
  const wrongCount = computed(() => totals.value.wrongbook ?? 0)
  const settings = computed(() => profile.value?.settings || {})

  /** 今日目标完成度，0-1，用于首页进度环 */
  const goalRatio = computed(() => {
    const goal = todayGoal.value
    if (!goal) return 0
    return Math.min(1, todayDone.value / goal)
  })

  function setLearnerId(id) {
    const next = (id || '').trim() || DEFAULT_LEARNER
    learnerId.value = next
    writeLearnerId(next)
  }

  async function loadProfile() {
    loading.value = true
    error.value = ''
    try {
      profile.value = await getLearner(learnerId.value)
    } catch (err) {
      const normalized = errorOf(err)
      error.value = normalized.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadStats(days = 7) {
    try {
      stats.value = await getStatsOverview(learnerId.value, days)
    } catch (err) {
      // 统计是辅助信息，加载失败不该阻断首页 —— 只在控制台留痕，
      // 首页照常显示今日任务。
      console.warn('[learner] 统计加载失败', errorOf(err).message)
    }
  }

  async function refresh() {
    // 两个请求并行：串行会让首页多等一个 RTT，而它们互不依赖
    await Promise.all([loadProfile(), loadStats()])
  }

  return {
    learnerId,
    profile,
    stats,
    loading,
    error,
    displayName,
    today,
    todayDone,
    todayGoal,
    todayAccuracy,
    streakDays,
    totals,
    wrongCount,
    settings,
    goalRatio,
    setLearnerId,
    loadProfile,
    loadStats,
    refresh,
  }
})
