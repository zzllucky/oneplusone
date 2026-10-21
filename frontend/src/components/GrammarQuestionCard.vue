<script setup lang="ts">
import { computed } from 'vue'
import type { GrammarAnswerResponse, GrammarQuestion } from '@/api/grammar'

const props = defineProps<{
  question: GrammarQuestion
  result?: GrammarAnswerResponse | null
}>()

const emit = defineEmits<{ select: [choiceKey: string] }>()

const answered = computed(() => Boolean(props.result))

function select(key: string) {
  if (answered.value) return
  emit('select', key)
}

function optionClass(key: string) {
  const result = props.result
  if (!result) return 'bg-white text-gray-800'
  if (key === result.correct_key) return 'bg-green-50 text-green-700'
  return 'bg-red-50 text-red-700'
}
</script>

<template>
  <section class="card flex flex-col gap-3">
    <header class="flex items-center justify-between gap-2">
      <p class="font-medium text-gray-900">{{ question.stem }}</p>
      <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
        {{ question.level }}
      </span>
    </header>

    <div class="flex flex-col gap-2">
      <button
        v-for="option in question.options"
        :key="option.key"
        type="button"
        class="rounded-xl border border-gray-200 px-3 py-3 text-left"
        :class="optionClass(option.key)"
        :disabled="answered"
        @click="select(option.key)"
      >
        {{ option.key }}. {{ option.text }}
      </button>
    </div>

    <div v-if="result" class="flex flex-col gap-1 rounded-xl bg-gray-50 p-3 text-sm">
      <p :class="result.is_correct ? 'text-green-700' : 'text-red-600'">
        {{ result.is_correct ? '回答正确' : '回答错误' }}
      </p>
      <p class="text-gray-700">正确答案 {{ result.correct_key }}</p>
      <p class="text-gray-700">{{ result.explanation }}</p>
      <p v-if="result.feedback" class="text-gray-500">错因：{{ result.feedback }}</p>
    </div>
  </section>
</template>
