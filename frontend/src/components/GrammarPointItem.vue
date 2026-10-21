<script setup lang="ts">
import { computed } from 'vue'
import type { GrammarPointItem } from '@/api/grammar'

const props = defineProps<{ item: GrammarPointItem }>()

const statusText = computed(() => {
  if (props.item.status === 'mastered') return '已掌握'
  if (props.item.status === 'learning') return '学习中'
  return '未学'
})

const statusClass = computed(() => {
  if (props.item.status === 'mastered') return 'bg-green-50 text-green-700'
  if (props.item.status === 'learning') return 'bg-amber-50 text-amber-700'
  return 'bg-gray-100 text-gray-600'
})
</script>

<template>
  <router-link
    :to="`/grammar/${item.id}`"
    class="card flex flex-col gap-2 hover:bg-brand-50"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="font-medium text-gray-900">{{ item.title }}</p>
      <span
        class="shrink-0 rounded-full px-2 py-0.5 text-xs"
        :class="item.depth === '核心' ? 'bg-brand-50 text-brand-600' : 'bg-gray-100 text-gray-600'"
      >
        {{ item.depth }}
      </span>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-xs">
      <span class="rounded-full px-2 py-0.5" :class="statusClass">{{ statusText }}</span>
      <span v-if="item.has_wrong" class="rounded-full bg-red-50 px-2 py-0.5 text-red-600">
        有错题
      </span>
      <span class="text-gray-400">{{ item.question_count }} 道练习题</span>
    </div>
  </router-link>
</template>
