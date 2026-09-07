import { AlertTriangle } from 'lucide-react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  danger?: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open, title, description, confirmLabel = 'Confirm', danger = true, loading, onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onCancel}>
      <div className="surface rounded-2xl max-w-sm w-full p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3 mb-2">
          <span
            className="h-9 w-9 rounded-full flex items-center justify-center shrink-0"
            style={{
              background: danger ? 'color-mix(in srgb, var(--color-negative) 12%, transparent)' : 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
              color: danger ? 'var(--color-negative)' : 'var(--color-accent)',
            }}
          >
            <AlertTriangle size={18} />
          </span>
          <h2 className="text-base font-semibold pt-1.5">{title}</h2>
        </div>
        <p className="text-sm text-muted mb-5">{description}</p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg border border-default text-sm">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 ${
              danger ? 'bg-[color:var(--color-negative)]' : 'bg-[color:var(--color-accent)]'
            }`}
          >
            {loading ? 'Please wait…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
