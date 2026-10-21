import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as grammarApi from '@/api/grammar'
import { ApiError } from '@/api/client'

export const useGrammarStore = defineStore('grammar', () => {
  const outline = ref<grammarApi.GrammarOutlineResponse | null>(null)
  const wrongPoints = ref<grammarApi.GrammarWrongPointItem[]>([])
  const wrongTotal = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const modules = computed(() => outline.value?.modules ?? [])
  const totalPoints = computed(() => outline.value?.total_points ?? 0)
  const masteredCount = computed(() => outline.value?.mastered_count ?? 0)
  const wrongCount = computed(() => outline.value?.wrong_count ?? 0)
  const isEmpty = computed(() => totalPoints.value === 0)

  /** 只看错题筛选视图：大纲中仍有错题的知识点 */
  const wrongPointIds = computed(
    () =>
      new Set(
        modules.value
          .flatMap((module) => module.points)
          .filter((point) => point.has_wrong)
          .map((point) => point.id),
      ),
  )

  async function loadOutline() {
    loading.value = true
    error.value = null
    try {
      outline.value = await grammarApi.getOutline()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '加载语法大纲失败'
    } finally {
      loading.value = false
    }
  }

  async function loadWrongPoints() {
    try {
      const data = await grammarApi.getWrongPoints()
      wrongPoints.value = data.items
      wrongTotal.value = data.total
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '加载语法错题本失败'
    }
  }

  function reset() {
    outline.value = null
    wrongPoints.value = []
    wrongTotal.value = 0
    error.value = null
  }

  return {
    outline,
    wrongPoints,
    wrongTotal,
    loading,
    error,
    modules,
    totalPoints,
    masteredCount,
    wrongCount,
    isEmpty,
    wrongPointIds,
    loadOutline,
    loadWrongPoints,
    reset,
  }
})
