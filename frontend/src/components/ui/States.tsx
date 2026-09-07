import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted">
      <Loader2 className="animate-spin" size={22} />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-[color:var(--color-negative)]">
      <AlertTriangle size={22} />
      <span className="text-sm">{message}</span>
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
      <Inbox size={28} className="text-muted" />
      <div className="font-medium">{title}</div>
      {description && <div className="text-sm text-muted max-w-sm">{description}</div>}
      {action}
    </div>
  )
}
