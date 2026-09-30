<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const loginName = ref('')
const nickname = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

const loginNameValid = computed(() => /^[A-Za-z0-9_]{3,20}$/.test(loginName.value))
const nicknameValid = computed(() => {
  const value = nickname.value.trim()
  return value.length >= 1 && value.length <= 24
})
const passwordValid = computed(() => password.value.length >= 6)
const formValid = computed(
  () => loginNameValid.value && nicknameValid.value && passwordValid.value,
)

async function submit() {
  errorMessage.value = ''
  if (!formValid.value) {
    errorMessage.value = '请检查登录名、昵称与密码格式'
    return
  }
  submitting.value = true
  try {
    await auth.register({
      login_name: loginName.value.trim(),
      nickname: nickname.value.trim(),
      password: password.value,
    })
    const redirect = (route.query.redirect as string) || '/home'
    router.push(redirect)
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '注册失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-md flex-col gap-4 py-6">
    <h1 class="text-2xl font-bold text-brand-600">注册账号</h1>

    <form class="card flex flex-col gap-3" @submit.prevent="submit">
      <label class="flex flex-col gap-1 text-sm text-gray-700">
        登录名（3–20 位字母 / 数字 / 下划线）
        <input v-model="loginName" class="input" type="text" autocomplete="username" />
        <span v-if="loginName && !loginNameValid" class="text-xs text-red-600">
          仅支持字母、数字、下划线，长度 3–20
        </span>
      </label>

      <label class="flex flex-col gap-1 text-sm text-gray-700">
        用户昵称（1–24 个字符，可重复）
        <input v-model="nickname" class="input" type="text" />
        <span v-if="nickname && !nicknameValid" class="text-xs text-red-600">
          昵称长度需为 1–24 个字符
        </span>
      </label>

      <label class="flex flex-col gap-1 text-sm text-gray-700">
        密码（至少 6 位）
        <input
          v-model="password"
          class="input"
          type="password"
          autocomplete="new-password"
        />
        <span v-if="password && !passwordValid" class="text-xs text-red-600">
          密码至少 6 位
        </span>
      </label>

      <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

      <button class="btn-primary" type="submit" :disabled="submitting || !formValid">
        {{ submitting ? '提交中…' : '注册并进入' }}
      </button>
    </form>

    <p class="text-sm text-gray-600">
      已有账号？
      <router-link class="text-brand-600 underline" to="/login">去登录</router-link>
    </p>
  </div>
</template>
