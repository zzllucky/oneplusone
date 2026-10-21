import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GrammarPracticePage from '@/pages/GrammarPracticePage.vue'
import * as grammarApi from '@/api/grammar'
import { ApiError } from '@/api/client'

vi.mock('@/api/grammar', () => ({
  getPoint: vi.fn(),
  startPractice: vi.fn(),
  answerGrammarQuestion: vi.fn(),
  finishGrammarAttempt: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { pointId: 'G-A01' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const questions: grammarApi.GrammarQuestion[] = [
  {
    question_id: 'G-A01-L1-01',
    level: 'L1',
    stem: '第一题',
    options: [
      { key: 'A', text: '选项一' },
      { key: 'B', text: '选项二' },
    ],
  },
  {
    question_id: 'G-A01-L2-01',
    level: 'L2',
    stem: '第二题',
    options: [
      { key: 'A', text: '选项三' },
      { key: 'B', text: '选项四' },
    ],
  },
]

const answer: grammarApi.GrammarAnswerResponse = {
  question_id: 'G-A01-L1-01',
  is_correct: true,
  correct_key: 'B',
  explanation: '解析',
  feedback: null,
  attempt: { total_count: 2, answered_count: 1, correct_count: 1, wrong_count: 0 },
  added_to_wrong_points: false,
  removed_from_wrong_points: false,
  correct_streak: 0,
}

const finished: grammarApi.GrammarFinishResponse = {
  attempt_id: 7,
  source: 'bank',
  point_id: 'G-A01',
  total_count: 2,
  correct_count: 2,
  wrong_count: 0,
  accuracy: 1,
  duration_seconds: 30,
  mastered: false,
  status: 'learning',
}

function mountPage() {
  return mount(GrammarPracticePage, {
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
}

async function clickByText(wrapper: ReturnType<typeof mountPage>, text: string) {
  const target = wrapper.findAll('button').find((button) => button.text().includes(text))
  expect(target).toBeTruthy()
  await target!.trigger('click')
  await flushPromises()
}

describe('GrammarPracticePage', () => {
  beforeEach(() => {
    vi.mocked(grammarApi.getPoint).mockResolvedValue({
      point: {
        id: 'G-A01',
        module: 'A',
        module_name: '形容词',
        title: '比较级最高级构成',
        depth: '核心',
        card_type: 'rule',
        status: 'learning',
        has_wrong: false,
      },
      payload: {},
      check_questions: [],
    })
    vi.mocked(grammarApi.startPractice).mockResolvedValue({
      attempt_id: 7,
      source: 'bank',
      point_id: 'G-A01',
      questions,
    })
    vi.mocked(grammarApi.answerGrammarQuestion).mockResolvedValue(answer)
    vi.mocked(grammarApi.finishGrammarAttempt).mockResolvedValue(finished)
  })

  it('展示难度层级标签与首题', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('L1')
    expect(wrapper.text()).toContain('第一题')
  })

  it('逐题推进：答完一题进入下一题', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await clickByText(wrapper, '选项一')
    expect(wrapper.text()).toContain('回答正确')
    await clickByText(wrapper, '下一题')

    expect(wrapper.text()).toContain('第二题')
    expect(wrapper.text()).toContain('L2')
  })

  it('答完全部题目后展示结算面板', async () => {
    const wrapper = mountPage()
    await flushPromises()

    await clickByText(wrapper, '选项一')
    await clickByText(wrapper, '下一题')
    await clickByText(wrapper, '选项三')
    await clickByText(wrapper, '查看结果')

    const text = wrapper.text()
    expect(text).toContain('共 2 题')
    expect(text).toContain('答对 2')
    expect(text).toContain('100%')
    expect(text).toContain('用时 30 秒')
  })

  it('无题库题时展示提示且不进入练习', async () => {
    vi.mocked(grammarApi.startPractice).mockRejectedValue(
      new ApiError(409, 'no_grammar_questions', '该知识点暂无练习题'),
    )
    const wrapper = mountPage()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('该知识点暂无练习题')
    expect(text).not.toContain('第一题')
  })
})
