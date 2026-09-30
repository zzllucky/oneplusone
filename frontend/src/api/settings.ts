import { get, put } from './client'

export interface SettingsOut {
  daily_goal: number
  updated_at: string
}

export function fetchSettings(): Promise<SettingsOut> {
  return get<SettingsOut>('/api/settings')
}

export function updateSettings(dailyGoal: number): Promise<SettingsOut> {
  return put<SettingsOut>('/api/settings', { daily_goal: dailyGoal })
}
