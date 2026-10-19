<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { QuizQuestion as Question } from '@/api/quiz'

const props = defineProps<{
  question: Question
  index: number
  total: number
  result?: { is_correct: boolean; correct_index: number } | null
  /** 切题后忽略选项点击的窗口长度（毫秒），默认 300，详见 contracts/ui-guard.md §3 */
  lockMs?: number
}>()

const emit = defineEmits<{ (event: 'select', choiceIndex: number): void }>()

// 切题后短暂忽略选项点击，避免连点误选（详见 contracts/ui-guard.md §3）
const DEFAULT_LOCK_MS = 300
const locked = ref(false)
let lockTimer: number | null = null

watch(
  () => [props.question, props.index] as const,
  () => {
    locked.value = true
    if (lockTimer !== null) window.clearTimeout(lockTimer)
    lockTimer = window.setTimeout(() => {
      locked.value = false
      lockTimer = null
    }, props.lockMs ?? DEFAULT_LOCK_MS)
  },
)

onBeforeUnmount(() => {
  if (lockTimer !== null) {
    window.clearTimeout(lockTimer)
    lockTimer = null
  }
})

function onOptionClick(choiceIndex: number) {
  if (locked.value) return
  if (answered.value) return
  emit('select', choiceIndex)
}

const promptLabel = computed(() =>
  props.question.type === 'en2zh' ? '请选择正确的中文释义' : '请选择正确的英文单词',
)

const answered = computed(() => Boolean(props.result))
</script>

<template>
  <section class="card flex flex-col gap-4">
    <header class="flex items-center justify-between text-sm text-gray-500">
      <span>第 {{ props.index + 1 }} / {{ props.total }} 题</span>
      <span>{{ promptLabel }}</span>
    </header>

    <h2 class="break-all text-2xl font-bold text-gray-900">
      {{ props.question.prompt }}
    </h2>

    <div class="flex flex-col gap-2">
      <button
        v-for="(option, optionIndex) in props.question.options"
        :key="optionIndex"
        type="button"
        class="min-h-[44px] rounded-xl border px-4 py-3 text-left transition"
        :class="[
          answered && optionIndex === props.result?.correct_index
            ? 'border-green-500 bg-green-50'
            : '',
          answered &&
          optionIndex !== props.result?.correct_index &&
          props.result?.is_correct === false
            ? 'border-gray-200 bg-white'
            : '',
          !answered ? 'border-gray-300 hover:border-brand-500 hover:bg-brand-50' : '',
        ]"
        :disabled="answered"
        @click="onOptionClick(optionIndex)"
      >
        <span class="mr-2 text-gray-400">{{ String.fromCharCode(65 + optionIndex) }}</span>
        <span class="break-all">{{ option }}</span>
      </button>
    </div>

    <p v-if="answered" class="text-base font-medium">
      <span v-if="props.result?.is_correct" class="text-green-600">回答正确！</span>
      <span v-else class="text-red-600">
        回答错误，正确答案：{{ props.question.options[props.result?.correct_index ?? 0] }}
      </span>
    </p>
  </section>
</template>
