/** 音效播放与偏好：播放、连对计数、开关与音量（004-sound-effects）。

职责边界：
- 只消费"答题结果"与"路径"，不存储任何学习数据，不采集播放行为（FR-023）
- 偏好只写本机 localStorage，不进账号（FR-024）
- 播放失败一律静默跳过，绝不打断学习流程（FR-027）

对外 API：playSound / playPageSound / playQuizStart / onCorrect / onWrong /
resetStreak / getStreakCount / resolveStreakEvent / 偏好读写。
*/

import { isPronouncing } from '@/composables/useAudioWarmup'
import { soundUrl, type SoundEvent } from '@/sounds/events'

export interface SoundPreferences {
  enabled: boolean
  volume: number
}

export const SOUND_PREF_KEY = 'word-study-sound-prefs'
export const DEFAULT_SOUND_PREFERENCES: SoundPreferences = { enabled: false, volume: 70 }

/** 同一页面语音的去重窗口（毫秒）：防止短时间内重复进入串成两声（FR-019）。 */
const PAGE_DEDUPE_MS = 800

const PAGE_SOUND_BY_PATH: Record<string, SoundEvent> = {
  '/home': 'page.home',
  '/study': 'page.study',
  '/quiz': 'page.quiz',
  '/wrong-words': 'page.wrong',
  '/summary': 'page.summary',
}

let streakCount = 0
let player: HTMLAudioElement | null = null
const lastPlayedAt = new Map<SoundEvent, number>()

/** 仅测试用：清空连对计数、播放记录与播放器。 */
export function __resetSoundState(): void {
  streakCount = 0
  lastPlayedAt.clear()
  player = null
}

function normalizeVolume(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return DEFAULT_SOUND_PREFERENCES.volume
  }
  const rounded = Math.round(value)
  if (rounded < 0 || rounded > 100) return DEFAULT_SOUND_PREFERENCES.volume
  return rounded
}

/** 读取偏好；缺失、损坏或字段非法均回退默认值，不抛错。 */
export function loadSoundPreferences(): SoundPreferences {
  try {
    const raw = localStorage.getItem(SOUND_PREF_KEY)
    if (!raw) return { ...DEFAULT_SOUND_PREFERENCES }
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return { ...DEFAULT_SOUND_PREFERENCES }
    const value = parsed as Partial<SoundPreferences>
    return { enabled: value.enabled === true, volume: normalizeVolume(value.volume) }
  } catch {
    return { ...DEFAULT_SOUND_PREFERENCES }
  }
}

export function saveSoundPreferences(preferences: SoundPreferences): void {
  localStorage.setItem(
    SOUND_PREF_KEY,
    JSON.stringify({
      enabled: preferences.enabled === true,
      volume: normalizeVolume(preferences.volume),
    }),
  )
}

export function setSoundEnabled(enabled: boolean): void {
  saveSoundPreferences({ ...loadSoundPreferences(), enabled })
}

export function setSoundVolume(volume: number): void {
  saveSoundPreferences({ ...loadSoundPreferences(), volume })
}

function getPlayer(): HTMLAudioElement {
  if (!player) {
    player = new Audio()
    player.preload = 'none'
  }
  return player
}

/**
 * 播放一条音效。后播覆盖先播（先暂停再换源），不排队叠加。
 * @returns 是否真的发声（关闭 / 发音中 / 去重窗口内 / 事件未知 都为 false）
 */
export function playSound(event: SoundEvent, options: { dedupeMs?: number } = {}): boolean {
  const preferences = loadSoundPreferences()
  if (!preferences.enabled) return false

  const now = Date.now()
  if (options.dedupeMs) {
    const last = lastPlayedAt.get(event)
    if (last !== undefined && now - last < options.dedupeMs) return false
  }

  // 单词发音优先：朗读进行中则跳过本次，不打断也不补播（FR-026）
  if (isPronouncing()) return false

  const url = soundUrl(event)
  if (!url) return false

  lastPlayedAt.set(event, now)
  const audio = getPlayer()
  audio.pause()
  audio.src = url
  audio.volume = preferences.volume / 100
  void audio.play().catch((error: unknown) => {
    console.warn('[sound] 音效播放失败，已静默跳过', error)
  })
  return true
}

/** 进入指定路径时播放对应页面语音；不在白名单（如 /review、/archive）则不发声。 */
export function playPageSound(path: string): boolean {
  const event = PAGE_SOUND_BY_PATH[path]
  if (!event) return false
  return playSound(event, { dedupeMs: PAGE_DEDUPE_MS })
}

/** 连对第 count 题应播的事件：1–10 为连杀台词，之后固定为 Good job。 */
export function resolveStreakEvent(count: number): SoundEvent {
  if (count >= 1 && count <= 10) {
    return `streak.${count}` as SoundEvent
  }
  return 'streak.extend'
}

export function getStreakCount(): number {
  return streakCount
}

/** 连对计数归零（用于"点击开始"）。 */
export function resetStreak(): void {
  streakCount = 0
}

/** 答对一题：连对 +1 并播报，返回本次事件。 */
export function onCorrect(): SoundEvent {
  streakCount += 1
  const event = resolveStreakEvent(streakCount)
  playSound(event)
  return event
}

/** 答错一题：播提示音并让连对归零。 */
export function onWrong(): void {
  streakCount = 0
  playSound('answer.wrong')
}

/** 点击"开始"：连对归零并播开始语音。 */
export function playQuizStart(): void {
  resetStreak()
  playSound('quiz.start')
}
