<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GrammarQuestionCard from '@/components/GrammarQuestionCard.vue'
import * as grammarApi from '@/api/grammar'
import type {
  GrammarAnswerResponse,
  GrammarFinishResponse,
  GrammarQuestion,
} from '@/api/grammar'
import { ApiError } from '@/api/client'

const route = useRoute()
const router = useRouter()

const pointId = computed(() => String(route.params.pointId ?? ''))
const title = ref('语法练习')
const questions = ref<GrammarQuestion[]>([])
const attemptId = ref<number | null>(null)
const index = ref(0)
const result = ref<GrammarAnswerResponse | null>(null)
const finished = ref<GrammarFinishResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const ending = ref(false)

const current = computed(() => questions.value[index.value] ?? null)
const progressText = computed(() => `${index.value + 1} / ${questions.value.length}`)
const isLast = computed(() => index.value + 1 >= questions.value.length)

async function loadPoint() {
  try {
    const data = await grammarApi.getPoint(pointId.value)
    title.value = data.point.title
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '加载知识点失败'
  }
}

async function start() {
  loading.value = true
  error.value = null
  try {
    const started = await grammarApi.startPractice(pointId.value)
    attemptId.value = started.attempt_id
    questions.value = started.questions
    index.value = 0
    result.value = null
    finished.value = null
    ending.value = false
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '发起练习失败'
  } finally {
    loading.value = false
  }
}

async function answer(choiceKey: string) {
  if (attemptId.value === null || !current.value) return
  try {
    result.value = await grammarApi.answerGrammarQuestion(
      attemptId.value,
      current.value.question_id,
      choiceKey,
    )
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '判分失败'
  }
}

async function next() {
  if (!isLast.value) {
    index.value += 1
    result.value = null
    return
  }
  await finish()
}

async function finish() {
  if (attemptId.value === null) return
  try {
    finished.value = await grammarApi.finishGrammarAttempt(attemptId.value)
    ending.value = false
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '结算失败'
  }
}

onMounted(async () => {
  await loadPoint()
  await start()
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h2 class="text-xl font-bold text-gray-900">{{ title }}</h2>
        <p class="text-sm text-gray-500">题库练习 · L1 识别 → L2 变形 → L3 陷阱</p>
      </div>
      <button class="btn-ghost" type="button" @click="router.push('/grammar')">
        返回大纲
      </button>
    </header>

    <p v-if="loading" class="card text-gray-500">加载中…</p>

    <div v-else-if="error && !current" class="card flex flex-col gap-2">
      <p class="text-sm text-red-600">{{ error }}</p>
      <div class="flex gap-2">
        <button class="btn-ghost" type="button" @click="start()">重试</button>
        <button class="btn-ghost" type="button" @click="router.push('/grammar')">
          返回大纲
        </button>
      </div>
    </div>

    <!-- 结算面板 -->
    <section v-else-if="finished" class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-500">本轮结果</h3>
      <div class="card flex flex-col gap-1 text-sm">
        <p class="text-gray-800">
          共 {{ finished.total_count }} 题 · 答对 {{ finished.correct_count }} · 答错
          {{ finished.wrong_count }}
        </p>
        <p class="text-gray-700">正确率 {{ Math.round(finished.accuracy * 100) }}%</p>
        <p class="text-gray-500">用时 {{ finished.duration_seconds }} 秒</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" type="button" @click="start()">再练一轮</button>
        <button class="btn-ghost" type="button" @click="router.push('/grammar')">
          返回大纲
        </button>
      </div>
    </section>

    <!-- 答题中 -->
    <template v-else-if="current">
      <p class="text-sm text-gray-500">第 {{ progressText }} 题</p>
      <GrammarQuestionCard :question="current" :result="result" @select="answer" />

      <div class="flex flex-wrap gap-2">
        <button v-if="result" class="btn-primary" type="button" @click="next()">
          {{ isLast ? '查看结果' : '下一题' }}
        </button>

        <button v-if="!ending" class="btn-ghost" type="button" @click="ending = true">
          结束本轮
        </button>
        <template v-else>
          <button class="btn-ghost" type="button" @click="finish()">确认结束</button>
          <button class="btn-ghost" type="button" @click="ending = false">继续练习</button>
        </template>
      </div>

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </template>
  </div>
</template>
