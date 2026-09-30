/** 设置页音效开关与音量：默认关闭、即时写入本机偏好。 */

import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api/settings', () => ({
  fetchSettings: vi.fn(async () => ({ daily_goal: 20 })),
  updateSettings: vi.fn(async () => ({ daily_goal: 20 })),
}))

import { loadSoundPreferences } from '@/sounds/soundEffects'
import SettingsPage from '@/pages/SettingsPage.vue'

async function mountPage() {
  const wrapper = mount(SettingsPage)
  await flushPromises()
  return wrapper
}

describe('设置页音效', () => {
  it('首次进入展示为关闭、音量 70', async () => {
    const wrapper = await mountPage()
    const checkbox = wrapper.find('input[type="checkbox"]')
    const range = wrapper.find('input[type="range"]')

    expect(checkbox.exists()).toBe(true)
    expect((checkbox.element as HTMLInputElement).checked).toBe(false)
    expect((range.element as HTMLInputElement).value).toBe('70')
    expect(loadSoundPreferences()).toEqual({ enabled: false, volume: 70 })
  })

  it('打开开关即时写入本机偏好', async () => {
    const wrapper = await mountPage()
    await wrapper.find('input[type="checkbox"]').setValue(true)

    const prefs = loadSoundPreferences()
    expect(prefs.enabled).toBe(true)
    expect(prefs.volume).toBe(70)
  })

  it('调整音量即时写入本机偏好', async () => {
    const wrapper = await mountPage()
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('input[type="range"]').setValue(40)

    expect(loadSoundPreferences()).toEqual({ enabled: true, volume: 40 })
  })

  it('偏好已存在时按本机值展示', async () => {
    localStorage.setItem('word-study-sound-prefs', JSON.stringify({ enabled: true, volume: 30 }))
    const wrapper = await mountPage()

    expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.find('input[type="range"]').element as HTMLInputElement).value).toBe('30')
  })
})
