import { AlertCircle, CheckCircle2, Info, TrendingUp } from 'lucide-react'

const SEVERITY_STYLE: Record<string, { icon: typeof Info; color: string }> = {
  info: { icon: Info, color: 'var(--color-accent)' },
  warning: { icon: AlertCircle, color: 'var(--color-warning)' },
  positive: { icon: CheckCircle2, color: 'var(--color-positive)' },
  critical: { icon: AlertCircle, color: 'var(--color-negative)' },
}

export function InsightCard({ title, explanation, severity, supportingMetric }: {
  title: string; explanation: string; severity: string; supportingMetric?: string
}) {
  const style = SEVERITY_STYLE[severity] ?? SEVERITY_STYLE.info
  const Icon = style.icon
  return (
    <div className="surface rounded-xl p-4 flex gap-3">
      <Icon size={18} style={{ color: style.color }} className="shrink-0 mt-0.5" />
      <div className="min-w-0">
        <div className="text-sm font-medium">{title}</div>
        <p className="text-sm text-muted mt-0.5">{explanation}</p>
        {supportingMetric && <div className="text-xs text-muted mt-1 inline-flex items-center gap-1"><TrendingUp size={12} />{supportingMetric}</div>}
      </div>
    </div>
  )
}
