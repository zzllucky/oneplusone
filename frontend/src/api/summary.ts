import { get } from './client'

export type CalendarLevel = 'gray' | 'light' | 'deep'

export interface CalendarDay {
  date: string
  level: CalendarLevel
  /** 深绿分档：0 = 非深绿；1 = 1–9 词；2 = 10–29 词；3 = ≥30 词 */
  shade: number
  learned_count: number
}

export interface PracticeStat {
  rounds: number
  answered: number
  correct: number
  wrong: number
}

export interface MonthTotal {
  learned_words: number
  quiz: PracticeStat
  review_practice: PracticeStat
  archive_practice: PracticeStat
  active_days: number
}

export interface MonthSummary {
  month: string
  today: string
  days: CalendarDay[]
  month_total: MonthTotal
  streak_days: number
}

export interface DaySummary {
  date: string
  has_record: boolean
  learned_count: number
  quiz: PracticeStat & { completed: boolean }
  review_practice: PracticeStat
  archive_practice: PracticeStat
}

export function getMonthSummary(month?: string): Promise<MonthSummary> {
  const query = month ? `?month=${encodeURIComponent(month)}` : ''
  return get<MonthSummary>(`/api/summary/month${query}`)
}

export function getDaySummary(date: string): Promise<DaySummary> {
  return get<DaySummary>(`/api/summary/day?date=${encodeURIComponent(date)}`)
}
