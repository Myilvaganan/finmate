import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authService, type User } from '@/services/authService'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('finmate_token')
    if (!token) {
      setLoading(false)
      return
    }
    authService
      .me()
      .then(setUser)
      .catch(() => localStorage.removeItem('finmate_token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const { token, user } = await authService.login(email, password)
    localStorage.setItem('finmate_token', token)
    setUser(user)
  }

  const signup = async (email: string, password: string, fullName: string) => {
    const { token, user } = await authService.signup(email, password, fullName)
    localStorage.setItem('finmate_token', token)
    setUser(user)
  }

  const logout = () => {
    localStorage.removeItem('finmate_token')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
