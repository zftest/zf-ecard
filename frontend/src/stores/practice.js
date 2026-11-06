import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { errorOf } from '@/api/client'
import { createSession, finishSession, submitAnswer } from '@/api/practice'

/**
 * 练习 store：一次练习会话的完整生命周期。
 *
 * 状态机：
 *   idle ──startSession──▶ active ──finish──▶ finished
 *                            │
 *                            └─ submit ─▶ (feedback 有值，等待"下一题")
 *
 * 为什么把会话状态放 store 而不是练习页组件里：
 * 结果页需要读 summary、错词页需要知道"本次错词"，
 * 状态放组件里一换路由就没了，用户从结果页点"只看错词"再返回就丢数据。
 */

/** 会话剩余时间不足这个值时提示用户（服务端 TTL 是 2 小时） */
const EXPIRE_WARN_MS = 5 * 60 * 1000

/**
 * 后端 SubmitAnswerBody 的硬上限，必须在这里夹住。
 *
 * `elapsed_ms: le=600000`、`replay_count: le=20` —— 这是服务端的防御性校验，
 * 但前端如果不夹，真实场景会踩到：孩子在一道题上想 12 分钟（走神、喝水、
 * 被叫去吃饭），提交时后端直接 400 VALIDATION_ERROR，
 * 于是**答对了也显示"请求失败"**，答案丢掉。
 *
 * 夹住之后的语义仍然合理：elapsed_ms 记录的是"这道题花的时间"，封顶 10 分钟
 * 对 SRS 与统计都没有影响（它不参与盒子计算）；replay_count 封顶 20 次同理。
 */
const MAX_ELAPSED_MS = 600000
const MAX_REPLAY = 20

