/** 页面进入语音：仅白名单路径发声，专项练习页进入无声，重复进入去重。 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { __resetSoundState, playPageSound, setSoundEnabled } from '@/sounds/soundEffects'

describe('页面进入语音白名单', () => {
  beforeEach(() => {
    __resetSoundState()
    setSoundEnabled(true)
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined as unknown as void)
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  })

  it('五个学习页面各播一次对应语音', () => {
    expect(playPageSound('/home')).toBe(true)
    expect(playPageSound('/study')).toBe(true)
    expect(playPageSound('/quiz')).toBe(true)
    expect(playPageSound('/wrong-words')).toBe(true)
    expect(playPageSound('/summary')).toBe(true)
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(5)
  })

  it('专项练习页与其他路径进入时不发声', () => {
    expect(playPageSound('/review')).toBe(false)
    expect(playPageSound('/archive')).toBe(false)
    expect(playPageSound('/settings')).toBe(false)
    expect(playPageSound('/login')).toBe(false)
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled()
  })

  it('同一路径极短时间内重复进入只播一次', () => {
    expect(playPageSound('/quiz')).toBe(true)
    expect(playPageSound('/quiz')).toBe(false)
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1)
  })
})
