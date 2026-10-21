import { get, post } from './client'

export type GrammarStatus = 'not_started' | 'learning' | 'mastered'
export type GrammarCardType = 'rule' | 'contrast' | 'memorize'
export type GrammarLevel = 'L1' | 'L2' | 'L3'

export interface GrammarOption {
  key: string
  text: string
}

export interface GrammarQuestion {
  question_id: string
  level: string
  stem: string
  options: GrammarOption[]
}

export interface GrammarPointItem {
  id: string
  title: string
  depth: string
  card_type: GrammarCardType
  status: GrammarStatus
  has_wrong: boolean
  question_count: number
}

export interface GrammarOutlineModule {
  module: string
  module_name: string
  points: GrammarPointItem[]
}

export interface GrammarOutlineResponse {
  total_points: number
  mastered_count: number
  wrong_count: number
  modules: GrammarOutlineModule[]
}

export interface GrammarPointDetail {
  id: string
  module: string
  module_name: string
  title: string
  depth: string
  card_type: GrammarCardType
  status: GrammarStatus
  has_wrong: boolean
}

export interface GrammarPointDetailResponse {
  point: GrammarPointDetail
  /** 教研内容（服务端已清洗答案），按 card_type 渲染 */
  payload: Record<string, unknown>
  check_questions: GrammarQuestion[]
}

export interface GrammarViewResponse {
  point_id: string
  status: GrammarStatus
  studied_at: string | null
}

export interface GrammarGuessResponse {
  point_id: string
  choice_key: string
  feedback: string
}

export interface AttemptStartResponse {
  attempt_id: number
  source: 'card' | 'bank'
  point_id: string
  questions: GrammarQuestion[]
}

export interface GrammarAttemptProgress {
  total_count: number
  answered_count: number
  correct_count: number
  wrong_count: number
}

export interface GrammarAnswerResponse {
  question_id: string
  is_correct: boolean
  correct_key: string
  explanation: string
  feedback: string | null
  attempt: GrammarAttemptProgress
  added_to_wrong_points: boolean
  removed_from_wrong_points: boolean
  correct_streak: number
}

export interface GrammarFinishResponse {
  attempt_id: number
  source: 'card' | 'bank'
  point_id: string
  total_count: number
  correct_count: number
  wrong_count: number
  accuracy: number
  duration_seconds: number
  mastered: boolean
  status: GrammarStatus
}

export interface GrammarWrongPointItem {
  point_id: string
  title: string
  module: string
  module_name: string
  wrong_count: number
  correct_streak: number
  added_at: string
  last_wrong_at: string
}

export interface GrammarWrongPointListResponse {
  total: number
  items: GrammarWrongPointItem[]
}

export function getOutline(): Promise<GrammarOutlineResponse> {
  return get<GrammarOutlineResponse>('/api/grammar/outline')
}

export function getPoint(pointId: string): Promise<GrammarPointDetailResponse> {
  return get<GrammarPointDetailResponse>(`/api/grammar/points/${pointId}`)
}

export function viewPoint(pointId: string): Promise<GrammarViewResponse> {
  return post<GrammarViewResponse>(`/api/grammar/points/${pointId}/view`, {})
}

/** 提交"猜一猜"所选选项，取服务端返回的针对性反馈（作答后下发，不泄露答案） */
export function guessPoint(pointId: string, choiceKey: string): Promise<GrammarGuessResponse> {
  return post<GrammarGuessResponse>(`/api/grammar/points/${pointId}/guess`, {
    choice_key: choiceKey,
  })
}

export function startCheck(pointId: string): Promise<AttemptStartResponse> {
  return post<AttemptStartResponse>(`/api/grammar/points/${pointId}/check/start`, {})
}

export function startPractice(
  pointId: string,
  level?: GrammarLevel | null,
): Promise<AttemptStartResponse> {
  return post<AttemptStartResponse>(`/api/grammar/points/${pointId}/practice/start`, {
    level: level ?? null,
  })
}

export function answerGrammarQuestion(
  attemptId: number,
  questionId: string,
  choiceKey: string,
): Promise<GrammarAnswerResponse> {
  return post<GrammarAnswerResponse>(`/api/grammar/attempts/${attemptId}/answer`, {
    question_id: questionId,
    choice_key: choiceKey,
  })
}

export function finishGrammarAttempt(attemptId: number): Promise<GrammarFinishResponse> {
  return post<GrammarFinishResponse>(`/api/grammar/attempts/${attemptId}/finish`, {})
}

export function getWrongPoints(): Promise<GrammarWrongPointListResponse> {
  return get<GrammarWrongPointListResponse>('/api/grammar/wrong-points')
}
