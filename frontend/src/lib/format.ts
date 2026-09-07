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
