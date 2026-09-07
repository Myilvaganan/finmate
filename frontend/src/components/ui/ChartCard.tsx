import type { ReactNode } from 'react'

export function ChartCard({ title, subtitle, children, action }: { title: string; subtitle?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="surface rounded-xl p-5 flex flex-col gap-4 min-w-0">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="min-h-0">{children}</div>
    </div>
  )
}
