<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchSettings, updateSettings } from '@/api/settings'
import { ApiError } from '@/api/client'
import { loadSoundPreferences, setSoundEnabled, setSoundVolume } from '@/sounds/soundEffects'

const goal = ref(20)
const saved = ref(false)
const errorMessage = ref('')
const submitting = ref(false)

/** 音效偏好只存本设备、不进账号；默认关闭（FR-012 / FR-024）。 */
const soundEnabled = ref(false)
const soundVolume = ref(70)

const inRange = computed(
  () => Number.isInteger(goal.value) && goal.value >= 1 && goal.value <= 200,
)

onMounted(async () => {
  const settings = await fetchSettings()
  goal.value = settings.daily_goal
  const preferences = loadSoundPreferences()
  soundEnabled.value = preferences.enabled
  soundVolume.value = preferences.volume
})

function toggleSound(event: Event) {
  const enabled = (event.target as HTMLInputElement).checked
  soundEnabled.value = enabled
  setSoundEnabled(enabled)
}

function changeVolume(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  soundVolume.value = value
  setSoundVolume(value)
}

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

    <section class="card flex flex-col gap-3">
      <h3 class="font-semibold text-gray-900">音效</h3>

      <label class="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          class="h-4 w-4"
          :checked="soundEnabled"
          @change="toggleSound"
        />
        开启音效（答题与进入页面时播放英文语音）
      </label>

      <label class="flex flex-col gap-1 text-sm text-gray-700">
        音量（{{ soundVolume }}）
        <input
          type="range"
          min="0"
          max="100"
          step="10"
          :value="soundVolume"
          :disabled="!soundEnabled"
          @change="changeVolume"
        />
      </label>

      <p class="text-sm text-gray-500">
        默认关闭；开启后仅在本设备生效，不写入账号、不会同步到其他设备。
      </p>
    </section>
  </div>
</template>
