import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { auth } from '../api/client'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // The CSRF cookie has to exist before any POST (login included) will
    // be accepted, so fetch it once up front alongside the session check.
    auth
      .csrf()
      .then(() => auth.me())
      .then(setUser)
      .catch(() => setUser({ authenticated: false }))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const loggedInUser = await auth.login(username, password)
    setUser({ ...loggedInUser, authenticated: true })
  }, [])

  const logout = useCallback(async () => {
    await auth.logout()
    setUser({ authenticated: false })
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
