<script setup lang="ts">
import { computed } from 'vue'
import PronounceButton from '@/components/PronounceButton.vue'
import type { WrongWordItem as Item } from '@/api/wrongWords'
import { parsePhrases } from '@/utils/phrase'

const props = defineProps<{ item: Item }>()

const phrases = computed(() => parsePhrases(props.item.phrase))

const addedAtText = computed(() => {
  const date = new Date(props.item.added_at)
  if (Number.isNaN(date.getTime())) return props.item.added_at
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
})
</script>

<template>
  <article class="card flex flex-col gap-2">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h3 class="break-all text-lg font-semibold text-gray-900">
        {{ props.item.spelling }}
      </h3>
      <span class="text-xs text-gray-500">加入时间：{{ addedAtText }}</span>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-xs">
      <span class="rounded-full bg-red-50 px-2 py-1 text-red-600">
        累计错 {{ props.item.wrong_count ?? 1 }} 次
      </span>
      <span
        v-if="(props.item.correct_streak ?? 0) > 0"
        class="rounded-full bg-green-50 px-2 py-1 text-green-700"
      >
        已连续答对 {{ props.item.correct_streak }} / 2，再答对
        {{ 2 - props.item.correct_streak }} 次移出
      </span>
    </div>
    <p class="text-gray-800">{{ props.item.meaning_zh }}</p>

    <ul v-if="phrases.length" class="flex flex-col gap-1">
      <li
        v-for="(phrase, index) in phrases"
        :key="index"
        class="flex flex-wrap items-center gap-2 text-sm text-gray-600"
      >
        <span>{{ phrase.english }}</span>
        <span v-if="phrase.chinese" class="text-gray-500">{{ phrase.chinese }}</span>
        <PronounceButton
          v-if="phrase.english"
          :text="phrase.english"
          label="例句发音"
          small
        />
      </li>
    </ul>

    <PronounceButton :text="props.item.spelling" label="单词发音" />
  </article>
</template>
