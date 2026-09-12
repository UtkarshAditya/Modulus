import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import '../styles/modulus.css'

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isModerator = user?.role === 'MODERATOR' || user?.role === 'ADMIN'

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="modulus-page" style={{ minHeight: '100vh' }}>
      <header className="m-app-header">
        <Link to="/" className="m-wordmark">
          <span className="m-bar">|</span>MODULUS<span className="m-bar">|</span>
        </Link>
        <nav className="m-app-nav">
          {!isModerator && (
            <NavLink to="/postings" className={({ isActive }) => (isActive ? 'is-active' : undefined)}>
              My postings
            </NavLink>
          )}
          {isModerator && (
            <NavLink to="/moderation" className={({ isActive }) => (isActive ? 'is-active' : undefined)}>
              Queue
            </NavLink>
          )}
          {user?.authenticated && (
            <>
              <span className="m-app-user">{user.username}</span>
              <button onClick={handleLogout} className="m-btn m-btn-ghost">
                Log out
              </button>
            </>
          )}
        </nav>
      </header>
      <main className="m-app-main">
        <Outlet />
      </main>
    </div>
  )
}
