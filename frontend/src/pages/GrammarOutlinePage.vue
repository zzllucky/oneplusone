<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import GrammarPointItem from '@/components/GrammarPointItem.vue'
import { useGrammarStore } from '@/stores/grammar'

const grammar = useGrammarStore()
const onlyWrong = ref(false)

const visibleModules = computed(() => {
  if (!onlyWrong.value) return grammar.modules
  return grammar.modules
    .map((module) => ({
      ...module,
      points: module.points.filter((point) => point.has_wrong),
    }))
    .filter((module) => module.points.length > 0)
})

const visibleCount = computed(() =>
  visibleModules.value.reduce((sum, module) => sum + module.points.length, 0),
)

async function refresh() {
  await grammar.loadOutline()
}

async function toggleWrong() {
  onlyWrong.value = !onlyWrong.value
  if (onlyWrong.value) {
    await grammar.loadWrongPoints()
  }
}

onMounted(async () => {
  await refresh()
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-xl font-bold text-gray-900">语法</h2>
      <p class="text-sm text-gray-500">
        已掌握 {{ grammar.masteredCount }} · 全部 {{ grammar.totalPoints }} · 错题
        {{ grammar.wrongCount }}
      </p>
    </header>

    <nav class="flex gap-2">
      <button
        type="button"
        class="rounded-xl px-4 py-2 text-sm"
        :class="onlyWrong ? 'bg-white text-gray-600' : 'bg-brand-50 font-semibold text-brand-600'"
        @click="toggleWrong()"
      >
        全部知识点
      </button>
      <button
        type="button"
        class="rounded-xl px-4 py-2 text-sm"
        :class="onlyWrong ? 'bg-brand-50 font-semibold text-brand-600' : 'bg-white text-gray-600'"
        @click="toggleWrong()"
      >
        只看错题
      </button>
    </nav>

    <p v-if="grammar.loading" class="card text-gray-500">加载中…</p>

    <div v-else-if="grammar.error" class="card flex flex-col gap-2">
      <p class="text-sm text-red-600">{{ grammar.error }}</p>
      <button class="btn-ghost" type="button" @click="refresh()">重试</button>
    </div>

    <p v-else-if="grammar.isEmpty" class="card text-gray-500">暂无语法知识点</p>

    <template v-else>
      <p v-if="onlyWrong && visibleCount === 0" class="card text-gray-500">
        暂无错题，继续保持！
      </p>

      <section
        v-for="module in visibleModules"
        :key="module.module"
        class="flex flex-col gap-2"
      >
        <h3 class="text-sm font-semibold text-gray-500">
          {{ module.module }}. {{ module.module_name }}
        </h3>
        <div class="flex flex-col gap-2">
          <GrammarPointItem
            v-for="point in module.points"
            :key="point.id"
            :item="point"
          />
        </div>
      </section>
    </template>
  </div>
</template>
