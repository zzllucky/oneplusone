<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isPublic = computed(() => Boolean(route.meta.public))

const navItems = [
  { path: '/home', label: '首页', icon: '🏠' },
  { path: '/study', label: '学习', icon: '📖' },
  { path: '/quiz', label: '测验', icon: '✅' },
  { path: '/wrong-words', label: '错题', icon: '🗂️' },
  { path: '/summary', label: '总结', icon: '📊' },
  { path: '/settings', label: '设置', icon: '⚙️' },
]

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="mx-auto flex min-h-screen w-full max-w-6xl flex-col">
    <header
      v-if="!isPublic"
      class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-3"
    >
      <h1 class="text-lg font-bold text-brand-600">1+1=2</h1>
      <div class="flex items-center gap-3 text-sm text-gray-600">
        <span v-if="auth.user">你好，{{ auth.user.nickname }}</span>
        <button class="text-gray-500 underline" type="button" @click="logout">
          退出
        </button>
      </div>
    </header>

    <!-- 桌面侧栏 -->
    <div class="flex flex-1 flex-col md:flex-row">
      <nav
        v-if="!isPublic"
        class="hidden w-40 shrink-0 gap-1 border-r border-gray-200 bg-white p-3 md:flex md:flex-col"
      >
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="rounded-xl px-3 py-3 text-gray-700 hover:bg-brand-50"
          active-class="bg-brand-50 text-brand-600 font-semibold"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <main class="flex-1 overflow-x-hidden p-4 pb-24 md:pb-6">
        <slot />
      </main>
    </div>

    <!-- 手机底部导航 -->
    <nav
      v-if="!isPublic"
      class="fixed bottom-0 left-0 right-0 z-10 flex border-t border-gray-200 bg-white md:hidden"
    >
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex min-h-[56px] flex-1 flex-col items-center justify-center text-xs text-gray-600"
        active-class="text-brand-600 font-semibold"
      >
        <span class="text-lg">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
  </div>
</template>
