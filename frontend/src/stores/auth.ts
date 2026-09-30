import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { clearToken, getToken, setToken } from '@/api/client'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<authApi.UserOut | null>(null)
  const dailyGoal = ref(20)

  const isAuthenticated = computed(() => Boolean(token.value))

  function applySession(payload: authApi.TokenResponse) {
    token.value = payload.access_token
    setToken(payload.access_token)
    user.value = payload.user
  }

  async function register(payload: {
    login_name: string
    nickname: string
    password: string
  }) {
    applySession(await authApi.register(payload))
  }

  async function login(payload: { login_name: string; password: string }) {
    applySession(await authApi.login(payload))
  }

  async function loadMe() {
    if (!token.value) return
    const me = await authApi.fetchMe()
    user.value = { id: me.id, login_name: me.login_name, nickname: me.nickname }
    dailyGoal.value = me.daily_goal
  }

  function logout() {
    token.value = ''
    user.value = null
    clearToken()
  }

  return { token, user, dailyGoal, isAuthenticated, register, login, loadMe, logout }
})
