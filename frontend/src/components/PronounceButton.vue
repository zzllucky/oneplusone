<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { fetchAudio } from '@/api/client'
import { getPlayer, warmUpAudio } from '@/composables/useAudioWarmup'
import { useSpeech } from '@/composables/useSpeech'

const props = withDefaults(
  defineProps<{ text: string; label?: string; small?: boolean }>(),
  { label: '发音', small: false },
)

const hint = ref('')
const playing = ref(false)
const { speak } = useSpeech()

const speakable = computed(() => props.text.trim())

/** 等音频可完整播放再出声，避免解码未就绪时丢掉开头。 */
function waitUntilPlayable(audio: HTMLAudioElement): Promise<void> {
  return new Promise((resolve) => {
    if (audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
      resolve()
      return
    }
    const done = () => {
      audio.removeEventListener('canplaythrough', done)
      audio.removeEventListener('error', done)
      resolve()
    }
    audio.addEventListener('canplaythrough', done)
    audio.addEventListener('error', done)
  })
}

async function play() {
  if (!speakable.value || playing.value) return
  hint.value = ''
  playing.value = true
  let url = ''
  try {
    // 兜底预热：正常流程中首次手势已预热，这里保证直接进入页面即点也能热链路
    await warmUpAudio()

    const blob = await fetchAudio(`/api/pronounce/${encodeURIComponent(speakable.value)}`)
    url = URL.createObjectURL(blob)

    const audio = getPlayer()
    audio.pause()
    audio.src = url
    audio.currentTime = 0
    await waitUntilPlayable(audio)

    const finish = () => {
      URL.revokeObjectURL(url)
      playing.value = false
    }
    audio.onended = finish
    audio.onerror = finish

    await audio.play()
  } catch {
    if (url) URL.revokeObjectURL(url)
    // 服务端无发音 → 降级为浏览器语音合成（不阻断学习）
    const ok = speak(speakable.value)
    hint.value = ok ? '已使用本地朗读' : '当前浏览器不支持朗读，可继续学习'
    playing.value = false
  }
}

onBeforeUnmount(() => {
  // 播放器是共享的，只在自己正在播放时才停止
  if (playing.value) {
    getPlayer().pause()
    playing.value = false
  }
})
</script>

<template>
  <div class="flex flex-col items-start gap-1">
    <button
      type="button"
      class="btn-ghost min-w-[44px] px-3"
      :class="props.small ? 'text-xs' : ''"
      :disabled="playing || !speakable"
      @click="play"
    >
      🔊 {{ playing ? '播放中' : props.label }}
    </button>
    <p v-if="hint" class="text-xs text-gray-500">{{ hint }}</p>
  </div>
</template>
