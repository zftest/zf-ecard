import { api } from './client'
import { cleanParams } from './query'

/** 练习会话。 */

/**
 * 建会话。
 *
 * 注意：这是 POST，**不会自动重试**（见 client.js 里的说明）。
 * 网络抖动时若自动重试，会建出两个会话，孩子的作答记录被劈成两半。
 *
 * @param {Object} body
 * @param {string} [body.learner_id='default']
 * @param {'unit'|'theme'|'wrongbook'|'all'} body.range
 * @param {string} [body.range_value]   unit 传单元 ID，theme 传主题名
 * @param {'zh_to_en'|'audio_to_en'|'en_to_zh'|'phonetic_to_en'} body.mode
 * @param {number} [body.size=20]       5-50
 * @param {'random'|'sequential'|'weak_first'} [body.order='random']
 * @param {boolean} [body.hint_enabled=true]
 */
export function createSession(body) {
  return api.post('/practice/sessions', body)
}

export function getSession(sessionId, { includeAnswers = false } = {}) {
  return api.get(`/practice/sessions/${sessionId}`, {
    params: cleanParams({ include_answers: includeAnswers }),
  })
}

/**
 * 提交答案。
 *
 * 判错也返回 200（correct:false），只有协议层问题才是 4xx。
 * 所以调用方不能用"请求成功 = 答对"来判断，必须读 correct 字段。
 *
 * @param {Object} body
 * @param {number} body.item_id
 * @param {string} body.answer
 * @param {boolean} [body.hint_used=false]
 * @param {number} [body.replay_count=0]
 * @param {number} [body.elapsed_ms=0]
 */
export function submitAnswer(sessionId, body) {
  return api.post(`/practice/sessions/${sessionId}/answers`, body)
}

/** 结束会话。幂等：重复调用返回完全一致的汇总。 */
export function finishSession(sessionId) {
  return api.post(`/practice/sessions/${sessionId}/finish`, {})
}
