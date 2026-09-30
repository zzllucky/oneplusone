<script setup lang="ts">
import { onMounted } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { registerAudioWarmup } from '@/composables/useAudioWarmup'

// 首次用户手势（点击 / 触摸 / 按键）即预热音频链路，避免首个发音被吞掉开头
onMounted(registerAudioWarmup)
</script>

<template>
  <AppShell>
    <router-view />
  </AppShell>
</template>
