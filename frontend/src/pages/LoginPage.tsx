import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user?.authenticated) {
    const destination = user.role === 'MODERATOR' || user.role === 'ADMIN' ? '/moderation' : '/postings'
    return <Navigate to={destination} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <h1 className="mb-1 text-xl font-semibold text-slate-900">Sign in</h1>
      <p className="mb-6 text-sm text-slate-500">
        Content moderation pipeline — submitter portal and moderator console.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>}
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Username</span>
          <input
            required
            autoFocus
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Password</span>
          <input
            required
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="text-center text-xs text-slate-400">
          Demo accounts (seed_demo): demo_employer / demo_moderator / demo_admin, password
          password123!
        </p>
      </form>
    </div>
  )
}
