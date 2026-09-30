<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchHomeSummary, type HomeSummary } from '@/api/home'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const summary = ref<HomeSummary | null>(null)
const loading = ref(false)

const percent = computed(() => {
  if (!summary.value || summary.value.today.total_count === 0) return 0
  return Math.round(
    (summary.value.today.viewed_count / summary.value.today.total_count) * 100,
  )
})

onMounted(async () => {
  loading.value = true
  try {
    if (!auth.user) await auth.loadMe()
    summary.value = await fetchHomeSummary()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-gray-900">
        你好，{{ summary?.user.nickname ?? auth.user?.nickname ?? '' }}
      </h2>
      <p class="text-sm text-gray-500">今日的学习进度与目标一览</p>
    </header>

    <section v-if="loading" class="card text-gray-500">加载中…</section>

    <template v-else-if="summary">
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="card">
          <p class="text-sm text-gray-500">今日进度</p>
          <p class="text-2xl font-semibold">
            {{ summary.today.viewed_count }} / {{ summary.today.total_count }}
          </p>
          <div class="mt-2 h-2 w-full rounded-full bg-gray-100">
            <div
              class="h-2 rounded-full bg-brand-500"
              :style="{ width: `${percent}%` }"
            />
          </div>
        </div>

        <div class="card">
          <p class="text-sm text-gray-500">每日目标</p>
          <p class="text-2xl font-semibold">{{ summary.daily_goal }} 词</p>
          <router-link class="text-sm text-brand-600 underline" to="/settings">
            调整目标
          </router-link>
        </div>

        <div class="card">
          <p class="text-sm text-gray-500">待复习错题</p>
          <p class="text-2xl font-semibold">{{ summary.wrong_word_count }}</p>
          <router-link class="text-sm text-brand-600 underline" to="/wrong-words">
            查看错题本
          </router-link>
        </div>

        <div class="card">
          <p class="text-sm text-gray-500">错题库（永久）</p>
          <p class="text-2xl font-semibold">{{ summary.archive_word_count ?? 0 }}</p>
          <router-link class="text-sm text-brand-600 underline" to="/wrong-words">
            查看错题库
          </router-link>
        </div>
      </div>

      <!-- 轮次区（003）：字段缺失时不渲染，页面其余部分照常显示 -->
      <section v-if="summary.current_round" class="card flex flex-col gap-1">
        <p class="text-sm text-gray-500">词库学习轮次</p>
        <p class="text-2xl font-semibold">
          已完成 {{ summary.completed_rounds ?? 0 }} 轮 · 当前第
          {{ summary.current_round.round_no }} 轮
        </p>
        <p class="text-sm text-gray-500">
          本轮已学 {{ summary.current_round.learned_count }} /
          {{ summary.current_round.total_count }}
        </p>
        <p class="text-xl font-bold text-brand-600">
          建议初中会考前每天坚持学习，至少完成 10 轮
        </p>
        <p v-if="summary.current_round.pending_quiz" class="text-sm text-amber-600">
          本轮单词已学完，完成今日测验即可计入第
          {{ summary.current_round.round_no }} 轮
        </p>
      </section>

      <div class="flex flex-wrap gap-3">
        <router-link class="btn-primary" to="/study">进入今日学习</router-link>
        <button
          v-if="summary.today.quiz_unlocked"
          class="btn-primary"
          type="button"
          @click="$router.push('/quiz')"
        >
          开始今日测验
        </button>
        <button v-else class="btn-primary" type="button" disabled>
          测验未解锁（请先完成今日全部单词浏览）
        </button>
      </div>
    </template>
  </div>
</template>
