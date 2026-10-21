<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GrammarQuestionCard from '@/components/GrammarQuestionCard.vue'
import * as grammarApi from '@/api/grammar'
import type {
  GrammarAnswerResponse,
  GrammarFinishResponse,
  GrammarPointDetailResponse,
} from '@/api/grammar'
import { ApiError } from '@/api/client'

type Stage = 'guess' | 'explain' | 'check' | 'result'

interface GuessBlock {
  examples?: { en: string; zh: string }[]
  question?: string
  options?: { key: string; text: string }[]
}

interface Anchor {
  en: string
  zh: string
  note?: string
}

interface RuleBlock {
  rule?: string
  signals?: string[]
  formula?: string
  anchors?: Anchor[]
  trap?: { wrong: string; right: string; why: string }
}

interface ContrastSide {
  label?: string
  formula?: string
  anchor?: Anchor
  focus?: string
}

interface ContrastBlock {
  left?: ContrastSide
  right?: ContrastSide
  diff?: string
  traps?: { wrong: string; right: string; why: string }[]
}

interface MemorizeGroup {
  pattern?: string
  tip?: string
  items?: { base: string; past: string; participle: string; zh: string }[]
  anchor?: Anchor
}

const route = useRoute()
const router = useRouter()

const pointId = computed(() => String(route.params.pointId ?? ''))
const data = ref<GrammarPointDetailResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const stage = ref<Stage>('guess')
const guessChoice = ref<string | null>(null)
const guessFeedback = ref<string | null>(null)
const guessError = ref<string | null>(null)

const attemptId = ref<number | null>(null)
const questionIndex = ref(0)
const answerResult = ref<GrammarAnswerResponse | null>(null)
const finishResult = ref<GrammarFinishResponse | null>(null)

const payload = computed(() => (data.value?.payload ?? {}) as Record<string, unknown>)
const guess = computed(() => (payload.value.guess ?? {}) as GuessBlock)
const rule = computed(() => (payload.value.rule ?? {}) as RuleBlock)
const contrast = computed(() => (payload.value.contrast ?? {}) as ContrastBlock)
const groups = computed(() => (payload.value.groups ?? []) as MemorizeGroup[])
const checkQuestions = computed(() => data.value?.check_questions ?? [])
const currentQuestion = computed(() => checkQuestions.value[questionIndex.value] ?? null)
const cardType = computed(() => data.value?.point.card_type ?? 'rule')
const hasCheck = computed(() => checkQuestions.value.length > 0)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await grammarApi.getPoint(pointId.value)
    await grammarApi.viewPoint(pointId.value)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '加载学卡失败'
  } finally {
    loading.value = false
  }
}

async function chooseGuess(key: string) {
  guessChoice.value = key
  guessFeedback.value = null
  guessError.value = null
  try {
    const result = await grammarApi.guessPoint(pointId.value, key)
    guessFeedback.value = result.feedback
  } catch (err) {
    guessError.value = err instanceof ApiError ? err.message : '获取反馈失败'
  }
}

function goExplain() {
  stage.value = 'explain'
}

async function startCheck() {
  if (!hasCheck.value) {
    stage.value = 'result'
    return
  }
  try {
    const started = await grammarApi.startCheck(pointId.value)
    attemptId.value = started.attempt_id
    questionIndex.value = 0
    answerResult.value = null
    stage.value = 'check'
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '开始检测失败'
  }
}

async function answer(choiceKey: string) {
  if (attemptId.value === null || !currentQuestion.value) return
  try {
    answerResult.value = await grammarApi.answerGrammarQuestion(
      attemptId.value,
      currentQuestion.value.question_id,
      choiceKey,
    )
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '判分失败'
  }
}

async function nextQuestion() {
  if (questionIndex.value + 1 < checkQuestions.value.length) {
    questionIndex.value += 1
    answerResult.value = null
    return
  }
  await finish()
}

