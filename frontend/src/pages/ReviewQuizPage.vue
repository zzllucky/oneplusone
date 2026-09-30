<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import QuizQuestion from '@/components/QuizQuestion.vue'
import QuizResult from '@/components/QuizResult.vue'
import { useWrongWordsStore } from '@/stores/wrongWords'
import * as quizApi from '@/api/quiz'
import { ApiError } from '@/api/client'
import { onCorrect, onWrong, playQuizStart } from '@/sounds/soundEffects'

const wrongWords = useWrongWordsStore()
const router = useRouter()

const questions = ref<quizApi.QuizQuestion[]>([])
const currentIndex = ref(0)
const result = ref<quizApi.ReviewAnswerResponse | null>(null)
const report = ref<quizApi.ReviewFinishResponse | null>(null)
const errorMessage = ref('')
const starting = ref(false)

const current = computed(() => questions.value[currentIndex.value] ?? null)

onMounted(() => wrongWords.load())

async function start() {
  errorMessage.value = ''
  starting.value = true
  try {
    const payload = await quizApi.startReviewQuiz()
    questions.value = payload.questions
    currentIndex.value = 0
    result.value = null
    report.value = null
    playQuizStart()
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '无法开始专项练习'
  } finally {
    starting.value = false
  }
}

async function select(choiceIndex: number) {
  if (!current.value) return
  result.value = await quizApi.answerReview(current.value.question_id, choiceIndex)
  if (result.value.is_correct) onCorrect()
  else onWrong()
}

async function next() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value += 1
    result.value = null
    return
  }
  report.value = await quizApi.finishReviewQuiz()
  await wrongWords.load()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-gray-900">错题专项练习</h2>
      <p class="text-sm text-gray-500">
        题目全部来自错题本；连续答对 2 次才移出，答错则重新计数
      </p>
    </header>

    <section v-if="!questions.length && !report" class="card flex flex-col gap-3">
      <p class="text-gray-700">当前错题 {{ wrongWords.total }} 条</p>
      <button
        class="btn-primary"
        type="button"
        :disabled="wrongWords.isEmpty || starting"
        @click="start"
      >
        {{ wrongWords.isEmpty ? '错题本为空，暂无可练习的单词' : '开始专项练习' }}
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
      <p v-if="result?.removed_from_wrong_words" class="text-sm text-green-600">
        已从错题本移除
      </p>
      <p
        v-else-if="result?.is_correct && (result.correct_streak ?? 0) > 0"
        class="text-sm text-gray-600"
      >
        答对了，再答对 {{ 2 - (result.correct_streak ?? 0) }} 次即可移出错题本
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
      :extra="`剩余错题 ${report.remaining_wrong_count} 条`"
    >
      <div class="flex flex-wrap gap-3">
        <button class="btn-ghost" type="button" @click="router.push('/wrong-words')">
          返回错题本
        </button>
        <button class="btn-primary" type="button" @click="start">再练一轮</button>
      </div>
    </QuizResult>
  </div>
</template>
