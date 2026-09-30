/** 音效事件 ↔ 台词 ↔ 音源文件 的映射表（004-sound-effects）。

本文件是"台词"的唯一事实来源：想换某句话，只改这里的 `text` 并重新生成音源
（`backend/scripts/generate_sound_assets.py`），触发逻辑、开关与音量都不受影响。

事件清单之外的一切交互（翻页、进入专项练习页、导航、普通按钮、登录注册等）
都不发声 —— 见 spec FR-011。
*/

export type SoundEvent =
  | 'page.home'
  | 'page.study'
  | 'page.quiz'
  | 'page.wrong'
  | 'page.summary'
  | 'quiz.start'
  | 'streak.1'
  | 'streak.2'
  | 'streak.3'
  | 'streak.4'
  | 'streak.5'
  | 'streak.6'
  | 'streak.7'
  | 'streak.8'
  | 'streak.9'
  | 'streak.10'
  | 'streak.extend'
  | 'answer.wrong'

export interface SoundEventDef {
  event: SoundEvent
  text: string
  file: string
}

export const SOUND_EVENTS: readonly SoundEventDef[] = [
  { event: 'page.home', text: 'Stick together, team.', file: 'page_home.mp3' },
  { event: 'page.study', text: "OK, let's go!", file: 'page_study.mp3' },
  { event: 'page.quiz', text: 'Fire in the hole!', file: 'page_quiz.mp3' },
  { event: 'page.wrong', text: 'Bombs on the ground here.', file: 'page_wrong.mp3' },
  { event: 'page.summary', text: 'Keep going and stay strong, team.', file: 'page_summary.mp3' },
  { event: 'quiz.start', text: 'Come get some!', file: 'quiz_start.mp3' },
  { event: 'streak.1', text: 'First blood', file: 'streak_1.mp3' },
  { event: 'streak.2', text: 'Double kill', file: 'streak_2.mp3' },
  { event: 'streak.3', text: 'Triple kill', file: 'streak_3.mp3' },
  { event: 'streak.4', text: 'Quadra kill', file: 'streak_4.mp3' },
  { event: 'streak.5', text: 'Penta kill', file: 'streak_5.mp3' },
  { event: 'streak.6', text: 'Hexa kill', file: 'streak_6.mp3' },
  { event: 'streak.7', text: 'Hepta kill', file: 'streak_7.mp3' },
  { event: 'streak.8', text: 'Octa kill', file: 'streak_8.mp3' },
  { event: 'streak.9', text: 'Nona kill', file: 'streak_9.mp3' },
  { event: 'streak.10', text: 'Deca kill', file: 'streak_10.mp3' },
  { event: 'streak.extend', text: 'Good job', file: 'streak_extend.mp3' },
  { event: 'answer.wrong', text: 'Storm the front.', file: 'answer_wrong.mp3' },
]

const FILE_BY_EVENT = new Map<SoundEvent, string>(
  SOUND_EVENTS.map((item) => [item.event, item.file]),
)

/** 音源文件名。 */
export function soundFile(event: SoundEvent): string {
  return FILE_BY_EVENT.get(event) ?? ''
}

/** 音源播放地址：站点同域的静态资源，不向第三方请求（FR-022）。 */
export function soundUrl(event: SoundEvent): string {
  const base = (import.meta.env?.BASE_URL as string | undefined) ?? '/'
  return `${base.endsWith('/') ? base : `${base}/`}sounds/${soundFile(event)}`
}
