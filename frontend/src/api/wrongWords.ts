import { get } from './client'

export interface WrongWordItem {
  word_id: number
  spelling: string
  meaning_zh: string
  phrase: string | null
  phonetic: string | null
  added_at: string
  /** 累计答错次数 */
  wrong_count: number
  /** 当前连续答对次数（达到 2 次即移出错题本） */
  correct_streak: number
}

export interface WrongWordListResponse {
  total: number
  page: number
  page_size: number
  items: WrongWordItem[]
}

export interface WrongArchiveItem {
  word_id: number
  spelling: string
  meaning_zh: string
  phrase: string | null
  phonetic: string | null
  /** 累计答错次数（永久档案，不记录时间） */
  wrong_count: number
}

export interface WrongArchiveListResponse {
  total: number
  page: number
  page_size: number
  sort: string
  items: WrongArchiveItem[]
}

export type ArchiveSort = 'added' | 'count'

export function fetchWrongWords(
  page = 1,
  pageSize = 100,
): Promise<WrongWordListResponse> {
  return get<WrongWordListResponse>(
    `/api/wrong-words?page=${page}&page_size=${pageSize}`,
  )
}

export function fetchWrongWordArchive(
  page = 1,
  pageSize = 100,
  sort: ArchiveSort = 'added',
): Promise<WrongArchiveListResponse> {
  return get<WrongArchiveListResponse>(
    `/api/wrong-words/archive?page=${page}&page_size=${pageSize}&sort=${sort}`,
  )
}
