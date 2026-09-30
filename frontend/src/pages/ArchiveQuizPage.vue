<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import QuizQuestion from '@/components/QuizQuestion.vue'
import QuizResult from '@/components/QuizResult.vue'
import { useWrongWordArchiveStore } from '@/stores/wrongWordArchive'
import * as quizApi from '@/api/quiz'
import { ApiError } from '@/api/client'

const archive = useWrongWordArchiveStore()
const router = useRouter()

const questions = ref<quizApi.QuizQuestion[]>([])
const currentIndex = ref(0)
const result = ref<quizApi.ArchiveAnswerResponse | null>(null)
const report = ref<quizApi.ArchiveFinishResponse | null>(null)
const errorMessage = ref('')
const starting = ref(false)

const current = computed(() => questions.value[currentIndex.value] ?? null)

onMounted(() => archive.load())

async function start() {
  errorMessage.value = ''
  starting.value = true
  try {
    const payload = await quizApi.startArchiveQuiz()
    questions.value = payload.questions
    currentIndex.value = 0
    result.value = null
    report.value = null
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '无法开始错题库练习'
  } finally {
    starting.value = false
  }
}

async function select(choiceIndex: number) {
  if (!current.value) return
  result.value = await quizApi.answerArchive(current.value.question_id, choiceIndex)
}

async function next() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value += 1
    result.value = null
    return
  }
  report.value = await quizApi.finishArchiveQuiz()
  await archive.load()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-gray-900">错题库专项练习</h2>
      <p class="text-sm text-gray-500">
        题目来自错题库（错误多的优先）；答对不会移除，答错只累加次数
      </p>
    </header>

    <section v-if="!questions.length && !report" class="card flex flex-col gap-3">
      <p class="text-gray-700">错题库共 {{ archive.total }} 条（永久保留）</p>
      <button
        class="btn-primary"
        type="button"
        :disabled="archive.isEmpty || starting"
        @click="start"
      >
        {{ archive.isEmpty ? '错题库为空，暂无可练习的单词' : '开始错题库练习' }}
      </button>
      <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>
    </section>

    <template v-else-if="current && !report">
      <QuizQuestion
        :question="current"
        :index="currentIndex"
        :total="questions.length"
        :result="result"
        @select="select"
      />
      <p v-if="result?.is_correct" class="text-sm text-gray-600">
        答对了，该词仍保留在错题库（累计错 {{ result.archive_wrong_count }} 次）
      </p>
      <p v-else-if="result" class="text-sm text-red-600">
        已记入错题库，累计错 {{ result.archive_wrong_count }} 次
      </p>
      <button v-if="result" class="btn-primary" type="button" @click="next">
        {{ currentIndex < questions.length - 1 ? '下一题' : '查看结果' }}
      </button>
    </template>

    <QuizResult
      v-else-if="report"
      :correct-count="report.correct_count"
      :wrong-count="report.wrong_count"
      :total-count="report.total_count"
      :accuracy="report.accuracy"
      :duration-seconds="report.duration_seconds"
      :extra="`错题库 ${report.archive_total} 条 · 待复习 ${report.remaining_wrong_count} 条`"
    >
      <div class="flex flex-wrap gap-3">
        <button class="btn-ghost" type="button" @click="router.push('/wrong-words')">
          返回错题
        </button>
        <button class="btn-primary" type="button" @click="start">再练一轮</button>
      </div>
    </QuizResult>
  </div>
</template>
