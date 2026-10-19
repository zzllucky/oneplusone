/**
 * 答题页关键接缝：离开拦截（US1）+ 切题防连点（US2）。
 * 真实路由（内存历史）+ 真实页面 + 真实守卫/弹窗；仅替换 store 与网络层。
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/sounds/soundEffects', () => ({
  playQuizStart: vi.fn(),
  onCorrect: vi.fn(),
  onWrong: vi.fn(),
  resetStreak: vi.fn(),
  __resetSoundState: vi.fn(),
  playPageSound: vi.fn(),
  setSoundEnabled: vi.fn(),
}))

vi.mock('@/api/quiz', () => ({
  startDailyQuiz: vi.fn(),
  answerDaily: vi.fn(),
  finishDailyQuiz: vi.fn(),
  startReviewQuiz: vi.fn(),
  answerReview: vi.fn(),
  finishReviewQuiz: vi.fn(),
  startArchiveQuiz: vi.fn(),
  answerArchive: vi.fn(),
  finishArchiveQuiz: vi.fn(),
}))

vi.mock('@/stores/study', () => ({
  useStudyStore: () => ({
    loadToday: vi.fn(async () => undefined),
    quizUnlocked: true,
    viewedCount: 5,
    totalCount: 5,
  }),
}))

vi.mock('@/stores/wrongWords', () => ({
  useWrongWordsStore: () => ({ load: vi.fn(async () => undefined) }),
}))

vi.mock('@/stores/wrongWordArchive', () => ({
  useWrongWordArchiveStore: () => ({ load: vi.fn(async () => undefined) }),
}))

import { onCorrect, onWrong, playQuizStart } from '@/sounds/soundEffects'
import * as quizApi from '@/api/quiz'
import TodayQuizPage from '@/pages/TodayQuizPage.vue'
import ReviewQuizPage from '@/pages/ReviewQuizPage.vue'
import ArchiveQuizPage from '@/pages/ArchiveQuizPage.vue'

const baseQuestion = {
  question_id: 1,
  word_id: 1,
  type: 'en2zh' as const,
  prompt: 'ability',
  options: ['能力；才能', '机会', '建议', '习惯'],
}

async function mountPage(PageComponent: any) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: PageComponent },
      { path: '/home', component: { template: '<div>home</div>' } },
      { path: '/study', component: { template: '<div>study</div>' } },
      { path: '/wrong-words', component: { template: '<div>ww</div>' } },
      { path: '/summary', component: { template: '<div>sum</div>' } },
    ],
  })
  const App = defineComponent({ setup: () => () => h(RouterView) })
  const wrapper = mount(App, { global: { plugins: [router] } })
  await router.isReady()
  await router.push('/')
  for (let i = 0; i < 6; i++) await nextTick()
  return { wrapper, router }
}

async function startAndAnswerOne(wrapper: any) {
  const startBtn = wrapper.findAll('button').find((b: any) => b.text().includes('开始'))
  if (!startBtn) throw new Error('未找到开始按钮')
  await startBtn.trigger('click')
  await flushPromises()
  await wrapper.findAll('button')[0].trigger('click')
  await flushPromises()
}

const pageCases = [
  {
    name: 'TodayQuizPage',
    Page: TodayQuizPage,
    startMock: () =>
      vi.mocked(quizApi.startDailyQuiz).mockResolvedValue({
        questions: [
          { ...baseQuestion, question_id: 1 },
          { ...baseQuestion, question_id: 2 },
        ],
      } as never),
    answerMock: () =>
      vi.mocked(quizApi.answerDaily).mockResolvedValue({
        is_correct: true,
        correct_index: 0,
      } as never),
  },
  {
    name: 'ReviewQuizPage',
    Page: ReviewQuizPage,
    startMock: () =>
      vi.mocked(quizApi.startReviewQuiz).mockResolvedValue({
        questions: [
          { ...baseQuestion, question_id: 1 },
          { ...baseQuestion, question_id: 2 },
        ],
      } as never),
    answerMock: () =>
      vi.mocked(quizApi.answerReview).mockResolvedValue({
        is_correct: true,
        correct_index: 0,
        correct_streak: 1,
      } as never),
  },
  {
    name: 'ArchiveQuizPage',
    Page: ArchiveQuizPage,
    startMock: () =>
      vi.mocked(quizApi.startArchiveQuiz).mockResolvedValue({
        questions: [
          { ...baseQuestion, question_id: 1 },
          { ...baseQuestion, question_id: 2 },
        ],
      } as never),
    answerMock: () =>
      vi.mocked(quizApi.answerArchive).mockResolvedValue({
        is_correct: true,
        correct_index: 0,
        archive_wrong_count: 0,
      } as never),
  },
]

describe('答题页离开拦截（US1）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  for (const c of pageCases) {
    describe(c.name, () => {
      beforeEach(() => {
        c.startMock()
        c.answerMock()
      })

      it('未开始时点导航不弹窗', async () => {
        const { router, wrapper } = await mountPage(c.Page)
        await router.push('/home')
        await flushPromises()
        expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
        expect(router.currentRoute.value.path).toBe('/home')
      })

      it('答题中点导航：弹窗出现，停留原题', async () => {
        const { router, wrapper } = await mountPage(c.Page)
        await startAndAnswerOne(wrapper)
        expect(playQuizStart).toHaveBeenCalled()
        expect(onCorrect).toHaveBeenCalledTimes(1)
        await router.push('/home')
        await flushPromises()
        const dialog = wrapper.find('[role="dialog"]')
        expect(dialog.exists()).toBe(true)
        expect(dialog.text()).toContain('离开测验？')
        expect(dialog.text()).toContain('离开后本轮测验不会保留')
        expect(router.currentRoute.value.path).toBe('/')
      })

      it('点「继续答题」关闭弹窗，不跳走', async () => {
        const { router, wrapper } = await mountPage(c.Page)
        await startAndAnswerOne(wrapper)
        await router.push('/home')
        await flushPromises()
        const stayBtn = wrapper
          .findAll('[role="dialog"] button')
          .find((b: any) => b.text() === '继续答题')!
        await stayBtn.trigger('click')
        await flushPromises()
        expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
        expect(router.currentRoute.value.path).toBe('/')
      })

      it('点「离开」跳到目标路由', async () => {
        const { router, wrapper } = await mountPage(c.Page)
        await startAndAnswerOne(wrapper)
        await router.push('/home')
        await flushPromises()
        const leaveBtn = wrapper
          .findAll('[role="dialog"] button')
          .find((b: any) => b.text() === '离开')!
        await leaveBtn.trigger('click')
        await flushPromises()
        expect(router.currentRoute.value.path).toBe('/home')
      })
    })
  }
})

describe('答题页切题防连点（US2）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  for (const c of pageCases) {
    describe(c.name, () => {
      beforeEach(() => {
        c.startMock()
        c.answerMock()
      })

      it('切题后 300ms 内点选项不触发音效', async () => {
        const { wrapper } = await mountPage(c.Page)
        await startAndAnswerOne(wrapper)
        const before = (onCorrect as unknown as { mock: { calls: unknown[] } }).mock.calls.length
        // 点「下一题」
        const nextBtn = wrapper
          .findAll('button')
          .find((b: any) => b.text().includes('下一题'))!
        await nextBtn.trigger('click')
        await flushPromises()
        await wrapper.vm.$nextTick()
        // 锁定窗口内点选项
        const optionBtn = wrapper.findAll('button')[0]
        expect(optionBtn, '新题应已渲染 4 个选项按钮').toBeTruthy()
        await optionBtn.trigger('click')
        await flushPromises()
        const after = (onCorrect as unknown as { mock: { calls: unknown[] } }).mock.calls.length
        expect(after).toBe(before)
      })
    })
  }
})
