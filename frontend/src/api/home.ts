import { get } from './client'

export interface HomeToday {
  study_date: string | null
  total_count: number
  viewed_count: number
  all_viewed: boolean
  quiz_unlocked: boolean
}

/** 当前轮次与进度（003 词库循环学习） */
export interface RoundProgress {
  round_no: number
  learned_count: number
  total_count: number
  /** 本轮单词已学完但当日测验未完成 → 该轮暂不计入已完成 */
  pending_quiz: boolean
}

export interface HomeSummary {
  user: { id: number; login_name: string; nickname: string }
  daily_goal: number
  today: HomeToday
  wrong_word_count: number
  archive_word_count?: number
  /** 已完成词库学习的轮数 */
  completed_rounds?: number
  /** 当前进行中轮次的进度（缺失时为 null / undefined，前端不渲染轮次区） */
  current_round?: RoundProgress | null
}

export function fetchHomeSummary(): Promise<HomeSummary> {
  return get<HomeSummary>('/api/home/summary')
}
