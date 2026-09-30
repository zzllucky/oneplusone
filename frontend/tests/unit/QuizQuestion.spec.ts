import { describe, expect, it } from 'vitest'
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
