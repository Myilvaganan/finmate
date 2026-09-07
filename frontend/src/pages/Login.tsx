import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { BRAND } from '@/config/brand'
import type { ApiError } from '@/services/apiClient'
import logoMark from '@/assets/finmate-mark.png'

export function LoginPage() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('demo@finmate.app')
  const [password, setPassword] = useState('demopassword123')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, signup } = useAuth()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') await login(email, password)
      else await signup(email, password, fullName)
      navigate('/')
    } catch (err) {
      setError((err as ApiError).message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-bg)' }}>
      <div className="w-full max-w-sm surface rounded-2xl p-8">
        <div className="flex items-center gap-2 mb-6">
          <img src={logoMark} alt="" className="h-8 w-8 rounded-md object-cover" />
          <div>
            <div className="font-semibold leading-tight">{BRAND.name}</div>
            <div className="text-xs text-muted leading-tight">{BRAND.tagline}</div>
          </div>
        </div>
        <h1 className="text-lg font-semibold mb-1">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p className="text-sm text-muted mb-6">{mode === 'login' ? 'Sign in to view your financial dashboard.' : 'Start tracking your finances in minutes.'}</p>

        <form onSubmit={submit} className="space-y-3">
          {mode === 'signup' && (
            <input
              required value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name"
              className="w-full rounded-lg border border-default bg-transparent px-3 py-2 text-sm outline-none focus:border-[color:var(--color-accent)]"
            />
          )}
          <input
            required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
            className="w-full rounded-lg border border-default bg-transparent px-3 py-2 text-sm outline-none focus:border-[color:var(--color-accent)]"
          />
          <input
            required type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password"
            className="w-full rounded-lg border border-default bg-transparent px-3 py-2 text-sm outline-none focus:border-[color:var(--color-accent)]"
          />
          {error && <p className="text-sm text-[color:var(--color-negative)]">{error}</p>}
          <button
            disabled={loading} type="submit"
            className="w-full rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] py-2 text-sm font-medium disabled:opacity-60"
          >
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <button
          className="text-sm text-muted mt-4 w-full text-center hover:text-current"
          onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>

        {mode === 'login' && (
          <p className="text-xs text-muted mt-4 text-center">
            Demo credentials are pre-filled — click Sign in to explore FinMate with sample data.
          </p>
        )}
      </div>
    </div>
  )
}
