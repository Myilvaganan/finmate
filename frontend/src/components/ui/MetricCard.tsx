import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react'
import { formatCurrency } from '@/lib/format'

interface MetricCardProps {
  label: string
  value: number
  isCurrency?: boolean
  suffix?: string
  changePct?: number | null
  invertColor?: boolean
  icon?: LucideIcon
  iconColor?: string
}

export function MetricCard({
  label, value, isCurrency = true, suffix = '', changePct, invertColor, icon: Icon, iconColor = '#2563eb',
}: MetricCardProps) {
  const positive = (changePct ?? 0) >= 0
  const goodDirection = invertColor ? !positive : positive

  return (
    <div className="surface rounded-xl p-5 flex flex-col gap-2 min-w-0">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{label}</span>
        {Icon && (
          <span
            className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${iconColor}1a`, color: iconColor }}
          >
            <Icon size={16} />
          </span>
        )}
      </div>
      <span className="text-2xl font-semibold tracking-tight truncate">
        {isCurrency ? formatCurrency(value) : `${value}${suffix}`}
      </span>
      {changePct !== null && changePct !== undefined && (
        <div className={`flex items-center gap-1 text-xs font-medium ${goodDirection ? 'text-[color:var(--color-positive)]' : 'text-[color:var(--color-negative)]'}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          <span>{Math.abs(changePct).toFixed(1)}% from last period</span>
        </div>
      )}
    </div>
  )
}
