import { post } from './client'

export type QuestionType = 'en2zh' | 'zh2en'

export interface QuizQuestion {
  question_id: number
  word_id: number
  type: QuestionType
  prompt: string
  options: string[]
}

export interface QuizStartResponse {
  attempt_id: number
  questions: QuizQuestion[]
}

export interface DailyAnswerResponse {
  question_id: number
  is_correct: boolean
  correct_index: number
  added_to_wrong_words: boolean
}

export interface ReviewAnswerResponse {
  question_id: number
  is_correct: boolean
  correct_index: number
  removed_from_wrong_words: boolean
  /** 未达移出阈值时的当前连续答对次数；已移出为 0 */
  correct_streak?: number
  added_back_to_wrong_words?: boolean
}

export interface ArchiveAnswerResponse {
  question_id: number
  is_correct: boolean
  correct_index: number
  /** 错题库永不移除，恒为 false */
  removed_from_wrong_words: boolean
  /** 答错时该词是否新进入错题本 */
  added_to_wrong_words?: boolean
  /** 该词在错题库中的累计错误次数 */
  archive_wrong_count?: number
}

export interface ArchiveFinishResponse {
  attempt_id: number
  total_count: number
  correct_count: number
  wrong_count: number
  accuracy: number
  duration_seconds: number
  /** 错题库总量（不因练习减少） */
  archive_total: number
  remaining_wrong_count: number
}

export interface QuizFinishResponse {
  attempt_id: number
  total_count: number
  correct_count: number
  wrong_count: number
  accuracy: number
  duration_seconds: number
  new_wrong_words: number[]
}

export interface ReviewFinishResponse {
  attempt_id: number
  total_count: number
  correct_count: number
  wrong_count: number
  accuracy: number
  duration_seconds: number
  remaining_wrong_count: number
}

export function startDailyQuiz(): Promise<QuizStartResponse> {
  return post<QuizStartResponse>('/api/quiz/today/start', {})
}

export function answerDaily(
  questionId: number,
  choiceIndex: number,
): Promise<DailyAnswerResponse> {
  return post<DailyAnswerResponse>('/api/quiz/today/answer', {
    question_id: questionId,
    choice_index: choiceIndex,
  })
}

export function finishDailyQuiz(): Promise<QuizFinishResponse> {
  return post<QuizFinishResponse>('/api/quiz/today/finish', {})
}

export function startReviewQuiz(): Promise<QuizStartResponse> {
  return post<QuizStartResponse>('/api/quiz/review/start', {})
}

export function answerReview(
  questionId: number,
  choiceIndex: number,
): Promise<ReviewAnswerResponse> {
  return post<ReviewAnswerResponse>('/api/quiz/review/answer', {
    question_id: questionId,
    choice_index: choiceIndex,
  })
}

export function finishReviewQuiz(): Promise<ReviewFinishResponse> {
  return post<ReviewFinishResponse>('/api/quiz/review/finish', {})
}

export function startArchiveQuiz(): Promise<QuizStartResponse> {
  return post<QuizStartResponse>('/api/quiz/archive/start', {})
}

export function answerArchive(
  questionId: number,
  choiceIndex: number,
): Promise<ArchiveAnswerResponse> {
  return post<ArchiveAnswerResponse>('/api/quiz/archive/answer', {
    question_id: questionId,
    choice_index: choiceIndex,
  })
}

export function finishArchiveQuiz(): Promise<ArchiveFinishResponse> {
  return post<ArchiveFinishResponse>('/api/quiz/archive/finish', {})
}
