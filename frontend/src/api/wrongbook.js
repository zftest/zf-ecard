import { api } from './client'
import { cleanParams } from './query'

/** 错词本。 */

/**
 * 错词本列表。
 *
 * 一行 = 一个词 × 一个技能。同一个单词可能出现在多行（拼写错过、听音也错过），
 * 这是后端刻意的设计，前端按 `skill` 分组展示即可，不要去重。
 *
 * @param {Object} params
 * @param {string} [params.skill]       题型名（不是库里的技能名），如 zh_to_en
 * @param {string} [params.due_before]  ISO 8601，只返回该时刻前到期的
 * @param {'due'|'wrong_count'|'recent'} [params.sort='due']
 * @param {number} [params.page]
 * @param {number} [params.page_size]
 */
export function listWrongbook(learnerId, params = {}) {
  return api.get(`/learners/${encodeURIComponent(learnerId)}/wrongbook`, {
    params: cleanParams(params),
  })
}

/**
 * 手动标记已掌握 / 重置回第 1 盒。
 *
 * `master` 幂等（第二次 affected_senses = 0 仍返回 200），
 * `reset` 对已掌握的词也生效，是「取消掌握」的唯一入口。
 *
 * @param {'master'|'reset'} action
 */
export function updateWrongbookEntry(learnerId, wordId, { skill, action }) {
  return api.patch(`/learners/${encodeURIComponent(learnerId)}/wrongbook/${wordId}`, {
    skill,
    action,
  })
}
