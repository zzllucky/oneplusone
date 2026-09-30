<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import QuizQuestion from '@/components/QuizQuestion.vue'
import QuizResult from '@/components/QuizResult.vue'
import { useStudyStore } from '@/stores/study'
import { useWrongWordsStore } from '@/stores/wrongWords'
import * as quizApi from '@/api/quiz'
import { ApiError } from '@/api/client'
import { onCorrect, onWrong, playQuizStart } from '@/sounds/soundEffects'

const study = useStudyStore()
const wrongWords = useWrongWordsStore()
const router = useRouter()

const questions = ref<quizApi.QuizQuestion[]>([])
const currentIndex = ref(0)
const result = ref<quizApi.DailyAnswerResponse | null>(null)
const report = ref<quizApi.QuizFinishResponse | null>(null)
const errorMessage = ref('')
const starting = ref(false)

const current = computed(() => questions.value[currentIndex.value] ?? null)

onMounted(async () => {
  await study.loadToday()
})

async function start() {
  errorMessage.value = ''
  starting.value = true
  try {
    const payload = await quizApi.startDailyQuiz()
    questions.value = payload.questions
    currentIndex.value = 0
    result.value = null
    report.value = null
    playQuizStart()
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '无法开始测验'
  } finally {
    starting.value = false
  }
}

async function select(choiceIndex: number) {
  if (!current.value) return
  result.value = await quizApi.answerDaily(current.value.question_id, choiceIndex)
  if (result.value.is_correct) onCorrect()
  else onWrong()
}

async function next() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value += 1
    result.value = null
    return
  }
  report.value = await quizApi.finishDailyQuiz()
  await Promise.all([study.loadToday(), wrongWords.load()])
}

async function backHome() {
  router.push('/home')
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-gray-900">今日单词测验</h2>
      <p class="text-sm text-gray-500">
        全部单词浏览完成后才可开启（英译中 / 中译英四选一）
      </p>
    </header>

    <!-- 未解锁：入口不可用 -->
    <section v-if="!questions.length && !report" class="card flex flex-col gap-3">
      <p class="text-gray-700">
        当前进度：{{ study.viewedCount }} / {{ study.totalCount }}
      </p>
      <button class="btn-primary" type="button" :disabled="!study.quizUnlocked || starting" @click="start">
        {{ study.quizUnlocked ? '开始测验' : '测验未解锁（请先完成全部浏览）' }}
      </button>
      <button class="btn-ghost" type="button" @click="$router.push('/study')">
        返回今日学习
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
      :extra="`本轮新增错题 ${report.new_wrong_words.length} 个（答对不会移除错题本已有记录）`"
    >
      <div class="flex flex-wrap gap-3">
        <button class="btn-ghost" type="button" @click="backHome">返回首页</button>
        <router-link class="btn-primary" to="/wrong-words">查看错题本</router-link>
      </div>
    </QuizResult>
  </div>
</template>
