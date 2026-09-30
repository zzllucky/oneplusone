/** 音效偏好：默认关闭、本机持久化、非法值回退。 */

import { describe, expect, it } from 'vitest'

import {
  DEFAULT_SOUND_PREFERENCES,
  SOUND_PREF_KEY,
  loadSoundPreferences,
  saveSoundPreferences,
  setSoundEnabled,
  setSoundVolume,
} from '@/sounds/soundEffects'

describe('音效偏好', () => {
  it('未设置时返回默认：关闭、音量 70', () => {
    expect(loadSoundPreferences()).toEqual({ enabled: false, volume: 70 })
    expect(DEFAULT_SOUND_PREFERENCES.enabled).toBe(false)
  })

  it('写入后可从 localStorage 读回', () => {
    saveSoundPreferences({ enabled: true, volume: 40 })
    const raw = localStorage.getItem(SOUND_PREF_KEY)
    expect(raw).toBeTruthy()
    expect(JSON.parse(raw as string)).toEqual({ enabled: true, volume: 40 })
    expect(loadSoundPreferences()).toEqual({ enabled: true, volume: 40 })
  })

  it('开关与音量可分别更新', () => {
    setSoundEnabled(true)
    expect(loadSoundPreferences().enabled).toBe(true)
    setSoundVolume(90)
    expect(loadSoundPreferences()).toEqual({ enabled: true, volume: 90 })
  })

  it('损坏的 JSON 回退默认值且不抛错', () => {
    localStorage.setItem(SOUND_PREF_KEY, '{not-json')
    expect(loadSoundPreferences()).toEqual({ enabled: false, volume: 70 })
  })

  it('字段类型错误回退默认值', () => {
    localStorage.setItem(SOUND_PREF_KEY, JSON.stringify({ enabled: 'yes', volume: 'loud' }))
    expect(loadSoundPreferences()).toEqual({ enabled: false, volume: 70 })
  })

  it('音量越界或非数字回退为 70', () => {
    localStorage.setItem(SOUND_PREF_KEY, JSON.stringify({ enabled: true, volume: 500 }))
    expect(loadSoundPreferences().volume).toBe(70)
    localStorage.setItem(SOUND_PREF_KEY, JSON.stringify({ enabled: true, volume: -1 }))
    expect(loadSoundPreferences().volume).toBe(70)
    localStorage.setItem(SOUND_PREF_KEY, JSON.stringify({ enabled: true, volume: null }))
    expect(loadSoundPreferences().volume).toBe(70)
  })

  it('音量为 0 时开关仍可保持开启', () => {
    saveSoundPreferences({ enabled: true, volume: 0 })
    const prefs = loadSoundPreferences()
    expect(prefs.enabled).toBe(true)
    expect(prefs.volume).toBe(0)
  })
})
