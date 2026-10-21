import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AppShell from '@/components/AppShell.vue'
import GrammarPointItem from '@/components/GrammarPointItem.vue'
import GrammarQuestionCard from '@/components/GrammarQuestionCard.vue'
import type { GrammarPointItem as PointItem, GrammarQuestion } from '@/api/grammar'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: {}, fullPath: '/grammar', path: '/grammar' }),
  useRouter: () => ({ push: () => undefined }),
}))

const point: PointItem = {
  id: 'G-A01',
  title: '比较级最高级构成',
  depth: '核心',
  card_type: 'rule',
  status: 'not_started',
  has_wrong: false,
  question_count: 6,
}

const question: GrammarQuestion = {
  question_id: 'G-A01-Q01',
  level: 'L1',
  stem: 'Which is ____, the sun or the moon?',
  options: [
    { key: 'A', text: 'big' },
    { key: 'B', text: 'bigger' },
  ],
}

/**
 * 语法页跨端约束（FR-021 / 场景 G）：jsdom 无真实布局，
 * 故沿用 responsive.spec.ts 的"结构约束"方式校验。
 */
describe('语法页响应式与触控区域', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('导航含「语法」入口且底部导航在窄屏可见', () => {
    const wrapper = mount(AppShell, {
      global: {
        stubs: { 'router-link': { template: '<a><slot /></a>' } },
      },
    })

    expect(wrapper.html()).toContain('/grammar')
    expect(wrapper.html()).toContain('语法')
    expect(wrapper.html()).toContain('md:hidden')
  })

  it('知识点条目纵向排布且不使用固定宽度', async () => {
    const wrapper = mount(GrammarPointItem, {
      props: { item: point },
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    const html = wrapper.html()
    expect(html).toContain('flex-col')
    expect(html).not.toMatch(/w-\[\d+px\]/)
  })

  it('选项按钮触控区满足 py-3（≥44px）', () => {
    const wrapper = mount(GrammarQuestionCard, { props: { question } })

    expect(wrapper.html()).toContain('py-3')
    expect(wrapper.findAll('button')).toHaveLength(2)
  })
})
