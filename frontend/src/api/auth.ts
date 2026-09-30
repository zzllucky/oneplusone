import { post, get } from './client'

export interface UserOut {
  id: number
  login_name: string
  nickname: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}

export interface MeResponse extends UserOut {
  daily_goal: number
}

export function register(payload: {
  login_name: string
  nickname: string
  password: string
}): Promise<TokenResponse> {
  return post<TokenResponse>('/api/auth/register', payload)
}

export function login(payload: {
  login_name: string
  password: string
}): Promise<TokenResponse> {
  return post<TokenResponse>('/api/auth/login', payload)
}

export function fetchMe(): Promise<MeResponse> {
  return get<MeResponse>('/api/auth/me')
}
