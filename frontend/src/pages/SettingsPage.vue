<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchSettings, updateSettings } from '@/api/settings'
import { ApiError } from '@/api/client'

const goal = ref(20)
const saved = ref(false)
const errorMessage = ref('')
const submitting = ref(false)

const inRange = computed(
  () => Number.isInteger(goal.value) && goal.value >= 1 && goal.value <= 200,
)

onMounted(async () => {
  const settings = await fetchSettings()
  goal.value = settings.daily_goal
})

async function save() {
  errorMessage.value = ''
  saved.value = false
  if (!inRange.value) {
    errorMessage.value = '每日目标需为 1–200 之间的整数'
    return
  }
  submitting.value = true
  try {
    const settings = await updateSettings(goal.value)
    goal.value = settings.daily_goal
    saved.value = true
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '保存失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex max-w-xl flex-col gap-4">
    <h2 class="text-xl font-bold text-gray-900">设置每日单词目标</h2>

    <form class="card flex flex-col gap-3" @submit.prevent="save">
      <label class="flex flex-col gap-1 text-sm text-gray-700">
        每日单词目标（1–200）
        <input v-model.number="goal" class="input" type="number" min="1" max="200" />
        <span v-if="!inRange" class="text-xs text-red-600">
          请输入 1–200 之间的整数
        </span>
      </label>

      <p class="text-sm text-gray-500">
        当日已分配的单词不受影响，新目标次日生效。
      </p>

      <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>
      <p v-if="saved" class="text-sm text-green-600">已保存</p>

      <button class="btn-primary" type="submit" :disabled="submitting || !inRange">
        {{ submitting ? '保存中…' : '保存' }}
      </button>
    </form>
  </div>
</template>