async function finish() {
  if (attemptId.value === null) return
  try {
    finishResult.value = await grammarApi.finishGrammarAttempt(attemptId.value)
    stage.value = 'result'
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '结算失败'
  }
}

function backToOutline() {
  router.push('/grammar')
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h2 class="text-xl font-bold text-gray-900">{{ data?.point.title ?? '语法学卡' }}</h2>
        <p class="text-sm text-gray-500">
          {{ data?.point.module }}. {{ data?.point.module_name }} ·
          {{ data?.point.depth }}
        </p>
      </div>
      <button class="btn-ghost" type="button" @click="backToOutline()">返回大纲</button>
    </header>

    <p v-if="loading" class="card text-gray-500">加载中…</p>

    <div v-else-if="error" class="card flex flex-col gap-2">
      <p class="text-sm text-red-600">{{ error }}</p>
      <button class="btn-ghost" type="button" @click="load()">重试</button>
    </div>

    <!-- ① 猜一猜 -->
    <section v-else-if="stage === 'guess'" class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-500">① 猜一猜</h3>
      <div v-if="guess.examples?.length" class="card flex flex-col gap-2">
        <p v-for="(item, index) in guess.examples" :key="index" class="text-sm">
          <span class="text-gray-900">{{ item.en }}</span>
          <span class="text-gray-500"> {{ item.zh }}</span>
        </p>
      </div>
      <p class="card font-medium text-gray-900">{{ guess.question }}</p>

      <div class="flex flex-col gap-2">
        <button
          v-for="option in guess.options ?? []"
          :key="option.key"
          type="button"
          class="rounded-xl border border-gray-200 px-3 py-3 text-left"
          :class="guessChoice === option.key ? 'bg-brand-50 text-brand-600' : 'bg-white'"
          @click="chooseGuess(option.key)"
        >
          {{ option.key }}. {{ option.text }}
        </button>
      </div>

      <p v-if="guessFeedback" class="card text-sm text-gray-700">{{ guessFeedback }}</p>
      <p v-if="guessError" class="card text-sm text-red-600">{{ guessError }}</p>

      <button class="btn-primary" type="button" @click="goExplain()">看讲解</button>
    </section>

    <!-- ② 讲解 -->
    <section v-else-if="stage === 'explain'" class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-500">② 讲解</h3>

      <div v-if="cardType === 'rule'" class="flex flex-col gap-3">
        <p class="card text-gray-900">{{ rule.rule }}</p>
        <div v-if="rule.signals?.length" class="card flex flex-wrap gap-2">
          <span
            v-for="signal in rule.signals"
            :key="signal"
            class="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-600"
          >
            {{ signal }}
          </span>
        </div>
        <p v-if="rule.formula" class="card whitespace-pre-line text-sm text-gray-800">
          {{ rule.formula }}
        </p>
        <div v-if="rule.anchors?.length" class="card flex flex-col gap-2">
          <p v-for="(anchor, index) in rule.anchors" :key="index" class="text-sm">
            <span class="text-gray-900">{{ anchor.en }}</span>
            <span class="text-gray-500"> {{ anchor.zh }}</span>
            <span v-if="anchor.note" class="text-gray-400">（{{ anchor.note }}）</span>
          </p>
        </div>
        <div v-if="rule.trap" class="card flex flex-col gap-1 text-sm">
          <p class="text-red-600">✗ {{ rule.trap.wrong }}</p>
          <p class="text-green-700">✓ {{ rule.trap.right }}</p>
          <p class="text-gray-500">{{ rule.trap.why }}</p>
        </div>
      </div>

      <div v-else-if="cardType === 'contrast'" class="flex flex-col gap-3">
        <div class="grid gap-3 md:grid-cols-2">
          <div v-if="contrast.left" class="card flex flex-col gap-1 text-sm">
            <p class="font-semibold text-gray-900">{{ contrast.left.label }}</p>
            <p class="text-gray-700">{{ contrast.left.formula }}</p>
            <p class="text-gray-500">{{ contrast.left.focus }}</p>
            <p v-if="contrast.left.anchor" class="text-gray-500">
              {{ contrast.left.anchor.en }} {{ contrast.left.anchor.zh }}
            </p>
          </div>
          <div v-if="contrast.right" class="card flex flex-col gap-1 text-sm">
            <p class="font-semibold text-gray-900">{{ contrast.right.label }}</p>
            <p class="text-gray-700">{{ contrast.right.formula }}</p>
            <p class="text-gray-500">{{ contrast.right.focus }}</p>
            <p v-if="contrast.right.anchor" class="text-gray-500">
              {{ contrast.right.anchor.en }} {{ contrast.right.anchor.zh }}
            </p>
          </div>
        </div>
        <p v-if="contrast.diff" class="card text-sm text-gray-800">{{ contrast.diff }}</p>
        <div v-if="contrast.traps?.length" class="card flex flex-col gap-2 text-sm">
          <div v-for="(trap, index) in contrast.traps" :key="index">
            <p class="text-red-600">✗ {{ trap.wrong }}</p>
            <p class="text-green-700">✓ {{ trap.right }}</p>
            <p class="text-gray-500">{{ trap.why }}</p>
          </div>
        </div>
      </div>

      <div v-else class="flex flex-col gap-3">
        <div v-for="(group, index) in groups" :key="index" class="card flex flex-col gap-2">
          <p class="font-semibold text-gray-900">{{ group.pattern }}</p>
          <p class="text-sm text-gray-600">{{ group.tip }}</p>
          <div v-if="group.items?.length" class="flex flex-col gap-1 text-sm">
            <p v-for="(item, itemIndex) in group.items" :key="itemIndex" class="text-gray-800">
              {{ item.base }} → {{ item.past }} → {{ item.participle }}（{{ item.zh }}）
            </p>
          </div>
          <p v-if="group.anchor" class="text-sm text-gray-500">
            {{ group.anchor.en }} {{ group.anchor.zh }}
          </p>
        </div>
      </div>

      <button class="btn-primary" type="button" @click="startCheck()">
        {{ hasCheck ? '做学后检测' : '完成学习' }}
      </button>
    </section>

    <!-- ③ 学后检测 -->
    <section v-else-if="stage === 'check'" class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-500">
        ③ 学后检测（{{ questionIndex + 1 }} / {{ checkQuestions.length }}）
      </h3>

      <GrammarQuestionCard
        v-if="currentQuestion"
        :question="currentQuestion"
        :result="answerResult"
        @select="answer"
      />

      <button
        v-if="answerResult"
        class="btn-primary"
        type="button"
        @click="nextQuestion()"
      >
        {{ questionIndex + 1 < checkQuestions.length ? '下一题' : '查看结果' }}
      </button>
    </section>

    <!-- 结果 -->
    <section v-else class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-500">本轮结果</h3>

      <div v-if="finishResult" class="card flex flex-col gap-1 text-sm">
        <p class="text-gray-800">
          共 {{ finishResult.total_count }} 题 · 答对 {{ finishResult.correct_count }} ·
          正确率 {{ Math.round(finishResult.accuracy * 100) }}%
        </p>
        <p class="text-gray-500">用时 {{ finishResult.duration_seconds }} 秒</p>
        <p :class="finishResult.mastered ? 'text-green-700' : 'text-amber-700'">
          {{ finishResult.mastered ? '全部答对，已掌握！' : '还有错题，状态保持学习中' }}
        </p>
      </div>

      <p v-else class="card text-sm text-gray-600">本卡为速记内容，浏览即完成学习。</p>

      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" type="button" @click="backToOutline()">返回大纲</button>
        <router-link
          v-if="data && data.point.id"
          class="btn-ghost"
          :to="`/grammar/${data.point.id}/practice`"
        >
          去练习
        </router-link>
      </div>
    </section>
  </div>
</template>
