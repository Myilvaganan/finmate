import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowRight, Landmark, Lightbulb, TrendingDown, TrendingUp, Wallet, PiggyBank, Receipt } from 'lucide-react'
import { analyticsService } from '@/services/analyticsService'
import { transactionService } from '@/services/transactionService'
import { useAuth } from '@/context/AuthContext'
import { MetricCard } from '@/components/ui/MetricCard'
import { ChartCard } from '@/components/ui/ChartCard'
import { DateRangePicker, presetToRange, type RangePreset } from '@/components/ui/DateRangePicker'
import { InsightCard } from '@/components/ui/InsightCard'
import { InitialsAvatar } from '@/components/ui/Avatar'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { formatCurrency, formatCompactNumber, formatDate } from '@/lib/format'

const PALETTE = ['#2563eb', '#16794e', '#b54708', '#7c3aed', '#0891b2', '#be185d', '#65a30d', '#c2410c']

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [preset, setPreset] = useState<RangePreset>('this_month')
  const range = presetToRange(preset)
  const params = { start_date: range.start, end_date: range.end }

  const overview = useQuery({ queryKey: ['overview', params], queryFn: () => analyticsService.overview(params) })
  const expenses = useQuery({ queryKey: ['expenses', params], queryFn: () => analyticsService.expenses(params) })
  const cashflow = useQuery({ queryKey: ['cashflow', params], queryFn: () => analyticsService.cashflow(params) })
  const merchants = useQuery({ queryKey: ['merchants', params], queryFn: () => analyticsService.merchants(params) })
  const insights = useQuery({ queryKey: ['insights'], queryFn: () => analyticsService.insights({}) })
  const recentTxns = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => transactionService.list({ page: 1, page_size: 5 }),
  })

  const hasAnyData = (overview.data?.transaction_count ?? 0) > 0
  const totalBalance = cashflow.data?.accounts?.reduce((s: number, a: any) => s + a.balance, 0) ?? 0
  const topInsight = insights.data?.[0]

  const greetingName = user?.full_name?.split(' ')[0] || 'there'
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{greeting}, {greetingName} 👋</h1>
          <p className="text-sm text-muted mt-0.5">Here's your financial overview.</p>
        </div>
        <DateRangePicker value={preset} onChange={setPreset} />
      </div>

      {overview.isLoading && <LoadingState label="Loading your financial overview…" />}
      {overview.isError && <ErrorState message="Could not load your financial overview." />}

      {overview.data && !hasAnyData && (
        <EmptyState
          title="No financial data yet."
          description="Upload your first bank statement to unlock your financial dashboard."
          action={
            <button
              onClick={() => navigate('/statements')}
              className="mt-2 rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] px-4 py-2 text-sm font-medium"
            >
              Upload Statement
            </button>
          }
        />
      )}

      {overview.data && hasAnyData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <MetricCard label="Total Balance" value={totalBalance} icon={Wallet} iconColor="#2563eb" />
            <MetricCard label="Total Income" value={overview.data.total_income} icon={TrendingUp} iconColor="#16794e" />
            <MetricCard label="Total Expenses" value={overview.data.total_expenses} invertColor icon={TrendingDown} iconColor="#b42318" />
            <MetricCard label="Net Cash Flow" value={overview.data.net_cash_flow} icon={Landmark} iconColor="#7c3aed" />
            <MetricCard label="Savings Rate" value={overview.data.savings_rate} isCurrency={false} suffix="%" icon={PiggyBank} iconColor="#0891b2" />
            <MetricCard label="Transactions" value={overview.data.transaction_count} isCurrency={false} icon={Receipt} iconColor="#c2410c" />
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <ChartCard title="Income vs Expenses" subtitle="Monthly comparison">
              {cashflow.data?.monthly?.length ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={cashflow.data.monthly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="month" fontSize={12} stroke="var(--color-text-muted)" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
                    <Legend />
                    <Bar dataKey="income" fill="#16794e" radius={[4, 4, 0, 0]} name="Income" />
                    <Bar dataKey="expenses" fill="#b42318" radius={[4, 4, 0, 0]} name="Expenses" />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No data for this period." />}
            </ChartCard>

            <ChartCard title="Expense by Category" subtitle="Where your money went">
              {expenses.data?.by_category?.length ? (
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width="55%" height={220}>
                    <PieChart>
                      <Pie data={expenses.data.by_category} dataKey="total" nameKey="category" innerRadius={55} outerRadius={90} paddingAngle={2}>
                        {expenses.data.by_category.map((_: any, i: number) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 min-w-0 space-y-2">
                    {expenses.data.by_category.slice(0, 6).map((c: any, i: number) => {
                      const total = expenses.data.by_category.reduce((s: number, x: any) => s + x.total, 0)
                      const pct = total ? Math.round((c.total / total) * 100) : 0
                      return (
                        <div key={c.category_id ?? c.category} className="flex items-center justify-between text-sm gap-2">
                          <span className="flex items-center gap-2 min-w-0">
                            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: PALETTE[i % PALETTE.length] }} />
                            <span className="truncate">{c.category}</span>
                          </span>
                          <span className="text-muted shrink-0">{pct}%</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : <EmptyState title="No categorized expenses yet." />}
            </ChartCard>
          </div>

          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
            <ChartCard title="Cash Flow Trend" subtitle="Daily spending" action={<span className="text-xs text-muted">{preset.replace('_', ' ')}</span>}>
              {expenses.data?.daily?.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={expenses.data.daily}>
                    <defs>
                      <linearGradient id="spend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" fontSize={11} stroke="var(--color-text-muted)" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
                    <Area type="monotone" dataKey="total" stroke="#2563eb" strokeWidth={2} fill="url(#spend)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No spending recorded for this period." />}
            </ChartCard>
            </div>

            <ChartCard title="Top Merchants" subtitle="By total spend">
              {merchants.data?.length ? (
                <div className="space-y-3">
                  {merchants.data.slice(0, 5).map((m) => (
                    <div key={m.merchant_id ?? m.merchant} className="flex items-center gap-3 text-sm">
                      <InitialsAvatar name={m.merchant} size={28} />
                      <span className="truncate flex-1">{m.merchant}</span>
                      <span className="font-medium shrink-0">{formatCurrency(m.total)}</span>
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="No merchant activity yet." />}
            </ChartCard>
          </div>

          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
            <ChartCard
              title="Recent Transactions"
              subtitle="Your latest activity"
              action={<Link to="/transactions" className="text-xs text-[color:var(--color-accent)] flex items-center gap-1 font-medium">View All <ArrowRight size={12} /></Link>}
            >
              {recentTxns.data?.data?.length ? (
                <div className="divide-y divide-[color:var(--color-border)] -mx-1">
                  {recentTxns.data.data.map((t) => (
                    <div key={t.id} className="flex items-center gap-3 py-2.5 px-1 text-sm">
                      <InitialsAvatar name={t.merchant || t.description} size={30} />
                      <div className="min-w-0 flex-1">
                        <div className="truncate">{t.merchant || t.description}</div>
                        <div className="text-xs text-muted">{formatDate(t.transaction_date)} · {t.category}</div>
                      </div>
                      <span className={`font-medium shrink-0 ${t.credit > 0 ? 'text-[color:var(--color-positive)]' : ''}`}>
                        {t.credit > 0 ? '+' : '-'}{formatCurrency(t.credit > 0 ? t.credit : t.debit)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="No transactions yet." />}
            </ChartCard>
            </div>

            <div className="surface rounded-xl p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Lightbulb size={16} className="text-[color:var(--color-warning)]" /> AI Insight
              </div>
              {topInsight ? (
                <>
                  <p className="text-sm text-muted flex-1">{topInsight.explanation}</p>
                  <Link to="/analytics" className="text-xs font-medium text-[color:var(--color-accent)] flex items-center gap-1">
                    View Details <ArrowRight size={12} />
                  </Link>
                </>
              ) : (
                <p className="text-sm text-muted">No insights yet — check back after a few weeks of activity.</p>
              )}
            </div>
          </div>
        </>
      )}

      <div>
        <h2 className="text-sm font-semibold mb-3">Smart Insights</h2>
        {insights.isLoading && <LoadingState label="Generating insights…" />}
        {insights.data && insights.data.length === 0 && (
          <EmptyState title="No insights yet." description="Insights appear once you have a few weeks of transaction history." />
        )}
        <div className="grid md:grid-cols-2 gap-3">
          {insights.data?.map((i, idx) => (
            <InsightCard key={idx} title={i.title} explanation={i.explanation} severity={i.severity} supportingMetric={i.supporting_metric} />
          ))}
        </div>
      </div>
    </div>
  )
}
