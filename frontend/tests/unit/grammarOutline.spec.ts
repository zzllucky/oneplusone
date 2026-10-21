import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GrammarOutlinePage from '@/pages/GrammarOutlinePage.vue'
import { getOutline, getWrongPoints } from '@/api/grammar'
import type { GrammarOutlineResponse } from '@/api/grammar'

vi.mock('@/api/grammar', () => ({
  getOutline: vi.fn(),
  getWrongPoints: vi.fn(),
}))

const outline: GrammarOutlineResponse = {
  total_points: 2,
  mastered_count: 1,
  wrong_count: 1,
  modules: [
    {
      module: 'A',
      module_name: '形容词',
      points: [
        {
          id: 'G-A01',
          title: '比较级最高级构成',
          depth: '核心',
          card_type: 'rule',
          status: 'mastered',
          has_wrong: true,
          question_count: 6,
        },
      ],
    },
    {
      module: 'T',
      module_name: '时态',
      points: [
        {
          id: 'G-T01',
          title: '一般现在时',
          depth: '核心',
          card_type: 'rule',
          status: 'not_started',
          has_wrong: false,
          question_count: 0,
        },
      ],
    },
  ],
}

function mountPage() {
  return mount(GrammarOutlinePage, {
    global: {
      stubs: {
        RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
      },
    },
  })
}

describe('GrammarOutlinePage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getOutline).mockResolvedValue(outline)
    vi.mocked(getWrongPoints).mockResolvedValue({ total: 0, items: [] })
  })

  it('按模块分组渲染全部知识点', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('形容词')
    expect(text).toContain('比较级最高级构成')
    expect(text).toContain('一般现在时')
  })

  it('顶部展示已掌握 / 全部 / 错题计数', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('已掌握 1')
    expect(text).toContain('全部 2')
    expect(text).toContain('错题 1')
  })

  it('知识点条目展示状态徽章与错题标记', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('已掌握')
    expect(text).toContain('有错题')
    expect(text).toContain('未学')
  })

  it('只看错题筛选只展示仍有错题的知识点', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const target = wrapper
      .findAll('button')
      .find((button) => button.text().includes('只看错题'))
    await target!.trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('比较级最高级构成')
    expect(text).not.toContain('一般现在时')
    expect(vi.mocked(getWrongPoints)).toHaveBeenCalled()
  })

  it('无题库题的知识点不展示练习入口', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const links = wrapper.findAll('a')
    const targets = links.map((link) => link.attributes('href'))
    expect(targets).toContain('/grammar/G-A01')
  })
})
