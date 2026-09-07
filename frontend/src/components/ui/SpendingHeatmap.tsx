import { useMemo } from 'react'
import { formatCurrency } from '@/lib/format'
import { withAlpha } from '@/lib/colors'

interface HeatmapDay {
  date: string
  amount: number
  transaction_count: number
}

const HEAT_COLOR = '#16794e'
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function levelFor(amount: number, thresholds: number[]): number {
  if (amount <= 0) return 0
  for (let i = 0; i < thresholds.length; i++) {
    if (amount <= thresholds[i]) return i + 1
  }
  return thresholds.length + 1
}

export function SpendingHeatmap({ data, year, onDayClick }: { data: HeatmapDay[]; year: number; onDayClick?: (date: string) => void }) {
  const { weeks, monthTicks, thresholds } = useMemo(() => {
    const byDate = new Map(data.map((d) => [d.date, d]))
    const jan1 = new Date(Date.UTC(year, 0, 1))
    const dec31 = new Date(Date.UTC(year, 11, 31))

    // Pad to a Sunday-start grid, GitHub-contribution-graph style.
    const startPad = jan1.getUTCDay()
    const days: (HeatmapDay | null)[] = Array(startPad).fill(null)
    for (let d = new Date(jan1); d <= dec31; d.setUTCDate(d.getUTCDate() + 1)) {
      const iso = d.toISOString().slice(0, 10)
      days.push(byDate.get(iso) ?? { date: iso, amount: 0, transaction_count: 0 })
    }

    const weeks: (HeatmapDay | null)[][] = []
    for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7))

    const nonZero = data.map((d) => d.amount).filter((a) => a > 0).sort((a, b) => a - b)
    const q = (p: number) => nonZero.length ? nonZero[Math.min(nonZero.length - 1, Math.floor(nonZero.length * p))] : 0
    const thresholds = [q(0.25), q(0.5), q(0.75)]

    const monthTicks: { label: string; weekIndex: number }[] = []
    let lastMonth = -1
    weeks.forEach((week, wi) => {
      const firstReal = week.find((d) => d)
      if (!firstReal) return
      const month = new Date(firstReal.date).getUTCMonth()
      if (month !== lastMonth) {
        monthTicks.push({ label: MONTH_LABELS[month], weekIndex: wi })
        lastMonth = month
      }
    })

    return { weeks, monthTicks, thresholds }
  }, [data, year])

  const alphaForLevel = [0, 0.22, 0.45, 0.7, 1]

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: `${weeks.length * 13 + 24}px` }}>
        <div className="relative h-4 mb-1 text-[10px] text-muted">
          {monthTicks.map((m, i) => (
            <span key={i} className="absolute" style={{ left: `${m.weekIndex * 13 + 20}px` }}>{m.label}</span>
          ))}
        </div>
        <div className="flex gap-[3px]">
          <div className="flex flex-col gap-[3px] text-[10px] text-muted pr-1 justify-around shrink-0" style={{ width: '16px' }}>
            <span>Mon</span><span>Wed</span><span>Fri</span>
          </div>
          <div className="flex gap-[3px]">
            {weeks.map((week, wi) => (
              <div key={wi} className="flex flex-col gap-[3px]">
                {week.map((day, di) => {
                  if (!day) return <div key={di} className="h-[11px] w-[11px]" />
                  const level = levelFor(day.amount, thresholds)
                  return (
                    <div
                      key={di}
                      onClick={onDayClick ? () => onDayClick(day.date) : undefined}
                      className="h-[11px] w-[11px] rounded-[2px]"
                      style={{
                        background: level === 0 ? 'var(--color-surface-2)' : withAlpha(HEAT_COLOR, alphaForLevel[level]),
                        border: level === 0 ? '1px solid var(--color-border)' : 'none',
                        cursor: onDayClick ? 'pointer' : undefined,
                      }}
                      title={`${day.date}: ${formatCurrency(day.amount)}${day.transaction_count ? ` (${day.transaction_count} txn${day.transaction_count > 1 ? 's' : ''})` : ''}`}
                    />
                  )
                })}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1.5 mt-3 text-[10px] text-muted">
          <span>Less</span>
          {alphaForLevel.map((a, i) => (
            <span
              key={i}
              className="h-[11px] w-[11px] rounded-[2px]"
              style={{
                background: i === 0 ? 'var(--color-surface-2)' : withAlpha(HEAT_COLOR, a),
                border: i === 0 ? '1px solid var(--color-border)' : 'none',
              }}
            />
          ))}
          <span>More</span>
        </div>
      </div>
    </div>
  )
}
