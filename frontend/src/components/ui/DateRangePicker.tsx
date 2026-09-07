import { useMemo } from 'react'

export type RangePreset = 'today' | 'this_week' | 'this_month' | 'last_month' | 'last_3_months' | 'last_6_months' | 'this_year'

const LABELS: Record<RangePreset, string> = {
  today: 'Today', this_week: 'This Week', this_month: 'This Month', last_month: 'Last Month',
  last_3_months: 'Last 3 Months', last_6_months: 'Last 6 Months', this_year: 'This Year',
}

export function presetToRange(preset: RangePreset): { start: string; end: string } {
  const now = new Date()
  const end = new Date(now)
  let start = new Date(now)

  switch (preset) {
    case 'today':
      break
    case 'this_week':
      start.setDate(now.getDate() - now.getDay())
      break
    case 'this_month':
      start = new Date(now.getFullYear(), now.getMonth(), 1)
      break
    case 'last_month': {
      const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0)
      const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return { start: toISO(lastMonthStart), end: toISO(lastMonthEnd) }
    }
    case 'last_3_months':
      start = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate())
      break
    case 'last_6_months':
      start = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate())
      break
    case 'this_year':
      start = new Date(now.getFullYear(), 0, 1)
      break
  }
  return { start: toISO(start), end: toISO(end) }
}

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function DateRangePicker({ value, onChange }: { value: RangePreset; onChange: (v: RangePreset) => void }) {
  const options = useMemo(() => Object.entries(LABELS) as [RangePreset, string][], [])
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as RangePreset)}
      className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none"
    >
      {options.map(([key, label]) => (
        <option key={key} value={key}>{label}</option>
      ))}
    </select>
  )
}
