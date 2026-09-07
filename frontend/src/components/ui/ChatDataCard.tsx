import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatCurrency } from '@/lib/format'

/** Renders the structured_data a chat answer was grounded in -- never invents anything,
 * only visualizes numbers the backend's deterministic tools already returned. */
export function ChatDataCard({ data }: { data: Record<string, any> }) {
  if (!data || Object.keys(data).length === 0) return null

  if (data.period_a && data.period_b) {
    const chartData = [
      { period: 'Previous', income: data.period_b.income, expenses: data.period_b.expenses },
      { period: 'Current', income: data.period_a.income, expenses: data.period_a.expenses },
    ]
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2">
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis dataKey="period" fontSize={11} stroke="var(--color-text-muted)" />
            <YAxis fontSize={10} stroke="var(--color-text-muted)" width={40} />
            <Tooltip formatter={(v: any) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', fontSize: 12 }} />
            <Bar dataKey="income" fill="#16794e" radius={[3, 3, 0, 0]} name="Income" />
            <Bar dataKey="expenses" fill="#b42318" radius={[3, 3, 0, 0]} name="Expenses" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (typeof data.total === 'number' && (data.category || data.merchant)) {
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2 flex items-center justify-between">
        <div>
          <div className="text-xs text-muted">{data.category || data.merchant}</div>
          <div className="text-lg font-semibold">{formatCurrency(data.total)}</div>
        </div>
        <div className="text-xs text-muted">{data.transaction_count} transaction{data.transaction_count === 1 ? '' : 's'}</div>
      </div>
    )
  }

  if (Array.isArray(data.transactions) && data.transactions.length > 0) {
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2 space-y-1.5">
        {data.transactions.slice(0, 5).map((t: any, i: number) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="truncate mr-2">{t.description}</span>
            <span className="font-medium shrink-0">{formatCurrency(t.amount)}</span>
          </div>
        ))}
      </div>
    )
  }

  if (Array.isArray(data.emis) && data.emis.length > 0) {
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2 space-y-1.5">
        {typeof data.total_monthly_emi === 'number' && (
          <div className="flex justify-between text-xs pb-1 mb-1 border-b border-default">
            <span className="text-muted">Total monthly EMI</span>
            <span className="font-semibold">{formatCurrency(data.total_monthly_emi)}</span>
          </div>
        )}
        {data.emis.slice(0, 5).map((e: any, i: number) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="truncate mr-2">{e.merchant} <span className="text-muted">({e.frequency})</span></span>
            <span className="font-medium shrink-0">{formatCurrency(e.amount)}</span>
          </div>
        ))}
      </div>
    )
  }

  if (Array.isArray(data.recurring) && data.recurring.length > 0) {
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2 space-y-1.5">
        {data.recurring.slice(0, 5).map((r: any, i: number) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="truncate mr-2">{r.merchant} <span className="text-muted">({r.frequency})</span></span>
            <span className="font-medium shrink-0">{formatCurrency(r.amount)}</span>
          </div>
        ))}
      </div>
    )
  }

  const numericEntries = Object.entries(data).filter(([, v]) => typeof v === 'number')
  if (numericEntries.length > 0) {
    return (
      <div className="surface-2 border border-default rounded-lg p-3 mt-2 flex flex-wrap gap-4">
        {numericEntries.map(([k, v]) => (
          <div key={k}>
            <div className="text-[10px] uppercase tracking-wide text-muted">{k.replace(/_/g, ' ')}</div>
            <div className="text-sm font-semibold">
              {k.toLowerCase().includes('pct') || k.toLowerCase().includes('rate') ? `${v}%` : formatCurrency(v as number)}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return null
}
