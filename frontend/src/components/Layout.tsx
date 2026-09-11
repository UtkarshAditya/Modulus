import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isModerator = user?.role === 'MODERATOR' || user?.role === 'ADMIN'

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-semibold text-slate-900">
            Content Moderation Pipeline
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {!isModerator && (
              <Link to="/postings" className="text-slate-600 hover:text-slate-900">
                My postings
              </Link>
            )}
            {isModerator && (
              <Link to="/moderation" className="text-slate-600 hover:text-slate-900">
                Queue
              </Link>
            )}
            {user?.authenticated && (
              <>
                <span className="text-slate-400">{user.username}</span>
                <button
                  onClick={handleLogout}
                  className="rounded-md border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-100"
                >
                  Log out
                </button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
