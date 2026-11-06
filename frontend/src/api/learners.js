import { api } from './client'
import { cleanParams } from './query'

/** 学习者档案与统计。 */

export function getLearner(learnerId) {
  return api.get(`/learners/${encodeURIComponent(learnerId)}`)
}

/**
 * 学习统计概览。
 * @param {number} days 趋势天数，只允许 7 / 14 / 30（后端白名单）
 */
export function getStatsOverview(learnerId, days = 7) {
  return api.get(`/learners/${encodeURIComponent(learnerId)}/stats/overview`, {
    params: cleanParams({ days }),
  })
}
