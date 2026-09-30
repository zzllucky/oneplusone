/** 音源资产契约测试：事件映射 ↔ manifest 一致，单条时长与体积达标。

manifest 由 backend/scripts/generate_sound_assets.py 生成（写出文件后统计大小），
因此 bytes > 0 即证明该音源已落盘。
*/

import { describe, expect, it } from 'vitest'

import manifest from '../../public/sounds/manifest.json'
import { SOUND_EVENTS, soundFile, soundUrl, type SoundEvent } from '@/sounds/events'

// 契约（specs/004-sound-effects/contracts/sound-assets.md 第 3 节）
const EXPECTED_EVENTS: SoundEvent[] = [
  'page.home',
  'page.study',
  'page.quiz',
  'page.wrong',
  'page.summary',
  'quiz.start',
  'streak.1',
  'streak.2',
  'streak.3',
  'streak.4',
  'streak.5',
  'streak.6',
  'streak.7',
  'streak.8',
  'streak.9',
  'streak.10',
  'streak.extend',
  'answer.wrong',
]

// 阈值以 manifest 为准（自备音源可用 --max-duration-ms / --max-bytes 放宽）
const thresholds = manifest.thresholds
const maxDurationMs = thresholds?.max_duration_ms ?? 2000
const maxBytes = thresholds?.max_bytes ?? 30 * 1024

describe('音源资产契约', () => {
  it('映射覆盖契约中的 18 个事件，且无重复', () => {
    const events = SOUND_EVENTS.map((item) => item.event)
    expect([...events].sort()).toEqual([...EXPECTED_EVENTS].sort())
    expect(new Set(events).size).toBe(events.length)
  })

  it('与 manifest.json 的事件集合完全一致', () => {
    expect(SOUND_EVENTS.map((item) => item.event).sort()).toEqual(
      manifest.entries.map((item) => item.event).sort(),
    )
  })

  it('台词与契约逐字一致', () => {
    const byEvent = new Map(manifest.entries.map((item) => [item.event, item.text]))
    expect(byEvent.get('page.home')).toBe('Stick together, team.')
    expect(byEvent.get('page.study')).toBe("OK, let's go!")
    expect(byEvent.get('page.quiz')).toBe('Fire in the hole!')
    expect(byEvent.get('page.wrong')).toBe('Bombs on the ground here.')
    expect(byEvent.get('page.summary')).toBe('Keep going and stay strong, team.')
    expect(byEvent.get('quiz.start')).toBe('Come get some!')
    expect(byEvent.get('streak.1')).toBe('First blood')
    expect(byEvent.get('streak.10')).toBe('Deca kill')
    expect(byEvent.get('streak.extend')).toBe('Good job')
    expect(byEvent.get('answer.wrong')).toBe('Storm the front.')
  })

  it('每条音源都已落盘（体积大于 0）', () => {
    for (const entry of manifest.entries) {
      expect(entry.bytes, `${entry.event} 音源为空`).toBeGreaterThan(0)
      expect(soundFile(entry.event as SoundEvent)).toBe(entry.file)
    }
  })

  it('单条时长与体积不超过阈值', () => {
    for (const entry of manifest.entries) {
      expect(entry.duration_ms, `${entry.event} 时长超过 ${maxDurationMs}ms`).toBeLessThanOrEqual(
        maxDurationMs,
      )
      expect(entry.bytes, `${entry.event} 体积超过 ${maxBytes}B`).toBeLessThanOrEqual(maxBytes)
    }
  })

  it('播放地址指向同域静态资源', () => {
    expect(soundUrl('streak.1')).toContain('/sounds/streak_1.mp3')
  })
})
