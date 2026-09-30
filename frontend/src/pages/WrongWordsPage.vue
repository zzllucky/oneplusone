<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import WrongWordItem from '@/components/WrongWordItem.vue'
import WrongArchiveItem from '@/components/WrongArchiveItem.vue'
import { useWrongWordsStore } from '@/stores/wrongWords'
import { useWrongWordArchiveStore } from '@/stores/wrongWordArchive'
import type { ArchiveSort } from '@/api/wrongWords'

type TabKey = 'book' | 'archive'

const wrongWords = useWrongWordsStore()
const archive = useWrongWordArchiveStore()

const tab = ref<TabKey>('book')
const tabs: { key: TabKey; label: string }[] = [
  { key: 'book', label: '错题本' },
  { key: 'archive', label: '错题库' },
]

const isBook = computed(() => tab.value === 'book')

async function refresh() {
  if (isBook.value) {
    await wrongWords.load()
    return
  }
  await archive.load()
}

async function switchTab(next: TabKey) {
  if (tab.value === next) return
  tab.value = next
  await refresh()
}

async function changeSort(sort: ArchiveSort) {
  await archive.setSort(sort)
}

onMounted(async () => {
  await Promise.all([wrongWords.load(), archive.load()])
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-xl font-bold text-gray-900">错题</h2>
      <p class="text-sm text-gray-500">
        错题本 {{ wrongWords.total }} 条 · 错题库 {{ archive.total }} 条
      </p>
    </header>

    <nav class="flex gap-2">
      <button
        v-for="item in tabs"
        :key="item.key"
        type="button"
        class="rounded-xl px-4 py-2 text-sm"
        :class="
          tab === item.key
            ? 'bg-brand-50 font-semibold text-brand-600'
            : 'bg-white text-gray-600'
        "
        @click="switchTab(item.key)"
      >
        {{ item.label }}
      </button>
    </nav>

    <!-- 错题本 -->
    <template v-if="isBook">
      <section class="card flex flex-col gap-2">
        <p class="text-sm text-gray-600">
          待复习队列：答错进入，专项练习中<strong>连续答对 2 次</strong>后移出；
          日期切换、重新登录、学习新单词都不会清空。
        </p>
        <router-link v-if="!wrongWords.isEmpty" class="btn-primary" to="/review">
          进入错题专项练习
        </router-link>
        <button v-else class="btn-primary" type="button" disabled>
          错题本为空，暂无可练习的单词
        </button>
      </section>

      <p v-if="wrongWords.isEmpty" class="card text-gray-500">暂无错题，继续保持！</p>

      <div v-else class="flex flex-col gap-3">
        <WrongWordItem
          v-for="item in wrongWords.items"
          :key="item.word_id"
          :item="item"
        />
        <button
          v-if="wrongWords.hasMore"
          class="btn-ghost"
          type="button"
          :disabled="wrongWords.loading"
          @click="wrongWords.loadMore()"
        >
          {{ wrongWords.loading ? '加载中…' : `加载更多（已显示 ${wrongWords.items.length} / ${wrongWords.total}）` }}
        </button>
      </div>
    </template>

    <!-- 错题库 -->
    <template v-else>
      <section class="card flex flex-col gap-2">
        <p class="text-sm text-gray-600">
          永久档案：只要答错过就一直保留，只累计错误次数、不记录时间，
          专项练习答对也<strong>不会移除</strong>。
        </p>
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-gray-500">排序</span>
          <button
            type="button"
            class="rounded-xl px-3 py-1 text-sm"
            :class="
              archive.sort === 'added'
                ? 'bg-brand-50 font-semibold text-brand-600'
                : 'bg-white text-gray-600'
            "
            @click="changeSort('added')"
          >
            加入顺序
          </button>
          <button
            type="button"
            class="rounded-xl px-3 py-1 text-sm"
            :class="
              archive.sort === 'count'
                ? 'bg-brand-50 font-semibold text-brand-600'
                : 'bg-white text-gray-600'
            "
            @click="changeSort('count')"
          >
            错误次数
          </button>
        </div>
        <router-link v-if="!archive.isEmpty" class="btn-primary" to="/archive">
          进入错题库专项练习
        </router-link>
        <button v-else class="btn-primary" type="button" disabled>
          错题库为空，暂无可练习的单词
        </button>
      </section>

      <p v-if="archive.isEmpty" class="card text-gray-500">错题库暂无记录</p>

      <div v-else class="flex flex-col gap-3">
        <WrongArchiveItem
          v-for="item in archive.items"
          :key="item.word_id"
          :item="item"
        />
        <button
          v-if="archive.hasMore"
          class="btn-ghost"
          type="button"
          :disabled="archive.loading"
          @click="archive.loadMore()"
        >
          {{ archive.loading ? '加载中…' : `加载更多（已显示 ${archive.items.length} / ${archive.total}）` }}
        </button>
      </div>
    </template>
  </div>
</template>
