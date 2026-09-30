import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as wrongWordsApi from '@/api/wrongWords'

const PAGE_SIZE = 50

export const useWrongWordsStore = defineStore('wrongWords', () => {
  const items = ref<wrongWordsApi.WrongWordItem[]>([])
  const total = ref(0)
  const page = ref(0)
  const loading = ref(false)

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
      const response = await wrongWordsApi.fetchWrongWords(page.value + 1, PAGE_SIZE)
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

  function reset() {
    items.value = []
    total.value = 0
    page.value = 0
    loading.value = false
  }

  return { items, total, page, loading, isEmpty, hasMore, load, loadMore, reset }
})