export const usePracticeStore = defineStore('practice', () => {
  const session = ref(null)
  /** 当前题在 items 里的下标（0 起） */
  const index = ref(0)
  /** 当前题的判题结果；null 表示还没提交 */
  const feedback = ref(null)
  const submitting = ref(false)
  const finishing = ref(false)
  const summary = ref(null)
  const error = ref('')
  /** 建会话时的参数，供"再练一组"原样复用 */
  const config = ref(null)
  /** 每道题的开始时刻，用于算 elapsed_ms */
  const itemStartedAt = ref(0)
  /** 哪些题用过首字母提示：{ [itemId]: true } */
  const hintUsed = ref({})
  /** 每道题重听了几次：{ [itemId]: number } */
  const replayCount = ref({})
  /** 本地累计的首答正确数，供练习过程中顶部实时显示 */
  const localFirstTry = ref(0)
  /** 已经计入 localFirstTry 的题，防止重复提交同一题重复计数 */
  const countedItems = ref({})

  const items = computed(() => session.value?.items || [])
  const currentItem = computed(() => items.value[index.value] || null)
  const total = computed(() => items.value.length)
  const position = computed(() => (total.value ? index.value + 1 : 0))
  const isAnswered = computed(() => feedback.value !== null)
  const isLast = computed(() => index.value >= total.value - 1)
  const isActive = computed(() => session.value?.status === 'active')
  const percent = computed(() =>
    total.value ? Math.round(((index.value + (isAnswered.value ? 1 : 0)) / total.value) * 100) : 0,
  )

  /** 练习中实时显示的首答正确数（本地累计，不等收尾） */
  const firstTryCorrectCount = computed(() => localFirstTry.value)

  /** 会话剩余毫秒。用于顶部"快过期了"的提示 */
  const msLeft = computed(() => {
    if (!session.value?.expires_at) return Infinity
    return new Date(session.value.expires_at).getTime() - Date.now()
  })

  const willExpireSoon = computed(() => msLeft.value < EXPIRE_WARN_MS)

  function markHintUsed() {
    const item = currentItem.value
    if (!item) return
    hintUsed.value = { ...hintUsed.value, [item.item_id]: true }
  }

  function markReplay() {
    const item = currentItem.value
    if (!item) return
    const key = item.item_id
    replayCount.value = { ...replayCount.value, [key]: (replayCount.value[key] || 0) + 1 }
  }

  /**
   * 建会话并开始。
   *
   * @param {Object} options 与 POST /practice/sessions 的 body 同构
   * @returns {Promise<{ok: boolean, warnings?: Array}>}
   */
  async function startSession(options) {
    submitting.value = true
    error.value = ''
    feedback.value = null
    summary.value = null
    index.value = 0
    hintUsed.value = {}
    replayCount.value = {}
    localFirstTry.value = 0
    countedItems.value = {}

    try {
      const data = await createSession(options)
      session.value = data
      config.value = { ...options }
      itemStartedAt.value = Date.now()
      return { ok: true, warnings: data.warnings || [] }
    } catch (err) {
      const normalized = errorOf(err)
      error.value = normalized.message
      session.value = null
      return { ok: false, error: normalized }
    } finally {
      submitting.value = false
    }
  }

  /**
   * 提交当前题（或指定题）的答案。
   *
   * 注意：判错也是 200 + correct:false，所以不能靠 try/catch 判断对错，
   * 必须读 feedback.correct。
   *
   * @param {string} answer
   * @param {number} [itemId] 不传则用当前题
   */
  async function submit(answer, itemId) {
    const target = itemId ?? currentItem.value?.item_id
    if (!target || submitting.value) return null

    submitting.value = true
    error.value = ''

    try {
      const data = await submitAnswer(session.value.session_id, {
        item_id: target,
        answer,
        hint_used: Boolean(hintUsed.value[target]),
        replay_count: Math.min(replayCount.value[target] || 0, MAX_REPLAY),
        elapsed_ms: Math.min(Date.now() - itemStartedAt.value, MAX_ELAPSED_MS),
      })
      feedback.value = data

      // 首答正确才计数。用 countedItems 挡住"重复提交同一题"，
      // 否则同一题提交两次会把首答分算成 2。
      if (data?.first_try_correct && !countedItems.value[target]) {
        countedItems.value = { ...countedItems.value, [target]: true }
        localFirstTry.value += 1
      }
      return data
    } catch (err) {
      const normalized = errorOf(err)
      error.value = normalized.message

      // 会话已结束/已过期：把本地状态同步成终态，
      // 否则界面会停在"可以继续答题"的样子，用户点提交一直报错
      if (normalized.code === 'SESSION_EXPIRED' || normalized.code === 'SESSION_FINISHED') {
        if (session.value) {
          session.value.status = normalized.code === 'SESSION_EXPIRED' ? 'expired' : 'finished'
        }
      }
      return null
    } finally {
      submitting.value = false
    }
  }

  /** 进入下一题。最后一题之后调用 finish()。 */
  function next() {
    if (!isAnswered.value) return
    if (isLast.value) return
    index.value += 1
    feedback.value = null
    itemStartedAt.value = Date.now()
  }

  /** 结束会话，拿汇总。幂等：重复调用返回一致结果。 */
  async function finish() {
    if (!session.value || finishing.value) return summary.value

    finishing.value = true
    try {
      summary.value = await finishSession(session.value.session_id)
      session.value.status = 'finished'
      return summary.value
    } catch (err) {
      error.value = errorOf(err).message
      return null
    } finally {
      finishing.value = false
    }
  }

  /** 清空本地会话（离开结果页、重新开始前调用） */
  function reset() {
    session.value = null
    index.value = 0
    feedback.value = null
    summary.value = null
    error.value = ''
    hintUsed.value = {}
    replayCount.value = {}
    localFirstTry.value = 0
    countedItems.value = {}
    itemStartedAt.value = 0
  }

  /** 用上一次的参数再开一组（结果页的"再练一组"） */
  function restart() {
    const previous = config.value
    reset()
    if (previous) return startSession(previous)
    return Promise.resolve({ ok: false })
  }

  return {
    session,
    index,
    feedback,
    submitting,
    finishing,
    summary,
    error,
    config,
    hintUsed,
    replayCount,
    items,
    currentItem,
    total,
    position,
    isAnswered,
    isLast,
    isActive,
    percent,
    firstTryCorrectCount,
    msLeft,
    willExpireSoon,
    markHintUsed,
    markReplay,
    startSession,
    submit,
    next,
    finish,
    reset,
    restart,
  }
})
