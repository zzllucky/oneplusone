import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import GrammarQuestionCard from '@/components/GrammarQuestionCard.vue'
import type { GrammarAnswerResponse, GrammarQuestion } from '@/api/grammar'

const question: GrammarQuestion = {
  question_id: 'G-A01-Q01',
  level: 'L1',
  stem: 'Which is ____, the sun or the moon?',
  options: [
    { key: 'A', text: 'big' },
    { key: 'B', text: 'bigger' },
    { key: 'C', text: 'biggest' },
  ],
}

const baseResult: GrammarAnswerResponse = {
  question_id: 'G-A01-Q01',
  is_correct: false,
  correct_key: 'B',
  explanation: '两者比较 → bigger。',
  feedback: '两者比较要用比较级',
  attempt: { total_count: 3, answered_count: 1, correct_count: 0, wrong_count: 1 },
  added_to_wrong_points: true,
  removed_from_wrong_points: false,
  correct_streak: 0,
}

describe('GrammarQuestionCard', () => {
  it('渲染题干与选项且不含答案', () => {
    const wrapper = mount(GrammarQuestionCard, { props: { question } })

    expect(wrapper.text()).toContain(question.stem)
    expect(wrapper.text()).toContain('bigger')
    expect(wrapper.findAll('button')).toHaveLength(3)
  })

  it('点击选项触发 select', async () => {
    const wrapper = mount(GrammarQuestionCard, { props: { question } })

    await wrapper.findAll('button')[1].trigger('click')

    expect(wrapper.emitted('select')).toEqual([['B']])
  })

  it('作答后展示对错、正确答案与解析', async () => {
    const wrapper = mount(GrammarQuestionCard, { props: { question } })
    await wrapper.setProps({ result: baseResult })

    const text = wrapper.text()
    expect(text).toContain('回答错误')
    expect(text).toContain('正确答案 B')
    expect(text).toContain('两者比较 → bigger。')
  })

  it('答错时展示所选错项的错因说明', async () => {
    const wrapper = mount(GrammarQuestionCard, { props: { question } })
    await wrapper.setProps({ result: baseResult })

    expect(wrapper.text()).toContain('两者比较要用比较级')
  })

  it('答对时不展示错因说明', async () => {
    const wrapper = mount(GrammarQuestionCard, {
      props: {
        question,
        result: { ...baseResult, is_correct: true, feedback: null },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('回答正确')
    expect(text).not.toContain('两者比较要用比较级')
  })

  it('已作答后禁止重复点击', async () => {
    const wrapper = mount(GrammarQuestionCard, {
      props: { question, result: baseResult },
    })

    expect(wrapper.findAll('button')[0].attributes('disabled')).toBeDefined()
  })
})
