import { StatusBadge } from '../components/StatusBadge'
import { useHealthCheck } from '../hooks/useHealthCheck'

// Phase 0 scaffold page: proves the full docker-compose stack is wired
// together (frontend -> backend /healthz/). Replaced by the submitter
// portal and moderator console routes starting in Phase 5.
export function StatusPage() {
  const status = useHealthCheck()

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">Content Moderation Pipeline</h1>
      <p className="text-slate-600">Scaffold is up. This page will become the submitter portal and moderator console.</p>
      <StatusBadge status={status} />
    </main>
  )
}
