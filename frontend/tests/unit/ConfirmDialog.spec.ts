import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

describe('ConfirmDialog', () => {
  const baseProps = {
    open: true,
    title: '离开测验？',
    message: '离开后本轮测验不会保留，确定离开吗？',
    confirmText: '离开',
    cancelText: '继续答题',
  }

  it('open=false 时不渲染弹窗', () => {
    const wrapper = mount(ConfirmDialog, { props: { ...baseProps, open: false } })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('open=true 渲染标题、正文与两个按钮', () => {
    const wrapper = mount(ConfirmDialog, { props: baseProps })
    expect(wrapper.text()).toContain('离开测验？')
    expect(wrapper.text()).toContain('离开后本轮测验不会保留')
    expect(wrapper.findAll('button')).toHaveLength(2)
    expect(wrapper.text()).toContain('继续答题')
    expect(wrapper.text()).toContain('离开')
  })

  it('点击「离开」只触发 confirm', async () => {
    const wrapper = mount(ConfirmDialog, { props: baseProps })
    const leaveBtn = wrapper.findAll('button').find((b) => b.text() === '离开')!
    await leaveBtn.trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('cancel')).toBeFalsy()
  })

  it('点击「继续答题」只触发 cancel', async () => {
    const wrapper = mount(ConfirmDialog, { props: baseProps })
    const stayBtn = wrapper.findAll('button').find((b) => b.text() === '继续答题')!
    await stayBtn.trigger('click')
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('confirm')).toBeFalsy()
  })

  it('具备对话框语义与足够触控区域', () => {
    const wrapper = mount(ConfirmDialog, { props: baseProps })
    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('aria-modal')).toBe('true')
    for (const b of wrapper.findAll('button')) {
      expect(b.classes().some((c) => c.includes('min-h'))).toBe(true)
    }
  })
})
