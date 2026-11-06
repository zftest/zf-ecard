/**
 * 错误归一化：把 axios 的异常折叠成一种前端好处理的结构。
 *
 * 为什么要有这一层：
 * axios 抛出来的东西形状极其不统一 —— 超时是 ECONNABORTED、断网没有 response、
 * 4xx 有 response.data.error、5xx 可能连 body 都不是 JSON。
 * 如果每个页面自己判断，就会出现「词库页弹一个英文报错、练习页什么都不弹」。
 * 统一在这里收口，页面只管读 normalized.message 和 normalized.details。
 */

/**
 * 不该弹全局错误的错误码。
 *
 * AUDIO_NOT_AVAILABLE：它不是一个"错误"，是"这个词没有录音文件"的正常信号。
 * 前端拿到它要做的是切到设备语音并在界面上标注「设备语音（演示）」，
 * 弹一个红色 Toast 说"该词暂无音频"纯属噪音 —— 用户根本没做错任何事，
 * 而且下一个词可能就有音频了，弹窗毫无意义。
 */
export const SILENT_CODES = new Set(['AUDIO_NOT_AVAILABLE'])

/** 后端错误码 → 面向孩子/家长的中文文案。没匹配到的走兜底。 */
const MESSAGES = {
  VALIDATION_ERROR: '填写的内容需要调整一下',
  NOT_FOUND: '没有找到这条内容',
  METHOD_NOT_ALLOWED: '这个操作暂时不支持',
  CONFLICT: '现在还不能这么做',
  SESSION_FINISHED: '这组练习已经结束了',
  SESSION_EXPIRED: '这组练习超过 2 小时了，重新开始一组吧',
  EMPTY_POOL: '这个范围里还没有可以练习的词',
  POOL_INSUFFICIENT: '可练习的词比要求的少，已经按最多能出的题数开始',
  FILE_TOO_LARGE: '文件太大了，换一个小一点的',
  IMPORT_PARSE_FAILED: '这个文件读不出来，检查一下格式',
  INTERNAL_ERROR: '服务出了点问题，稍后再试',
}

const FALLBACK_4XX = '这次请求没有被接受，请检查后重试'
const NETWORK_MESSAGE = '网络连接不上，检查一下网络再试'

/**
 * @typedef {Object} NormalizedError
 * @property {string} code            后端错误码，或前端合成的 NETWORK_ERROR / TIMEOUT
 * @property {string} message         可直接展示的中文
 * @property {Array<{field: string, message: string}>} details  字段级错误，表单用
 * @property {string|null} requestId  5xx 时带上，方便对着服务端日志查
 * @property {number|null} status     HTTP 状态码，网络错误为 null
 * @property {boolean} retryable      重试有意义吗（5xx / 网络类为 true）
 * @property {boolean} silent         是否应该跳过全局提示
 * @property {boolean} expected       是否属于预期内的"业务信号"而非故障
 */

/** @returns {NormalizedError} */
export function normalizeError(error) {
  // 1) 请求被取消（组件卸载、路由切换时主动 abort）—— 不是错误，静默丢掉
  if (error?.code === 'ERR_CANCELED') {
    return build({
      code: 'CANCELED',
      message: '',
      status: null,
      retryable: false,
      silent: true,
      expected: true,
    })
  }

  // 2) 超时
  if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
    return build({
      code: 'TIMEOUT',
      message: '等服务响应太久了，稍后再试',
      status: null,
      retryable: true,
    })
  }

  // 3) 断网 / 服务没起来 / 被 CORS 拦掉 —— axios 这三种情况都是"没有 response"
  if (!error?.response) {
    return build({
      code: 'NETWORK_ERROR',
      message: NETWORK_MESSAGE,
      status: null,
      retryable: true,
    })
  }

  const { status, data } = error.response
  const payload = data && typeof data === 'object' ? data : {}
  const apiError = payload.error && typeof payload.error === 'object' ? payload.error : {}
  const requestId = payload.request_id || null

  // 4) 字段级校验失败：把后端 details 原样带出去，表单据此标红
  const details = Array.isArray(apiError.details)
    ? apiError.details.filter((item) => item && typeof item.field === 'string')
    : []

  // 5) 5xx：不把后端文案直接抛给用户。
  //    后端 500 的 message 是"服务器内部错误"，对用户没有信息量；
  //    真正有用的是 request_id —— 用户报障时把它给到，能直接在日志里定位。
  if (status >= 500) {
    return build({
      code: apiError.code || 'INTERNAL_ERROR',
      message: requestId
        ? `服务出了点问题，稍后再试（问题编号 ${requestId}）`
        : '服务出了点问题，稍后再试',
      details: [],
      requestId,
      status,
      retryable: true,
    })
  }

  // 6) 4xx：用后端给的中文文案。后端的 message 已经是写给人看的
  //    （"该词不在此技能维度的错词本中"），前端再改一遍只会走样。
  const code = apiError.code || 'CLIENT_ERROR'
  const message = apiError.message || MESSAGES[code] || FALLBACK_4XX

  return build({
    code,
    message,
    details,
    requestId,
    status,
    retryable: false,
  })
}

function build({
  code,
  message,
  details = [],
  requestId = null,
  status = null,
  retryable = false,
  silent = false,
  expected = false,
}) {
  const isSilent = silent || SILENT_CODES.has(code)
  return {
    code,
    message,
    details,
    requestId,
    status,
    retryable,
    silent: isSilent,
    expected,
  }
}

/** 把字段级错误摊平成 { 字段名: 文案 }，供表单直接绑定。 */
export function toFieldErrors(details = []) {
  const map = {}
  for (const item of details) {
    if (!map[item.field]) map[item.field] = item.message
  }
  return map
}
