import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import '../styles/modulus.css'

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const next = searchParams.get('next')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user?.authenticated) {
    const destination = next || (user.role === 'MODERATOR' || user.role === 'ADMIN' ? '/moderation' : '/postings')
    return <Navigate to={destination} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(username, password)
      navigate(next || '/')
    } catch {
      setError('Invalid username or password.')
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
          <span className="m-eyebrow">WELCOME BACK</span>
          <h1>Log in</h1>
          <p className="m-auth-sub">Continue to the submitter portal or moderator console.</p>
          <form onSubmit={handleSubmit} className="m-auth-form">
            {error && <div className="m-auth-error">{error}</div>}
            <div className="m-field">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                required
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="m-field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button type="submit" disabled={submitting} className="m-btn m-btn-solid m-btn-block">
              {submitting ? 'Signing in…' : 'Log in'}
            </button>
          </form>
          <div className="m-auth-switch">
            New to Modulus? <Link to={next ? `/signup?next=${encodeURIComponent(next)}` : '/signup'}>Create an account</Link>
          </div>
          <div className="m-auth-demo">
            demo accounts (seed_demo): demo_employer / demo_moderator / demo_admin
            <br />
            password: password123!
          </div>
        </div>
      </div>
    </div>
  )
}
