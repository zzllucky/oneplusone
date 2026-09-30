import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as wrongWordsApi from '@/api/wrongWords'

const PAGE_SIZE = 50

/** 错题库（永久档案）：只累计错误次数，永不移除。 */
export const useWrongWordArchiveStore = defineStore('wrongWordArchive', () => {
  const items = ref<wrongWordsApi.WrongArchiveItem[]>([])
  const total = ref(0)
  const page = ref(0)
  const loading = ref(false)
  const sort = ref<wrongWordsApi.ArchiveSort>('added')

  const isEmpty = computed(() => total.value === 0)
  const hasMore = computed(() => items.value.length < total.value)

  async function load() {
    items.value = []
    total.value = 0
    page.value = 0
    await loadMore()
  }

  async function loadMore() {
    if (loading.value || (page.value > 0 && !hasMore.value)) return
    loading.value = true
    try {
      const response = await wrongWordsApi.fetchWrongWordArchive(
        page.value + 1,
        PAGE_SIZE,
        sort.value,
      )
      const known = new Set(items.value.map((item) => item.word_id))
      items.value.push(
        ...response.items.filter((item) => !known.has(item.word_id)),
      )
      total.value = response.total
      page.value += 1
    } finally {
      loading.value = false
    }
  }

  async function setSort(next: wrongWordsApi.ArchiveSort) {
    if (sort.value === next) return
    sort.value = next
    await load()
  }

  function reset() {
    items.value = []
    total.value = 0
    page.value = 0
    loading.value = false
    sort.value = 'added'
  }

  return {
    items,
    total,
    page,
    loading,
    sort,
    isEmpty,
    hasMore,
    load,
    loadMore,
    setSort,
    reset,
  }
})
