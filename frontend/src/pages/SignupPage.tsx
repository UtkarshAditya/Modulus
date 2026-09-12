import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import '../styles/modulus.css'

function firstFieldError(body: unknown, field: string): string | null {
  if (typeof body !== 'object' || body === null) return null
  const value = (body as Record<string, unknown>)[field]
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return null
}

export function SignupPage() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const next = searchParams.get('next')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ username?: string; email?: string; password?: string; general?: string }>({})
  const [submitting, setSubmitting] = useState(false)

  if (user?.authenticated) {
    return <Navigate to={next || '/postings'} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})
    try {
      await signup(username, email, password)
      navigate(next || '/postings')
    } catch (err) {
      if (err instanceof ApiError && typeof err.body === 'object' && err.body !== null) {
        setErrors({
          username: firstFieldError(err.body, 'username') ?? undefined,
          email: firstFieldError(err.body, 'email') ?? undefined,
          password: firstFieldError(err.body, 'password') ?? undefined,
        })
      } else {
        setErrors({ general: 'Something went wrong. Please try again.' })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modulus-page m-auth-shell">
      <header className="m-nav">
        <Link to="/" className="m-wordmark">
          <span className="m-bar">|</span>MODULUS<span className="m-bar">|</span>
        </Link>
      </header>
      <div className="m-auth-main">
        <div className="m-auth-card">
          <span className="m-eyebrow">GET STARTED</span>
          <h1>Create your account</h1>
          <p className="m-auth-sub">Post a job today — it's auto‑analyzed the moment you submit it.</p>
          <form onSubmit={handleSubmit} className="m-auth-form" noValidate>
            {errors.general && <div className="m-auth-error">{errors.general}</div>}
            <div className="m-field">
              <label htmlFor="signup-username">Username</label>
              <input
                id="signup-username"
                required
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              {errors.username && <div className="m-field-hint" style={{ color: 'var(--m-critical)' }}>{errors.username}</div>}
            </div>
            <div className="m-field">
              <label htmlFor="signup-email">Work email</label>
              <input
                id="signup-email"
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              {errors.email && <div className="m-field-hint" style={{ color: 'var(--m-critical)' }}>{errors.email}</div>}
            </div>
            <div className="m-field">
              <label htmlFor="signup-password">Password</label>
              <input
                id="signup-password"
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {errors.password ? (
                <div className="m-field-hint" style={{ color: 'var(--m-critical)' }}>{errors.password}</div>
              ) : (
                <div className="m-field-hint">At least 8 characters, not too common or all-numeric.</div>
              )}
            </div>
            <button type="submit" disabled={submitting} className="m-btn m-btn-solid m-btn-block">
              {submitting ? 'Creating account…' : 'Create free account'}
            </button>
          </form>
          <div className="m-auth-switch">
            Already have an account?{' '}
            <Link to={next ? `/login?next=${encodeURIComponent(next)}` : '/login'}>Log in</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
