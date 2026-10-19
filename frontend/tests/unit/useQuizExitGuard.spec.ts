import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { mount } from '@vue/test-utils'
import { useQuizExitGuard } from '@/composables/useQuizExitGuard'

// 模块级句柄，简化组件实例与断言的桥接；每个测试通过 boot() 重置
let guardHandle: ReturnType<typeof useQuizExitGuard> | null = null

function buildGuardChild(isActive: boolean) {
  return defineComponent({
    setup() {
      guardHandle = useQuizExitGuard({ isActive: () => isActive })
      return () => h('div', 'guard')
    },
  })
}

function makeRouter(child: ReturnType<typeof buildGuardChild>) {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: child },
      { path: '/other', component: { template: '<div>o</div>' } },
      { path: '/quiz', component: { template: '<div>q</div>' } },
    ],
  })
}

async function boot(active: boolean) {
  guardHandle = null
  const child = buildGuardChild(active)
  const router = makeRouter(child)
  const App = defineComponent({ setup: () => () => h(RouterView) })
  const wrapper = mount(App, { global: { plugins: [router] } })
  await router.isReady()
  await router.push('/')
  // 等待 child 被 router 真正实例化（onBeforeRouteLeave 需 setup 已跑过）
  for (let i = 0; i < 6; i++) {
    await nextTick()
  }
  if (guardHandle === null) {
    throw new Error('守卫组件未被 router 渲染，onBeforeRouteGuard 未注册')
  }
  return { wrapper, router }
}

beforeEach(() => {
  guardHandle = null
})

describe('useQuizExitGuard', () => {
  it('激活且 pending 为空：记录目标并阻止导航', async () => {
    const { router } = await boot(true)
    expect(guardHandle!.pending.value).toBe(null)
    await router.push('/other')
    expect(guardHandle!.pending.value).toBe('/other')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('激活且 pending 已设：保持原目标，阻止后续导航', async () => {
    const { router } = await boot(true)
    await router.push('/other') // 首次拦截，写入 pending
    await router.push('/quiz') // 已拦截，保持 /other
    expect(guardHandle!.pending.value).toBe('/other')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('未激活：正常放行，pending 不变', async () => {
    const { router } = await boot(false)
    await router.push('/other')
    expect(guardHandle!.pending.value).toBe(null)
    expect(router.currentRoute.value.path).toBe('/other')
  })

  it('cancelLeave：清空 pending，停留当前页', async () => {
    const { router } = await boot(true)
    await router.push('/other')
    expect(guardHandle!.pending.value).toBe('/other')
    guardHandle!.cancelLeave()
    expect(guardHandle!.pending.value).toBe(null)
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('confirmLeave：跳到 pending 并清空', async () => {
    const { router } = await boot(true)
    await router.push('/other')
    await guardHandle!.confirmLeave()
    expect(router.currentRoute.value.path).toBe('/other')
    expect(guardHandle!.pending.value).toBe(null)
  })
})
