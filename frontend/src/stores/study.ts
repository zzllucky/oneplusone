import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as studyApi from '@/api/study'

export const useStudyStore = defineStore('study', () => {
  const today = ref<studyApi.TodayStudyResponse | null>(null)
  const loading = ref(false)

  const items = computed(() => today.value?.items ?? [])
  const totalCount = computed(() => today.value?.total_count ?? 0)
  const viewedCount = computed(() => today.value?.viewed_count ?? 0)
  const quizUnlocked = computed(() => Boolean(today.value?.quiz_unlocked))
  const libraryExhausted = computed(() => Boolean(today.value?.library_exhausted))
  // 轮次信息（003）：缺失 / null 时前端不渲染轮次区
  const round = computed(() => today.value?.round ?? null)

  async function loadToday() {
    loading.value = true
    try {
      today.value = await studyApi.fetchTodayStudy()
    } finally {
      loading.value = false
    }
  }

  async function markViewed(wordId: number) {
    const result = await studyApi.markWordViewed(wordId)
    if (today.value) {
      const item = today.value.items.find((entry) => entry.word_id === wordId)
      if (item && !item.viewed_at) {
        item.viewed_at = new Date().toISOString()
      }
      today.value.viewed_count = result.viewed_count
      today.value.all_viewed = result.all_viewed
      today.value.quiz_unlocked = result.quiz_unlocked
    }
    return result
  }

  function reset() {
    today.value = null
  }

  return {
    today,
    loading,
    items,
    totalCount,
    viewedCount,
    quizUnlocked,
    libraryExhausted,
    round,
    loadToday,
    markViewed,
    reset,
  }
})
