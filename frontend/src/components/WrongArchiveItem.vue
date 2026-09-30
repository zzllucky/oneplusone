<script setup lang="ts">
import { computed } from 'vue'
import PronounceButton from '@/components/PronounceButton.vue'
import type { WrongArchiveItem as Item } from '@/api/wrongWords'
import { parsePhrases } from '@/utils/phrase'

const props = defineProps<{ item: Item }>()

const phrases = computed(() => parsePhrases(props.item.phrase))
</script>

<template>
  <article class="card flex flex-col gap-2">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h3 class="break-all text-lg font-semibold text-gray-900">
        {{ props.item.spelling }}
      </h3>
      <span class="rounded-full bg-red-50 px-2 py-1 text-xs text-red-600">
        累计错 {{ props.item.wrong_count ?? 1 }} 次
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
