/** 测验页与音效的接线：开始 / 答对 / 答错分别触发对应音效（播放被 mock）。 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

vi.mock('@/sounds/soundEffects', () => ({
  playQuizStart: vi.fn(),
  onCorrect: vi.fn(() => 'streak.1'),
  onWrong: vi.fn(),
  resetStreak: vi.fn(),
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

vi.mock('@/api/quiz', () => ({
  startDailyQuiz: vi.fn(),
  answerDaily: vi.fn(),
  finishDailyQuiz: vi.fn(),
}))

import * as quizApi from '@/api/quiz'
import { onCorrect, onWrong, playQuizStart } from '@/sounds/soundEffects'
import TodayQuizPage from '@/pages/TodayQuizPage.vue'

const question = {
  question_id: 1,
  word_id: 1,
  type: 'en2zh' as const,
  prompt: 'ability',
  options: ['能力；才能', '机会', '建议', '习惯'],
}

function nextQuestion(questionId: number) {
  return { ...question, question_id: questionId }
}

async function startQuiz() {
  vi.mocked(quizApi.startDailyQuiz).mockResolvedValue({
    questions: [nextQuestion(1), nextQuestion(2), nextQuestion(3)],
  } as never)

  const wrapper = mount(TodayQuizPage, {
    global: { stubs: { RouterLink: true } },
  })
  const startButton = wrapper.findAll('button').find((node) => node.text().includes('开始测验'))
  expect(startButton, '未找到开始测验按钮').toBeTruthy()
  await startButton!.trigger('click')
  await wrapper.vm.$nextTick()
  await Promise.resolve()
  return wrapper
}

describe('测验页音效接线', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(quizApi.answerDaily).mockResolvedValue({
      is_correct: true,
      correct_index: 0,
    } as never)
  })

  it('点击开始测验：播开始语音并重置连对', async () => {
    await startQuiz()
    expect(playQuizStart).toHaveBeenCalledTimes(1)
  })

  it('答对触发连杀音效，连续答对逐次调用', async () => {
    const wrapper = await startQuiz()

    await wrapper.findAll('button')[0].trigger('click')
    await Promise.resolve()
    expect(onCorrect).toHaveBeenCalledTimes(1)

    // 下一题后继续答对
    const nextButton = wrapper.findAll('button').find((node) => node.text().includes('下一题'))
    await nextButton!.trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.findAll('button')[0].trigger('click')
    await Promise.resolve()
    expect(onCorrect).toHaveBeenCalledTimes(2)
  })

  it('答错触发答错音效', async () => {
    vi.mocked(quizApi.answerDaily).mockResolvedValue({
      is_correct: false,
      correct_index: 0,
    } as never)

    const wrapper = await startQuiz()
    await wrapper.findAll('button')[1].trigger('click')
    await Promise.resolve()

    expect(onWrong).toHaveBeenCalledTimes(1)
    expect(onCorrect).not.toHaveBeenCalled()
  })
})
