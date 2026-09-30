import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const registerMock = vi.fn()
const loginMock = vi.fn()
const fetchMeMock = vi.fn()

vi.mock('@/api/auth', () => ({
  register: (payload: unknown) => registerMock(payload),
  login: (payload: unknown) => loginMock(payload),
  fetchMe: () => fetchMeMock(),
}))

const session = {
  access_token: 'test-token',
  token_type: 'bearer',
  user: { id: 1, login_name: 'stu01', nickname: '小明' },
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    registerMock.mockReset()
    loginMock.mockReset()
    fetchMeMock.mockReset()
  })

  it('register 成功后写入 token 与用户信息', async () => {
    registerMock.mockResolvedValue(session)
    const auth = useAuthStore()

    await auth.register({ login_name: 'stu01', nickname: '小明', password: 'abc123' })

    expect(auth.token).toBe('test-token')
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.nickname).toBe('小明')
    expect(localStorage.getItem('word-study-token')).toBe('test-token')
  })

  it('login 成功后写入 token 与用户信息', async () => {
    loginMock.mockResolvedValue(session)
    const auth = useAuthStore()

    await auth.login({ login_name: 'stu01', password: 'abc123' })

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.login_name).toBe('stu01')
  })

  it('logout 清空本地会话', async () => {
    registerMock.mockResolvedValue(session)
    const auth = useAuthStore()
    await auth.register({ login_name: 'stu01', nickname: '小明', password: 'abc123' })

    auth.logout()

    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('word-study-token')).toBeNull()
  })
})
