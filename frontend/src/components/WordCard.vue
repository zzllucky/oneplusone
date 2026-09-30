<script setup lang="ts">
import { computed } from 'vue'
import PronounceButton from '@/components/PronounceButton.vue'
import type { StudyWordItem } from '@/api/study'
import { parsePhrases } from '@/utils/phrase'

const props = defineProps<{ word: StudyWordItem }>()
const emit = defineEmits<{ (event: 'view', wordId: number): void }>()

const phrases = computed(() => parsePhrases(props.word.phrase))
</script>

<template>
  <article class="card flex flex-col gap-3">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h2 class="break-all text-2xl font-bold text-gray-900">
        {{ props.word.spelling }}
      </h2>
      <span v-if="props.word.phonetic" class="text-sm text-gray-500">
        {{ props.word.phonetic }}
      </span>
    </div>

    <p class="text-lg text-gray-800">{{ props.word.meaning_zh }}</p>

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

    <div class="flex flex-wrap items-center gap-3">
      <PronounceButton :text="props.word.spelling" label="单词发音" />
      <button
        v-if="!props.word.viewed_at"
        type="button"
        class="btn-primary"
        @click="emit('view', props.word.word_id)"
      >
        标记为已浏览
      </button>
      <span v-else class="text-sm font-medium text-green-600">✓ 已浏览</span>
    </div>
  </article>
</template>
