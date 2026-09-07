import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { LoadingState } from '@/components/ui/States'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState label="Loading FinMate…" />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}
