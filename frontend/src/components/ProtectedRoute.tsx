import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import type { ReactNode } from 'react'

export function ProtectedRoute({
  children,
  requireModerator = false,
}: {
  children: ReactNode
  requireModerator?: boolean
}) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="p-6 text-slate-500">Loading…</div>
  }
  if (!user?.authenticated) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  if (requireModerator && user.role !== 'MODERATOR' && user.role !== 'ADMIN') {
    return <Navigate to="/postings" replace />
  }
  return <>{children}</>
}
