import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import QuizQuestion from '@/components/QuizQuestion.vue'

const question = {
  question_id: 101,
  word_id: 101,
  type: 'en2zh' as const,
  prompt: 'ability',
  options: ['能力；才能', '机会', '建议', '习惯'],
}

describe('QuizQuestion', () => {
  it('渲染 4 个选项且不下发正确答案', () => {
    const wrapper = mount(QuizQuestion, {
      props: { question, index: 0, total: 20 },
    })

    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(4)
    expect(wrapper.text()).toContain('请选择正确的中文释义')
    expect(wrapper.text()).not.toContain('correct_index')
  })

  it('点击选项触发 select', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question, index: 0, total: 20 },
    })

    await wrapper.findAll('button')[1].trigger('click')

    expect(wrapper.emitted('select')).toEqual([[1]])
  })

  it('作答后展示对错与正确答案', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question, index: 0, total: 20 },
    })

    await wrapper.setProps({ result: { is_correct: false, correct_index: 0 } })

    expect(wrapper.text()).toContain('回答错误')
    expect(wrapper.text()).toContain('能力；才能')
  })

  it('答对时展示正确反馈', () => {
    const wrapper = mount(QuizQuestion, {
      props: {
        question,
        index: 2,
        total: 20,
        result: { is_correct: true, correct_index: 2 },
      },
    })

    expect(wrapper.text()).toContain('回答正确')
  })
})

describe('QuizQuestion 选项锁定窗口', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  const questionA = {
    question_id: 1,
    word_id: 1,
    type: 'en2zh' as const,
    prompt: 'a',
    options: ['A1', 'A2', 'A3', 'A4'],
  }
  const questionB = {
    question_id: 2,
    word_id: 2,
    type: 'en2zh' as const,
    prompt: 'b',
    options: ['B1', 'B2', 'B3', 'B4'],
  }

  it('切题后 300ms 内点击选项不触发 select', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question: questionA, index: 0, total: 2 },
    })
    await wrapper.setProps({ question: questionB, index: 1 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('select')).toBeFalsy()
  })

  it('切题后 300ms 之后点击选项触发 select', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question: questionA, index: 0, total: 2 },
    })
    await wrapper.setProps({ question: questionB, index: 1 })
    vi.advanceTimersByTime(300)
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('select')).toEqual([[0]])
  })

  it('锁定窗口内的点击不会在窗口结束后被补提交', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question: questionA, index: 0, total: 2 },
    })
    await wrapper.setProps({ question: questionB, index: 1 })
    await wrapper.findAll('button')[1].trigger('click') // 锁定期内
    vi.advanceTimersByTime(300)
    await wrapper.findAll('button')[1].trigger('click') // 窗口结束
    expect(wrapper.emitted('select')).toEqual([[1]])
  })

  it('锁定窗口不改变选项的视觉禁用态（无 answered 时不应出现 disabled）', async () => {
    const wrapper = mount(QuizQuestion, {
      props: { question: questionA, index: 0, total: 2 },
    })
    await wrapper.setProps({ question: questionB, index: 1 })
    const btn = wrapper.findAll('button')[0]
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
