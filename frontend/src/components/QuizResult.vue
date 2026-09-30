<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  correctCount: number
  wrongCount: number
  totalCount: number
  accuracy: number
  durationSeconds: number
  extra?: string
}>()

const percent = computed(() => Math.round(props.accuracy * 100))
</script>

<template>
  <section class="card flex flex-col gap-3">
    <h2 class="text-xl font-bold text-gray-900">练习报告</h2>
    <div class="grid grid-cols-2 gap-3 text-gray-700 sm:grid-cols-4">
      <div class="rounded-xl bg-gray-50 p-3">
        <p class="text-xs text-gray-500">题目数</p>
        <p class="text-xl font-semibold">{{ props.totalCount }}</p>
      </div>
      <div class="rounded-xl bg-gray-50 p-3">
        <p class="text-xs text-gray-500">答对</p>
        <p class="text-xl font-semibold text-green-600">{{ props.correctCount }}</p>
      </div>
      <div class="rounded-xl bg-gray-50 p-3">
        <p class="text-xs text-gray-500">答错</p>
        <p class="text-xl font-semibold text-red-600">{{ props.wrongCount }}</p>
      </div>
      <div class="rounded-xl bg-gray-50 p-3">
        <p class="text-xs text-gray-500">正确率</p>
        <p class="text-xl font-semibold">{{ percent }}%</p>
      </div>
    </div>
    <p class="text-sm text-gray-500">用时 {{ props.durationSeconds }} 秒</p>
    <p v-if="props.extra" class="text-sm text-gray-600">{{ props.extra }}</p>
    <slot />
  </section>
</template>
