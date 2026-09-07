export function formatCurrency(value: number, currency = 'INR'): string {
  const formatter = new Intl.NumberFormat('en-IN', {
    style: 'currency', currency, maximumFractionDigits: 0,
  })
  return formatter.format(value)
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en-IN', { notation: 'compact' }).format(value)
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

/** Last calendar day of a "YYYY-MM" month string, e.g. "2026-02" -> "2026-02-28". */
export function monthEndDate(monthStr: string): string {
  const [year, month] = monthStr.split('-').map(Number)
  const end = new Date(Date.UTC(year, month, 0))
  return end.toISOString().slice(0, 10)
}
