import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { errorOf } from '@/api/client'
import { listWrongbook, updateWrongbookEntry } from '@/api/wrongbook'
import { useLearnerStore } from '@/stores/learner'

/**
 * 错词本 store。
 *
 * 数据形状要特别注意：后端返回的是**扁平行**，一行 = 一个词 × 一个技能。
 * 同一个单词可能有两行（拼写错过、听音也错过），这是刻意的设计，
 * 前端不要按 word_id 去重 —— 去重会把"这个词有两种能力都很弱"这个信息抹掉。
 */

export const useWrongbookStore = defineStore('wrongbook', () => {
  const learner = useLearnerStore()

  const items = ref([])
  const pagination = ref({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const summary = ref({ total: 0, due_today: 0, mastered_this_week: 0 })
  const loading = ref(false)
  const error = ref('')

  const filters = reactive({
    /** 题型名，null 表示全部技能 */
    skill: null,
    sort: 'due',
  })

  /** 每行的唯一键：同一个词在不同技能上是不同的条目 */
  const rowKey = (row) => `${row.word_id}:${row.skill}`

  /** 按技能分组，供页面分块展示（"拼写错了 5 个""听音没听出来 3 个"） */
  const groupedBySkill = computed(() => {
    const groups = new Map()
    for (const row of items.value) {
      if (!groups.has(row.skill)) groups.set(row.skill, [])
      groups.get(row.skill).push(row)
    }
    return [...groups.entries()].map(([skill, rows]) => ({
      skill,
      rows,
      wrongTotal: rows.reduce((sum, row) => sum + row.wrong_count, 0),
    }))
  })

  /** 今天到期的条目（用于"现在复习"主按钮的可用性判断） */
  const dueItems = computed(() => items.value.filter((row) => row.is_due))

  const isEmpty = computed(() => !loading.value && items.value.length === 0)

  async function load({ page, silent = false } = {}) {
    if (!silent) {
      loading.value = true
      error.value = ''
    }

    try {
      const data = await listWrongbook(learner.learnerId, {
        skill: filters.skill,
        sort: filters.sort,
        page: page ?? pagination.value.page,
        page_size: pagination.value.page_size,
      })
      items.value = data.items || []
      pagination.value = data.pagination || pagination.value
      summary.value = data.summary || summary.value
    } catch (err) {
      if (!silent) {
        error.value = errorOf(err).message
        items.value = []
      }
    } finally {
      if (!silent) loading.value = false
    }
  }

  function setSkill(skill) {
    filters.skill = filters.skill === skill ? null : skill
    pagination.value.page = 1
    return load({ page: 1 })
  }

  function setSort(sort) {
    filters.sort = sort
    pagination.value.page = 1
    return load({ page: 1 })
  }

  function goToPage(page) {
    const total = pagination.value.total_pages || 1
    const next = Math.min(Math.max(1, page), total)
    if (next === pagination.value.page) return Promise.resolve()
    return load({ page: next })
  }

  /**
   * 标记已掌握。
   *
   * 先本地移除再后台刷新：用户点完立刻看到那一行消失，
   * 而不是盯着 loading 等一个 RTT。刷新用 silent 模式，不闪 loading。
   * 万一后台刷新失败，本地已经移除的不会自己回来 ——
   * 但下次进页面重新加载就会修正，不会永久错乱。
   */
  async function master(wordId, skill) {
    const key = `${wordId}:${skill}`
    const snapshot = items.value
    items.value = items.value.filter((row) => rowKey(row) !== key)
    summary.value = {
      ...summary.value,
      total: Math.max(0, summary.value.total - 1),
      mastered_this_week: summary.value.mastered_this_week + 1,
    }

    try {
      const result = await updateWrongbookEntry(learner.learnerId, wordId, {
        skill,
        action: 'master',
      })
      // 静默对齐服务端真实数字
      load({ silent: true })
      return result
    } catch (err) {
      // 失败就回滚，不能让列表少一行而后端没变
      items.value = snapshot
      load({ silent: true })
      error.value = errorOf(err).message
      throw err
    }
  }

  /**
   * 重置回第 1 盒（或取消掌握）。
   *
   * 不做乐观更新：重置之后这一行在列表里的位置会变（立刻到期 → 排到最前），
   * 猜位置容易猜错，直接重拉更可靠。
   */
  async function resetEntry(wordId, skill) {
    try {
      const result = await updateWrongbookEntry(learner.learnerId, wordId, {
        skill,
        action: 'reset',
      })
      await load({ silent: true })
      return result
    } catch (err) {
      error.value = errorOf(err).message
      throw err
    }
  }

  function resetFilters() {
    filters.skill = null
    filters.sort = 'due'
    pagination.value.page = 1
    return load({ page: 1 })
  }

  return {
    items,
    pagination,
    summary,
    loading,
    error,
    filters,
    groupedBySkill,
    dueItems,
    isEmpty,
    rowKey,
    load,
    setSkill,
    setSort,
    goToPage,
    master,
    resetEntry,
    resetFilters,
  }
})
