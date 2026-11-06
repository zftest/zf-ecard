import { api } from './client'
import { cleanParams } from './query'

/** 词库相关的读接口。全部是 GET，天然幂等，可享受自动重试。 */

export function getUnits(params = {}) {
  return api.get('/units', { params: cleanParams(params) })
}

export function getThemes(params = {}) {
  return api.get('/themes', { params: cleanParams(params) })
}

/**
 * 词库列表。
 *
 * @param {Object} params
 * @param {string} [params.q]          搜索词，同时匹配英文词形与中文释义
 * @param {number} [params.unit]       单元 ID
 * @param {string} [params.theme]      主题
 * @param {string[]} [params.pos]      词性，如 ['n.', 'v.']（内部拼成 n.,v.）
 * @param {string[]} [params.status]   掌握状态，如 ['new', 'learning']
 * @param {string} [params.skill]      题型，决定 status 按哪个技能的口径算
 * @param {string} [params.sort]       unit / alpha / wrong_first / recent
 * @param {number} [params.page]
 * @param {number} [params.page_size]
 */
export function listWords(params = {}) {
  return api.get('/words', { params: cleanParams(params) })
}

export function getWord(wordId, params = {}) {
  return api.get(`/words/${wordId}`, { params: cleanParams(params) })
}
