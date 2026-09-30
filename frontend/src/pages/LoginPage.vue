<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const loginName = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await auth.login({ login_name: loginName.value.trim(), password: password.value })
    const redirect = (route.query.redirect as string) || '/home'
    router.push(redirect)
  } catch {
    // 后端对"登录名不存在"与"密码错误"返回同一提示（FR-003）
    errorMessage.value = '登录名或密码错误'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-md flex-col gap-4 py-6">
    <h1 class="text-2xl font-bold text-brand-600">登录</h1>

    <form class="card flex flex-col gap-3" @submit.prevent="submit">
      <label class="flex flex-col gap-1 text-sm text-gray-700">
        登录名
        <input v-model="loginName" class="input" type="text" autocomplete="username" />
      </label>

      <label class="flex flex-col gap-1 text-sm text-gray-700">
        密码
        <input
          v-model="password"
          class="input"
          type="password"
          autocomplete="current-password"
        />
      </label>

      <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

      <button class="btn-primary" type="submit" :disabled="submitting">
        {{ submitting ? '登录中…' : '登录' }}
      </button>
    </form>

    <p class="text-sm text-gray-600">
      还没有账号？
      <router-link class="text-brand-600 underline" to="/register">去注册</router-link>
    </p>
  </div>
</template>
