import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GrammarCardPage from '@/pages/GrammarCardPage.vue'
import * as grammarApi from '@/api/grammar'
import { ApiError } from '@/api/client'

vi.mock('@/api/grammar', () => ({
  getPoint: vi.fn(),
  viewPoint: vi.fn(),
  guessPoint: vi.fn(),
  startCheck: vi.fn(),
  answerGrammarQuestion: vi.fn(),
  finishGrammarAttempt: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { pointId: 'G-A01' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const point: grammarApi.GrammarPointDetailResponse = {
  point: {
    id: 'G-A01',
    module: 'A',
    module_name: '形容词',
    title: '比较级最高级构成',
    depth: '核心',
    card_type: 'rule',
    status: 'not_started',
    has_wrong: false,
  },
  payload: {
    guess: {
      examples: [{ en: 'Tom is taller than Jim.', zh: '汤姆比吉姆高。' }],
      question: '为什么是 more interesting？',
      options: [
        { key: 'A', text: '因为它是多音节词' },
        { key: 'B', text: '因为它以 -ing 结尾' },
      ],
    },
    rule: {
      rule: '单音节加 -er；多音节加 more',
      signals: ['-er', 'more'],
      formula: 'tall → taller → tallest',
      anchors: [{ en: 'Tom is taller than Jim.', zh: '汤姆比吉姆高。', note: '单音节' }],
      trap: { wrong: 'interestinger', right: 'more interesting', why: '多音节不能加 -er' },
    },
  },
  check_questions: [
    {
      question_id: 'G-A01-Q01',
      level: 'L1',
      stem: 'Which is ____?',
      options: [
        { key: 'A', text: 'big' },
        { key: 'B', text: 'bigger' },
      ],
    },
  ],
}

function mountPage() {
  return mount(GrammarCardPage, {
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
}

/** 点击"猜一猜"选项（页面首个按钮是返回大纲，需按文本定位） */
async function clickGuessOption(wrapper: ReturnType<typeof mountPage>, text: string) {
  const target = wrapper
    .findAll('button')
    .find((button) => button.text().includes(text))
  expect(target).toBeTruthy()
  await target!.trigger('click')
}

describe('GrammarCardPage 猜一猜', () => {
  beforeEach(() => {
    vi.mocked(grammarApi.getPoint).mockResolvedValue(point)
    vi.mocked(grammarApi.viewPoint).mockResolvedValue({
      point_id: 'G-A01',
      status: 'learning',
      studied_at: null,
    })
    vi.mocked(grammarApi.guessPoint).mockResolvedValue({
      point_id: 'G-A01',
      choice_key: 'A',
      feedback: '对！三个音节以上的词一律用 more。',
    })
  })

  it('渲染猜一猜的选项且不渲染答案', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('因为它是多音节词')
    expect(text).not.toContain('"answer"')
    expect(vi.mocked(grammarApi.getPoint)).toHaveBeenCalledWith('G-A01')
  })

  it('选择后调用接口并展示服务端返回的反馈', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await clickGuessOption(wrapper, '因为它是多音节词')
    await flushPromises()

    expect(vi.mocked(grammarApi.guessPoint)).toHaveBeenCalledWith('G-A01', 'A')
    expect(wrapper.text()).toContain('对！三个音节以上的词一律用 more。')
  })

  it('反馈接口失败时展示错误且可重试', async () => {
    vi.mocked(grammarApi.guessPoint).mockRejectedValueOnce(
      new ApiError(422, 'invalid_choice_key', '选项不合法'),
    )
    const wrapper = mountPage()
    await flushPromises()

    await clickGuessOption(wrapper, '因为它是多音节词')
    await flushPromises()

    expect(wrapper.text()).toContain('选项不合法')
  })

  it('打开学卡即标记已学', async () => {
    mountPage()
    await flushPromises()

    expect(vi.mocked(grammarApi.viewPoint)).toHaveBeenCalledWith('G-A01')
  })
})
