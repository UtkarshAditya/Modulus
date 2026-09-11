import type {
  CasePosting,
  Decision,
  Flag,
  JobPosting,
  JobPostingInput,
  QueueRow,
  User,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Django sets this cookie once /api/auth/csrf/ (or any GET) has been hit;
// we read it back out to satisfy CSRF protection on POST/PATCH.
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, body: unknown) {
    const detail =
      typeof body === 'object' && body !== null && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${status}`
    super(detail)
    this.status = status
    this.body = body
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (method !== 'GET') {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) headers['X-CSRFToken'] = csrfToken
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })

  if (response.status === 204) return undefined as T

  const contentType = response.headers.get('content-type') ?? ''
  const data = contentType.includes('application/json') ? await response.json() : undefined

  if (!response.ok) throw new ApiError(response.status, data)
  return data as T
}

export { ApiError }

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/healthz/`)
  if (!response.ok) throw new Error(`Health check failed with status ${response.status}`)
  return response.json()
}

// --- auth --------------------------------------------------------------

export const auth = {
  csrf: () => request<{ detail: string }>('/api/auth/csrf/'),
  me: () => request<User>('/api/auth/me/'),
  login: (username: string, password: string) =>
    request<User>('/api/auth/login/', { method: 'POST', body: { username, password } }),
  logout: () => request<void>('/api/auth/logout/', { method: 'POST' }),
}

// --- postings (submitter) -----------------------------------------------

export const postings = {
  list: () => request<JobPosting[]>('/api/postings/'),
  retrieve: (id: number) => request<JobPosting>(`/api/postings/${id}/`),
  create: (input: JobPostingInput) =>
    request<JobPosting>('/api/postings/', { method: 'POST', body: input }),
  update: (id: number, input: Partial<JobPostingInput>) =>
    request<JobPosting>(`/api/postings/${id}/`, { method: 'PATCH', body: input }),
}

// --- moderation ----------------------------------------------------------

export interface QueueFilters {
  category?: string
  severity?: string
  min_score?: number
  max_score?: number
  ordering?: string
}

function toQueryString(filters: QueueFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const moderation = {
  queue: (filters: QueueFilters = {}) =>
    request<QueueRow[]>(`/api/moderation/queue/${toQueryString(filters)}`),
  claim: (id: number) =>
    request<{ expires_at: string }>(`/api/moderation/queue/${id}/claim/`, { method: 'POST' }),
  release: (id: number) =>
    request<void>(`/api/moderation/queue/${id}/release/`, { method: 'POST' }),
  caseDetail: (id: number) => request<CasePosting>(`/api/moderation/postings/${id}/`),
  decide: (id: number, action: string, reasonCode: string, notes: string) =>
    request<Decision>(`/api/moderation/postings/${id}/decide/`, {
      method: 'POST',
      body: { action, reason_code: reasonCode, notes },
    }),
  markFalsePositive: (flagId: number) =>
    request<Flag>(`/api/moderation/flags/${flagId}/false-positive/`, { method: 'POST' }),
}
