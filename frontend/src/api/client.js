import axios from 'axios'

import { normalizeError } from './errors'

/**
 * 全站唯一的 HTTP 客户端。
 *
 * 三条纪律：
 * 1. 页面不直接 import axios，只用这里的 api.get/post/patch。
 *    否则拦截器会被绕过，错误提示、重试策略就各写各的。
 * 2. 响应拦截器直接返回 response.data，调用方拿到的就是业务数据，
 *    不用每次写 res.data.data。
 * 3. 错误统一抛出 NormalizedError（见 errors.js），页面只读 code / message / details。
 */

const BASE_URL = '/api/v1'

/** 5xx 与网络错误的重试次数（只对 GET 生效，见下方说明） */
const MAX_RETRIES = 2

/** 全局错误监听器。由 main.js 注册成 Toast，避免 client 反向依赖 UI 组件。 */
let errorListener = null

export function setErrorListener(fn) {
  errorListener = fn
}

/** 每次请求前可以加个自定义头，方便后端日志里区分来源 */
const APP_VERSION = 'b6'

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    Accept: 'application/json',
    'X-Client': `web/${APP_VERSION}`,
  },
})

http.interceptors.request.use((config) => {
  // GET 加时间戳会破坏浏览器缓存，这里不做任何缓存破坏；
  // 需要强制刷新时由调用方传 params: { _t: Date.now() }。
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const normalized = normalizeError(error)

    // 主动取消、白名单错误（如 AUDIO_NOT_AVAILABLE）不打扰用户
    if (!normalized.silent && errorListener) {
      errorListener(normalized)
    }

    // 把归一化结果挂回原错误对象：调用方既可以用 try/catch 读 err.normalized，
    // 也能继续访问 err.response（排查时有用）
    error.normalized = normalized
    return Promise.reject(error)
  },
)

/**
 * 是否自动重试。
 *
 * ⚠️ 这里和通用最佳实践（"5xx 自动重试最多 3 次"）刻意不同：**只重试 GET**。
 *
 * 原因是本项目的写接口不都是幂等的：
 * - `POST /practice/sessions` 重试会建出两个会话，孩子做题记录被劈成两半；
 * - `POST /answers` 在网络超时时可能服务端已经写成功，重试虽然被后端判为
 *   "重复提交"而不重复计数，但会让前端以为自己刚提交的那一次失败过，
 *   从而在 UI 上多显示一次错误。
 *
 * 5xx 对写操作的处理方式是：**把错误如实告诉用户，由他点"重试"**。
 * 用户主动点的那一次是他自己的决定，语义清晰，也不会产生隐藏的重复副作用。
 */
function isRetryable(error, config) {
  const method = (config?.method || 'get').toLowerCase()
  if (method !== 'get' && method !== 'head') return false
  const normalized = error.normalized
  return Boolean(normalized?.retryable)
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function request(config) {
  let lastError = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
    try {
      return await http.request(config)
    } catch (error) {
      lastError = error
      if (attempt === MAX_RETRIES || !isRetryable(error, config)) break
      // 指数退避：300ms → 900ms。抖一下就能好的情况不要连打三次。
      await sleep(300 * 3 ** attempt)
    }
  }

  throw lastError
}

export const api = {
  get: (url, config) => request({ ...config, url, method: 'get' }),
  post: (url, data, config) => request({ ...config, url, data, method: 'post' }),
  patch: (url, data, config) => request({ ...config, url, data, method: 'patch' }),
  delete: (url, config) => request({ ...config, url, method: 'delete' }),
}

/**
 * 直接从错误里取归一化结构。页面 catch 之后用它。
 *
 * 用法：
 *   try { await api.post(...) } catch (e) { const err = errorOf(e); ... }
 */
export function errorOf(error) {
  return error?.normalized || normalizeError(error)
}

export { BASE_URL }
export default api
