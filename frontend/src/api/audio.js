import { BASE_URL } from './client'

/**
 * 发音。
 *
 * 刻意**不走 axios**：音频要做的是交给 <audio src> 或 Audio() 直接流式播放，
 * 让浏览器自己发 Range 请求、自己管缓存。用 axios 先下载成 ArrayBuffer
 * 再转 Blob URL，等于把浏览器的流式播放能力丢掉，一个词要等整个文件下完。
 *
 * 接口带 `Cache-Control: immutable`，所以同一个词第二次播放是零请求。
 */

/**
 * 发音地址。
 * @param {number} wordId
 * @param {'uk'|'us'} [accent='uk']
 */
export function audioUrl(wordId, accent = 'uk') {
  return `${BASE_URL}/audio/${wordId}?accent=${accent}`
}

/** 前端已知的音频可用性（来自词条上的 audio: {uk, us}）。 */
export function hasAudio(word, accent = 'uk') {
  return Boolean(word?.audio?.[accent])
}
