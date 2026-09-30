import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AppShell from '@/components/AppShell.vue'
import WordCard from '@/components/WordCard.vue'
import QuizQuestion from '@/components/QuizQuestion.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: {}, fullPath: '/home', path: '/home' }),
  useRouter: () => ({ push: () => undefined }),
}))

/**
 * 响应式（US7）：jsdom 无真实布局，故以"结构约束"方式校验——
 * 1. 外壳使用断点类（md:）且主内容区禁止横向溢出
 * 2. 关键触控元素的高度类不小于 44px（R-010）
 */
describe('响应式与触控区域', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('AppShell 使用 md 断点并禁止主区域横向滚动', () => {
    const wrapper = mount(AppShell, {
      global: { stubs: { 'router-link': true } },
    })

    expect(wrapper.html()).toContain('md:flex')
    expect(wrapper.html()).toContain('overflow-x-hidden')
    expect(wrapper.html()).toContain('max-w-6xl')
    expect(wrapper.html()).toContain('fixed bottom-0')
  })

  it('单词卡与选项按钮触控区不小于 44px', () => {
    const card = mount(WordCard, {
      props: {
        word: {
          word_id: 1,
          spelling: 'ability',
          meaning_zh: '能力',
          phrase: null,
          phonetic: null,
          order_index: 1,
          viewed_at: null,
        },
      },
    })
    // btn-* 由 style.css 的 @apply 提供 min-h-[44px]
    expect(card.html()).toContain('btn-primary')

    const quiz = mount(QuizQuestion, {
      props: {
        question: {
          question_id: 1,
          word_id: 1,
          type: 'en2zh',
          prompt: 'ability',
          options: ['a', 'b', 'c', 'd'],
        },
        index: 0,
        total: 20,
      },
    })
    expect(quiz.html()).toContain('min-h-[44px]')
  })
})
