const TOKEN_KEY = 'word-study-token'

export class ApiError extends Error {
  code: string
  status: number

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

function redirectToLogin(): void {
  clearToken()
  const target = window.location.pathname + window.location.search
  window.location.href = `/login?redirect=${encodeURIComponent(target)}`
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(path, { ...options, headers })
  } catch (error) {
    throw new ApiError(0, 'network_error', '网络异常，请稍后再试')
  }

  if (response.status === 401) {
    redirectToLogin()
    throw new ApiError(401, 'unauthorized', '请先登录')
  }

  const text = await response.text()
  const payload = text ? JSON.parse(text) : null

  if (!response.ok) {
    const error = payload?.error ?? {}
    throw new ApiError(response.status, error.code ?? 'unknown', error.message ?? '请求失败')
  }

  return payload as T
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) })
}

export async function fetchAudio(path: string): Promise<Blob> {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(path, { headers })
  if (!response.ok) {
    throw new ApiError(response.status, 'pronunciation_unavailable', '暂无发音')
  }
  return await response.blob()
}
