/** 连对播报与播放行为：覆盖播放、默认静音、发音优先、失败静默。

播放用 mock 的 HTMLMediaElement，测试不真的出声。
*/

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/composables/useAudioWarmup', () => ({
  isPronouncing: vi.fn(() => false),
}))

import { isPronouncing } from '@/composables/useAudioWarmup'
import {
  __resetSoundState,
  getStreakCount,
  onCorrect,
  onWrong,
  playQuizStart,
  playSound,
  resolveStreakEvent,
  setSoundEnabled,
} from '@/sounds/soundEffects'

const mockedIsPronouncing = vi.mocked(isPronouncing)

function spyPlayback() {
  const play = vi
    .spyOn(HTMLMediaElement.prototype, 'play')
    .mockResolvedValue(undefined as unknown as void)
  const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
  return { play, pause }
}

describe('连对播报', () => {
  beforeEach(() => {
    __resetSoundState()
    setSoundEnabled(true)
    spyPlayback()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('连对 1–10 依次解析为连杀台词', () => {
    expect(resolveStreakEvent(1)).toBe('streak.1')
    expect(resolveStreakEvent(5)).toBe('streak.5')
    expect(resolveStreakEvent(10)).toBe('streak.10')
  })

  it('连对超过 10 后固定为 Good job', () => {
    expect(resolveStreakEvent(11)).toBe('streak.extend')
    expect(resolveStreakEvent(99)).toBe('streak.extend')
  })

  it('连续答对依次播放对应连杀音', () => {
    expect(onCorrect()).toBe('streak.1')
    expect(onCorrect()).toBe('streak.2')
    expect(getStreakCount()).toBe(2)
    onCorrect()
    expect(onCorrect()).toBe('streak.4')
  })

  it('答错播 Storm the front. 并让连对归零', () => {
    onCorrect()
    onCorrect()
    onWrong()
    expect(getStreakCount()).toBe(0)
    expect(onCorrect()).toBe('streak.1')
  })

  it('点击开始时归零并播开始语音', () => {
    onCorrect()
    onCorrect()
    playQuizStart()
    expect(getStreakCount()).toBe(0)
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
  })
})

describe('播放行为', () => {
  beforeEach(() => {
    __resetSoundState()
    spyPlayback()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    mockedIsPronouncing.mockReturnValue(false)
  })

  it('默认关闭时不发声', () => {
    expect(playSound('streak.1')).toBe(false)
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled()
  })

  it('连续播放时先暂停再换源，不排队叠加', () => {
    setSoundEnabled(true)
    playSound('streak.1')
    playSound('streak.2')
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(2)
  })

  it('单词发音进行中时跳过本次音效，且不补播', () => {
    setSoundEnabled(true)
    mockedIsPronouncing.mockReturnValue(true)
    expect(playSound('streak.1')).toBe(false)
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled()
  })

  it('播放失败时静默降级，仅告警不抛错', async () => {
    setSoundEnabled(true)
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockRejectedValue(new Error('blocked'))
    expect(() => playSound('streak.1')).not.toThrow()
    await Promise.resolve()
    expect(warn).toHaveBeenCalled()
  })
})
