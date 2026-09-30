<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  getDaySummary,
  getMonthSummary,
  type CalendarDay,
  type DaySummary,
  type MonthSummary,
  type PracticeStat,
} from '@/api/summary'

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']

const loading = ref(false)
const error = ref('')
const month = ref<MonthSummary | null>(null)
const activeMonth = ref('')

const selectedDate = ref<string | null>(null)
const dayDetail = ref<DaySummary | null>(null)
const dayLoading = ref(false)
const dayError = ref('')

const cells = computed(() => {
  if (!month.value || !month.value.days.length) return []
  const [year, monthPart] = month.value.month.split('-').map(Number)
  const firstWeekday = (new Date(year, monthPart - 1, 1).getDay() + 6) % 7 // 周一为第一列
  return [...Array.from({ length: firstWeekday }, () => null), ...month.value.days]
})

const selectedDateText = computed(() => selectedDate.value ?? '')

function shiftMonth(key: string, delta: number): string {
  const [year, monthPart] = key.split('-').map(Number)
  const target = new Date(year, monthPart - 1 + delta, 1)
  return `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, '0')}`
}

function cellClass(day: CalendarDay): string {
  if (day.level === 'light') return 'bg-green-100 text-green-700'
  if (day.level === 'deep') {
    return (
      ['bg-green-300 text-green-900', 'bg-green-500 text-white', 'bg-green-700 text-white'][
        day.shade - 1
      ] ?? 'bg-green-300 text-green-900'
    )
  }
  return 'bg-gray-100 text-gray-400'
}

async function loadMonth(key?: string) {
  loading.value = true
  error.value = ''
  try {
    month.value = await getMonthSummary(key)
    activeMonth.value = month.value.month
    selectedDate.value = null
    dayDetail.value = null
  } catch {
    error.value = '日历加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function selectDay(day: CalendarDay) {
  selectedDate.value = day.date
  dayDetail.value = null
  dayLoading.value = true
  dayError.value = ''
  try {
    dayDetail.value = await getDaySummary(day.date)
  } catch {
    dayError.value = '明细加载失败，请稍后重试'
  } finally {
    dayLoading.value = false
  }
}

function accuracy(stat: PracticeStat): string {
  if (!stat.answered) return '—'
  return `${Math.round((stat.correct / stat.answered) * 100)}%`
}

function practiceText(stat: PracticeStat): string {
  if (!stat.answered) return '未进行'
  return `${stat.rounds} 轮 · 答 ${stat.answered} 题（对 ${stat.correct} / 错 ${stat.wrong}）`
}

onMounted(() => loadMonth())
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-gray-900">学习总结</h2>
      <p class="text-sm text-gray-500">每天的学习情况一眼可见，点击日期看当天明细</p>
    </header>

    <section v-if="loading" class="card text-gray-500">加载中…</section>
    <section v-else-if="error" class="card text-gray-500">{{ error }}</section>

    <template v-else-if="month">
      <!-- 月份切换 -->
      <div class="card flex items-center justify-between">
        <button
          class="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          type="button"
          @click="loadMonth(shiftMonth(activeMonth, -1))"
        >
          上一月
        </button>
        <p class="text-lg font-semibold">{{ activeMonth }}</p>
        <button
          class="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          type="button"
          @click="loadMonth(shiftMonth(activeMonth, 1))"
        >
          下一月
        </button>
      </div>

      <!-- 月历 -->
      <section class="card">
        <div class="mb-2 grid grid-cols-7 gap-1 text-center text-xs text-gray-500">
          <span v-for="label in WEEK_LABELS" :key="label">{{ label }}</span>
        </div>
        <div class="grid grid-cols-7 gap-1">
          <template v-for="(cell, index) in cells" :key="index">
            <span v-if="!cell" class="h-10" />
            <button
              v-else
              class="flex h-10 flex-col items-center justify-center rounded-lg text-xs"
              :class="[
                cellClass(cell),
                cell.date === month.today ? 'ring-2 ring-brand-500' : '',
                cell.date === selectedDate ? 'outline outline-2 outline-brand-600' : '',
              ]"
              type="button"
              @click="selectDay(cell)"
            >
              <span>{{ Number(cell.date.slice(-2)) }}</span>
              <span v-if="cell.learned_count" class="text-[10px]">
                {{ cell.learned_count }}
              </span>
            </button>
          </template>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
          <span class="flex items-center gap-1">
            <i class="h-3 w-3 rounded bg-gray-100" />无记录
          </span>
          <span class="flex items-center gap-1">
            <i class="h-3 w-3 rounded bg-green-100" />打开过
          </span>
          <span class="flex items-center gap-1">
            <i class="h-3 w-3 rounded bg-green-300" />学了一点
          </span>
          <span class="flex items-center gap-1">
            <i class="h-3 w-3 rounded bg-green-500" />学得不错
          </span>
          <span class="flex items-center gap-1">
            <i class="h-3 w-3 rounded bg-green-700" />学得很多
          </span>
        </div>
      </section>

      <!-- 月度汇总与连续天数 -->
      <section class="card flex flex-col gap-2">
        <p class="text-lg font-semibold text-brand-600">
          连续学习 {{ month.streak_days }} 天
        </p>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <p class="text-sm text-gray-500">本月学习词数</p>
            <p class="text-xl font-semibold">{{ month.month_total.learned_words }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">有活动天数</p>
            <p class="text-xl font-semibold">{{ month.month_total.active_days }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">今日测验</p>
            <p class="text-base">
              {{ month.month_total.quiz.answered }} 题 · 对
              {{ month.month_total.quiz.correct }} / 错 {{ month.month_total.quiz.wrong }}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-500">错题本专项</p>
            <p class="text-base">{{ practiceText(month.month_total.review_practice) }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">错题库专项</p>
            <p class="text-base">
              {{ practiceText(month.month_total.archive_practice) }}
            </p>
          </div>
        </div>
      </section>

      <!-- 单日明细 -->
      <section v-if="selectedDate" class="card flex flex-col gap-2">
        <p class="font-semibold">{{ selectedDateText }}</p>

        <p v-if="dayLoading" class="text-gray-500">加载中…</p>
        <p v-else-if="dayError" class="text-gray-500">{{ dayError }}</p>
        <p v-else-if="dayDetail && !dayDetail.has_record" class="text-gray-500">
          当天没有学习记录
        </p>
        <div v-else-if="dayDetail" class="flex flex-col gap-1 text-sm">
          <p>学习单词数：<span class="font-semibold">{{ dayDetail.learned_count }}</span></p>
          <p>
            今日测验：<span class="font-semibold">{{ dayDetail.quiz.completed ? '已完成' : '未进行' }}</span>
            · 对 {{ dayDetail.quiz.correct }} / 错 {{ dayDetail.quiz.wrong }}
            · 正确率 {{ accuracy(dayDetail.quiz) }}
          </p>
          <p>错题本专项：{{ practiceText(dayDetail.review_practice) }}</p>
          <p>错题库专项：{{ practiceText(dayDetail.archive_practice) }}</p>
        </div>
      </section>
    </template>
  </div>
</template>
