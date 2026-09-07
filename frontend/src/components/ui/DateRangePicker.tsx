import { useMemo, useState } from 'react'

export type RangePreset =
  | 'today' | 'this_week' | 'this_month' | 'last_month' | 'last_3_months' | 'last_6_months' | 'this_year' | 'custom'

export interface CustomRange {
  start: string
  end: string
}

const LABELS: Record<RangePreset, string> = {
  today: 'Today', this_week: 'This Week', this_month: 'This Month', last_month: 'Last Month',
  last_3_months: 'Last 3 Months', last_6_months: 'Last 6 Months', this_year: 'This Year',
  custom: 'Custom Range',
}

export function presetToRange(preset: Exclude<RangePreset, 'custom'>): { start: string; end: string } {
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

/** Resolves any RangePreset (including 'custom') to concrete dates. Use this instead of
 * presetToRange() wherever the selected preset could be 'custom' -- presetToRange() itself
 * has no notion of a user-picked range and can't return one. */
export function resolveDateRange(preset: RangePreset, custom: CustomRange): { start: string; end: string } {
  if (preset === 'custom') {
    // Guard against an incomplete/invalid custom range (e.g. end before start) rather than
    // silently sending a backwards range to the API.
    if (custom.start && custom.end && custom.start <= custom.end) return custom
    return presetToRange('last_3_months')
  }
  return presetToRange(preset)
}

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function defaultCustomRange(): CustomRange {
  return presetToRange('last_3_months')
}

export function DateRangePicker({
  value, onChange, customRange, onCustomRangeChange,
}: {
  value: RangePreset
  onChange: (v: RangePreset) => void
  customRange?: CustomRange
  onCustomRangeChange?: (r: CustomRange) => void
}) {
  const options = useMemo(() => Object.entries(LABELS) as [RangePreset, string][], [])
  const [localCustom, setLocalCustom] = useState<CustomRange>(customRange ?? defaultCustomRange())
  const custom = customRange ?? localCustom

  const updateCustom = (next: CustomRange) => {
    setLocalCustom(next)
    onCustomRangeChange?.(next)
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as RangePreset)}
        className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none"
      >
        {options.map(([key, label]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>
      {value === 'custom' && (
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={custom.start}
            max={custom.end || undefined}
            onChange={(e) => updateCustom({ ...custom, start: e.target.value })}
            className="rounded-lg border border-default bg-transparent px-2.5 py-1.5 text-sm outline-none"
          />
          <span className="text-muted text-sm">to</span>
          <input
            type="date"
            value={custom.end}
            min={custom.start || undefined}
            onChange={(e) => updateCustom({ ...custom, end: e.target.value })}
            className="rounded-lg border border-default bg-transparent px-2.5 py-1.5 text-sm outline-none"
          />
        </div>
      )}
    </div>
  )
}
