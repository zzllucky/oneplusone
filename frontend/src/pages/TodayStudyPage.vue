<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WordCard from '@/components/WordCard.vue'
import { prefetchPronunciation } from '@/composables/useAudioWarmup'
import { useStudyStore } from '@/stores/study'

const study = useStudyStore()
const router = useRouter()
const index = ref(0)

const current = computed(() => study.items[index.value] ?? null)
const remaining = computed(() => study.totalCount - study.viewedCount)

// 切换单词时预取发音：服务端提前合成并缓存，点发音按钮时不再等待
watch(index, (value) => {
  const spelling = study.items[value]?.spelling
  if (spelling) void prefetchPronunciation(spelling)
})

onMounted(async () => {
  await study.loadToday()
  const firstUnviewed = study.items.findIndex((item) => !item.viewed_at)
  index.value = firstUnviewed >= 0 ? firstUnviewed : 0

  const spelling = study.items[index.value]?.spelling
  if (spelling) void prefetchPronunciation(spelling)
})

async function markViewed(wordId: number) {
  await study.markViewed(wordId)
  const nextUnviewed = study.items.findIndex((item) => !item.viewed_at)
  if (nextUnviewed >= 0) {
    index.value = nextUnviewed
  }
}

function go(delta: number) {
  const next = index.value + delta
  if (next >= 0 && next < study.items.length) index.value = next
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-xl font-bold text-gray-900">今日单词学习</h2>
      <p class="text-sm text-gray-500">
        已浏览 {{ study.viewedCount }} / {{ study.totalCount }}
        <span v-if="study.round">
          · 第 {{ study.round.round_no }} 轮（本轮已学
          {{ study.round.learned_count }} / {{ study.round.total_count }}）
        </span>
        <span v-if="remaining > 0">（还剩 {{ remaining }} 个）</span>
      </p>

      <p v-if="study.round?.pending_quiz" class="card text-sm text-amber-600">
        本轮单词已学完，完成今日测验即可计入第 {{ study.round.round_no }} 轮
      </p>
    </header>

    <p v-if="study.loading" class="card text-gray-500">加载中…</p>

    <template v-else-if="current">
      <WordCard :word="current" @view="markViewed" />

      <div class="flex flex-wrap gap-3">
        <button class="btn-ghost" type="button" :disabled="index === 0" @click="go(-1)">
          上一个
        </button>
        <button
          class="btn-ghost"
          type="button"
          :disabled="index >= study.items.length - 1"
          @click="go(1)"
        >
          下一个
        </button>
        <button
          v-if="study.quizUnlocked"
          class="btn-primary"
          type="button"
          @click="router.push('/quiz')"
        >
          全部浏览完成，去测验
        </button>
        <button v-else class="btn-primary" type="button" disabled>
          测验未解锁：需浏览完全部 {{ study.totalCount }} 个单词
        </button>
      </div>

      <p v-if="study.libraryExhausted" class="text-sm text-gray-500">
        词库中未学习的单词已不足目标数量，本日按剩余数量分配。
      </p>
    </template>

    <p v-else class="card text-gray-500">今日暂无待学习单词。</p>
  </div>
</template>
