import { get, post } from './client'
import type { RoundProgress } from './home'

export interface StudyWordItem {
  word_id: number
  spelling: string
  meaning_zh: string
  phrase: string | null
  phonetic: string | null
  order_index: number
  viewed_at: string | null
}

export interface TodayStudyResponse {
  study_date: string
  total_count: number
  viewed_count: number
  all_viewed: boolean
  quiz_unlocked: boolean
  library_exhausted: boolean
  items: StudyWordItem[]
  /** 当前轮次与进度（缺失时为 null / undefined，前端不渲染轮次区） */
  round?: RoundProgress | null
}

export interface ViewWordResponse {
  word_id: number
  viewed_count: number
  total_count: number
  all_viewed: boolean
  quiz_unlocked: boolean
}

export function fetchTodayStudy(): Promise<TodayStudyResponse> {
  return get<TodayStudyResponse>('/api/study/today')
}

export function markWordViewed(wordId: number): Promise<ViewWordResponse> {
  return post<ViewWordResponse>(`/api/study/today/items/${wordId}/view`)
}
