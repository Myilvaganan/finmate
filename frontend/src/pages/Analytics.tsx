import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { analyticsService } from '@/services/analyticsService'
import { DateRangePicker, presetToRange, type RangePreset } from '@/components/ui/DateRangePicker'
import { ChartCard } from '@/components/ui/ChartCard'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { formatCurrency, formatCompactNumber } from '@/lib/format'

export function AnalyticsPage() {
  const [preset, setPreset] = useState<RangePreset>('last_3_months')
  const range = presetToRange(preset)
  const params = { start_date: range.start, end_date: range.end }

  const categories = useQuery({ queryKey: ['a-categories', params], queryFn: () => analyticsService.categories(params) })
  const merchants = useQuery({ queryKey: ['a-merchants', params], queryFn: () => analyticsService.merchants(params) })
  const recurring = useQuery({ queryKey: ['a-recurring'], queryFn: analyticsService.recurring })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <DateRangePicker value={preset} onChange={setPreset} />
      </div>

      <ChartCard title="Category Trends" subtitle="Spending by category over the selected period">
        {categories.isLoading && <LoadingState />}
        {categories.data && categories.data.length === 0 && <EmptyState title="No category data for this period." />}
        {categories.data && categories.data.length > 0 && (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={categories.data} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis type="number" tickFormatter={formatCompactNumber} fontSize={12} stroke="var(--color-text-muted)" />
              <YAxis type="category" dataKey="category" width={140} fontSize={12} stroke="var(--color-text-muted)" />
              <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
              <Bar dataKey="total" fill="#2563eb" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Merchant Ranking">
          {merchants.data?.length ? (
            <div className="space-y-2">
              {merchants.data.map((m) => (
                <div key={m.merchant_id ?? m.merchant} className="flex justify-between text-sm">
                  <span>{m.merchant}</span>
                  <span className="font-medium">{formatCurrency(m.total)} <span className="text-muted">({m.count})</span></span>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No merchant data yet." />}
        </ChartCard>

        <ChartCard title="Recurring Payments" subtitle="Estimated based on transaction history">
          {recurring.data?.length ? (
            <div className="space-y-2">
              {recurring.data.map((r: any, i: number) => (
                <div key={i} className="flex justify-between text-sm">
                  <span>{r.merchant} <span className="text-muted text-xs">({r.frequency})</span></span>
                  <span className="font-medium">{formatCurrency(r.average_amount)}</span>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No recurring payments detected yet." />}
        </ChartCard>
      </div>
    </div>
  )
}
