import { reactive } from 'vue'

/**
 * Toast 队列（模块级单例）。
 *
 * 放在 .js 里而不是组件里，是为了让**非组件代码**也能弹提示 ——
 * 最典型的场景是 axios 拦截器：它在任意请求失败时都要提示用户，
 * 但它拿不到组件实例。如果 Toast 状态存在组件内，
 * 拦截器就只能靠事件总线或者全局变量，反而更绕。
 *
 * 为什么不用 pinia store：Toast 不属于业务状态，它不进 devtools 时间线、
 * 不需要持久化、不需要被别的 store 依赖。做成 store 只会让它看起来
 * 比实际重要。
 */

/** 成功/提示的默认停留时间。错误不走这个值（见下） */
const AUTO_DISMISS_MS = 3600

/** 错误默认常驻：带 request_id 的错误需要用户看清了去反馈，3 秒后消失等于没提示 */
const ERROR_DISMISS_MS = 0

const state = reactive({ items: [] })
let seq = 0

const timers = new Map()

function startTimer(id, duration) {
  if (!duration || duration <= 0) return
  clearTimer(id)
  timers.set(
    id,
    setTimeout(() => dismiss(id), duration),
  )
}

function clearTimer(id) {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

/**
 * 推一条提示。
 *
 * @param {string} message 主文案
 * @param {Object} [options]
 * @param {'info'|'success'|'error'} [options.type='info']
 * @param {string} [options.detail] 次要说明，如 request_id
 * @param {number} [options.duration] 毫秒；0 表示不自动消失
 */
function push(message, options = {}) {
  if (!message) return null

  const type = options.type || 'info'
  const duration =
    options.duration !== undefined
      ? options.duration
      : type === 'error'
        ? ERROR_DISMISS_MS
        : AUTO_DISMISS_MS

  // 去重：同类型同文案的提示不叠加。
  // 用户连点两次"保存"时，弹两条一模一样的错误只会让他以为坏了两次。
  const existing = state.items.find((item) => item.message === message && item.type === type)
  if (existing) {
    startTimer(existing.id, duration)
    return existing.id
  }

  const id = (seq += 1)
  state.items.push({
    id,
    type,
    message,
    detail: options.detail || '',
  })
  startTimer(id, duration)

  // 最多同时显示 3 条，超出的挤掉最旧的
  while (state.items.length > 3) {
    dismiss(state.items[0].id)
  }

  return id
}

function dismiss(id) {
  clearTimer(id)
  const index = state.items.findIndex((item) => item.id === id)
  if (index >= 0) state.items.splice(index, 1)
}

function clear() {
  for (const id of [...timers.keys()]) clearTimer(id)
  state.items.splice(0, state.items.length)
}

export const toast = {
  push,
  dismiss,
  clear,
  info: (message, options) => push(message, { ...options, type: 'info' }),
  success: (message, options) => push(message, { ...options, type: 'success' }),
  error: (message, options) => push(message, { ...options, type: 'error' }),
}

/** 组件里拿响应式队列用这个 */
export function useToast() {
  return { toasts: state.items, toast }
}
