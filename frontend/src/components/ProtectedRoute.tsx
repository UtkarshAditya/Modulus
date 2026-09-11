import { Navigate } from 'react-router-dom'
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

  if (loading) {
    return <div className="p-6 text-slate-500">Loading…</div>
  }
  if (!user?.authenticated) {
    return <Navigate to="/login" replace />
  }
  if (requireModerator && user.role !== 'MODERATOR' && user.role !== 'ADMIN') {
    return <Navigate to="/postings" replace />
  }
  return <>{children}</>
}
