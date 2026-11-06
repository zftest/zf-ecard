import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { errorOf } from '@/api/client'
import { getThemes, getUnits, listWords } from '@/api/words'

/**
 * 词库 store：单元/主题字典 + 单词列表的筛选与分页。
 */

const SEARCH_DEBOUNCE_MS = 250

export const useCatalogStore = defineStore('catalog', () => {
  const units = ref([])
  const themes = ref([])
  const words = ref([])
  const pagination = ref({ page: 1, page_size: 20, total: 0, total_pages: 0 })

  const loading = ref(false)
  const loadingCatalog = ref(false)
  const error = ref('')

  const filters = reactive({
    q: '',
    unit: null,
    theme: null,
    pos: [],
    status: [],
    /** status 的口径按哪个技能算。改这个会让列表的"掌握状态"整体变一次 */
    skill: 'zh_to_en',
    sort: 'unit',
  })

  /*
   * 请求序号：解决"输入框里快速打字，先发的慢请求后到，把新结果覆盖掉"。
   * 没有这个守卫，搜 "en" 的结果可能盖住搜 "environment" 的结果，
   * 表现为"搜索框里写着 environment，列表却是 en 的结果"。
   */
  let requestSeq = 0
  let debounceTimer = null

  const activeFilterCount = computed(() => {
    let count = 0
    if (filters.q) count += 1
    if (filters.unit) count += 1
    if (filters.theme) count += 1
    count += filters.pos.length
    count += filters.status.length
    return count
  })

  const hasActiveFilters = computed(() => activeFilterCount.value > 0)

  /** 单元/主题字典。进页面拉一次即可，不需要跟着筛选变。 */
  async function loadCatalog() {
    if (loadingCatalog.value) return
    loadingCatalog.value = true
    try {
      const [unitData, themeData] = await Promise.all([getUnits(), getThemes()])
      units.value = unitData.items || []
      themes.value = themeData.items || []
    } catch (err) {
      error.value = errorOf(err).message
    } finally {
      loadingCatalog.value = false
    }
  }

  async function loadWords({ page } = {}) {
    const mySeq = (requestSeq += 1)
    loading.value = true
    error.value = ''

    try {
      const data = await listWords({
        q: filters.q,
        unit: filters.unit,
        theme: filters.theme,
        pos: filters.pos,
        status: filters.status,
        skill: filters.skill,
        sort: filters.sort,
        page: page ?? pagination.value.page,
        page_size: pagination.value.page_size,
      })

      // 有更新的请求发出去了，这次的结果已经过期，直接丢弃
      if (mySeq !== requestSeq) return

      words.value = data.items || []
      pagination.value = data.pagination || pagination.value
    } catch (err) {
      if (mySeq !== requestSeq) return
      error.value = errorOf(err).message
      words.value = []
    } finally {
      if (mySeq === requestSeq) loading.value = false
    }
  }

  /**
   * 改搜索词（带防抖）。
   *
   * 防抖放在 store 而不是输入框组件里：搜索框可能不止一个
   * （词库页顶部一个、首页跳转过去一个），
   * 每个都写一遍防抖，迟早有一个忘了写，一打字就打出几十个请求。
   */
  function setQuery(value) {
    filters.q = value
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      pagination.value.page = 1
      loadWords({ page: 1 })
    }, SEARCH_DEBOUNCE_MS)
  }

  /** 多选筛选（词性、状态）。同一个值再点一次就取消。 */
  function toggleFilter(key, value) {
    const list = filters[key]
    if (!Array.isArray(list)) return
    const index = list.indexOf(value)
    if (index >= 0) list.splice(index, 1)
    else list.push(value)
    pagination.value.page = 1
    loadWords({ page: 1 })
  }

  /** 单选筛选（单元、主题、排序）。传同一个值视为取消。 */
  function setFilter(key, value) {
    if (key === 'unit' || key === 'theme') {
      filters[key] = filters[key] === value ? null : value
    } else {
      filters[key] = value
    }
    pagination.value.page = 1
    loadWords({ page: 1 })
  }

  function resetFilters() {
    filters.q = ''
    filters.unit = null
    filters.theme = null
    filters.pos.splice(0)
    filters.status.splice(0)
    filters.sort = 'unit'
    pagination.value.page = 1
    loadWords({ page: 1 })
  }

  function goToPage(page) {
    const total = pagination.value.total_pages || 1
    const next = Math.min(Math.max(1, page), total)
    if (next === pagination.value.page) return
    loadWords({ page: next })
  }

  return {
    units,
    themes,
    words,
    pagination,
    loading,
    loadingCatalog,
    error,
    filters,
    activeFilterCount,
    hasActiveFilters,
    loadCatalog,
    loadWords,
    setQuery,
    setFilter,
    toggleFilter,
    resetFilters,
    goToPage,
  }
})
