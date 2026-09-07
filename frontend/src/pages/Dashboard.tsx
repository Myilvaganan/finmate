import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowRight, Landmark, Lightbulb, Repeat, TrendingDown, TrendingUp, Wallet, PiggyBank, Receipt, CreditCard } from 'lucide-react'
import { analyticsService } from '@/services/analyticsService'
import { transactionService } from '@/services/transactionService'
import { useAuth } from '@/context/AuthContext'
import { MetricCard } from '@/components/ui/MetricCard'
import { ChartCard } from '@/components/ui/ChartCard'
import {
  DateRangePicker, defaultCustomRange, resolveDateRange, type CustomRange, type RangePreset,
} from '@/components/ui/DateRangePicker'
import { InsightCard } from '@/components/ui/InsightCard'
import { InitialsAvatar } from '@/components/ui/Avatar'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States'
import { formatCurrency, formatCompactNumber, formatDate, monthEndDate } from '@/lib/format'
import { getCategoryColor } from '@/lib/colors'

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [preset, setPreset] = useState<RangePreset>('this_month')
  const [customRange, setCustomRange] = useState<CustomRange>(defaultCustomRange())
  const range = resolveDateRange(preset, customRange)
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
  const recurring = useQuery({ queryKey: ['recurring'], queryFn: analyticsService.recurring })
  const emi = useQuery({ queryKey: ['emi'], queryFn: analyticsService.emi })

  const hasAnyData = (overview.data?.transaction_count ?? 0) > 0
  const totalBalance = cashflow.data?.accounts?.reduce((s: number, a: any) => s + a.balance, 0) ?? 0
  const topInsight = insights.data?.[0]

  const greetingName = user?.full_name?.split(' ')[0] || 'there'
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  const goToMonth = (month: string) => navigate(`/transactions?start_date=${month}-01&end_date=${monthEndDate(month)}`)
  const goToDay = (day: string) => navigate(`/transactions?start_date=${day}&end_date=${day}`)
  const goToCategory = (categoryId: string | null, categoryLabel: string) => {
    if (!categoryId) return
    navigate(`/transactions?category_id=${categoryId}&category_label=${encodeURIComponent(categoryLabel)}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToMerchant = (merchantId: string | null, merchantLabel: string) => {
    if (!merchantId) return
    navigate(`/transactions?merchant_id=${merchantId}&merchant_label=${encodeURIComponent(merchantLabel)}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToSearch = (text: string) => {
    if (!text) return
    navigate(`/transactions?search=${encodeURIComponent(text)}`)
  }
  const goToEssential = (isEssential: boolean) => {
    navigate(`/transactions?is_essential=${isEssential}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToInsightPeriod = (sourcePeriod: string) => {
    const [start, end] = sourcePeriod.split(' to ')
    if (start && end) navigate(`/transactions?start_date=${start}&end_date=${end}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{greeting}, {greetingName} 👋</h1>
          <p className="text-sm text-muted mt-0.5">Here's your financial overview.</p>
        </div>
        <DateRangePicker value={preset} onChange={setPreset} customRange={customRange} onCustomRangeChange={setCustomRange} />
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
            <ChartCard title="Income vs Expenses" subtitle="Monthly comparison -- click a bar to see that month's transactions" defaultHeight={300}>
              {cashflow.data?.monthly?.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cashflow.data.monthly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="month" fontSize={12} stroke="var(--color-text-muted)" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
                    <Legend />
                    <Bar dataKey="income" fill="#16794e" radius={[4, 4, 0, 0]} name="Income" animationDuration={800} animationEasing="ease-out"
                      cursor="pointer" onClick={(d: any) => goToMonth(d.month)} />
                    <Bar dataKey="expenses" fill="#b42318" radius={[4, 4, 0, 0]} name="Expenses" animationDuration={800} animationEasing="ease-out" animationBegin={100}
                      cursor="pointer" onClick={(d: any) => goToMonth(d.month)} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No data for this period." />}
            </ChartCard>

            <ChartCard title="Expense by Category" subtitle="Where your money went -- click a category to see its transactions" defaultHeight={320}>
              {expenses.data?.by_category?.length ? (
                <div className="flex flex-wrap items-center gap-4">
                  <div className="w-[200px] h-[200px] shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={expenses.data.by_category} dataKey="total" nameKey="category" innerRadius={55} outerRadius={90} paddingAngle={2} animationDuration={800} animationEasing="ease-out"
                          cursor="pointer" onClick={(d: any) => goToCategory(d.category_id, d.category)}>
                          {expenses.data.by_category.map((c: any, i: number) => <Cell key={i} fill={getCategoryColor(c.category)} />)}
                        </Pie>
                        <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex-1 min-w-[140px] space-y-2">
                    {expenses.data.by_category.slice(0, 6).map((c: any) => {
                      const total = expenses.data.by_category.reduce((s: number, x: any) => s + x.total, 0)
                      const pct = total ? Math.round((c.total / total) * 100) : 0
                      return (
                        <button key={c.category_id ?? c.category} onClick={() => goToCategory(c.category_id, c.category)} className="flex items-center justify-between text-sm gap-2 w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-0.5 -mx-1.5">
                          <span className="flex items-center gap-2 min-w-0">
                            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: getCategoryColor(c.category) }} />
                            <span className="truncate">{c.category}</span>
                          </span>
                          <span className="text-muted shrink-0">{pct}%</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              ) : <EmptyState title="No categorized expenses yet." />}
            </ChartCard>
          </div>

          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
            <ChartCard title="Cash Flow Trend" subtitle="Daily spending -- click the chart to see that day's transactions" action={<span className="text-xs text-muted">{preset.replace('_', ' ')}</span>} defaultHeight={260}>
              {expenses.data?.daily?.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={expenses.data.daily} onClick={(d: any) => d?.activeLabel && goToDay(d.activeLabel)} style={{ cursor: 'pointer' }}>
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
                    <Area type="monotone" dataKey="total" stroke="#2563eb" strokeWidth={2} fill="url(#spend)" animationDuration={900} animationEasing="ease-out" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No spending recorded for this period." />}
            </ChartCard>
            </div>

            <ChartCard title="Top Merchants" subtitle="By total spend -- click one to see its transactions" defaultHeight={260}>
              {merchants.data?.length ? (
                <div className="space-y-3">
                  {merchants.data.slice(0, 5).map((m) => (
                    <button key={m.merchant_id ?? m.merchant} onClick={() => goToMerchant(m.merchant_id, m.merchant)} className="flex items-center gap-3 text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5">
                      <InitialsAvatar name={m.merchant} size={28} />
                      <span className="truncate flex-1">{m.merchant}</span>
                      <span className="font-medium shrink-0">{formatCurrency(m.total)}</span>
                    </button>
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
              defaultHeight={300}
            >
              {recentTxns.data?.data?.length ? (
                <div className="divide-y divide-[color:var(--color-border)] -mx-1">
                  {recentTxns.data.data.map((t) => (
                    <button key={t.id} onClick={() => goToDay(t.transaction_date)} className="flex items-center gap-3 py-2.5 px-1 text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md">
                      <InitialsAvatar name={t.merchant || t.description} size={30} />
                      <div className="min-w-0 flex-1">
                        <div className="truncate">{t.merchant || t.description}</div>
                        <div className="text-xs text-muted flex items-center gap-1.5">
                          {formatDate(t.transaction_date)} ·
                          <span className="inline-flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: getCategoryColor(t.category) }} />
                            {t.category}
                          </span>
                        </div>
                      </div>
                      <span className={`font-medium shrink-0 ${t.credit > 0 ? 'text-[color:var(--color-positive)]' : ''}`}>
                        {t.credit > 0 ? '+' : '-'}{formatCurrency(t.credit > 0 ? t.credit : t.debit)}
                      </span>
                    </button>
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

          <div className="grid lg:grid-cols-3 gap-4">
            <ChartCard
              title="Recurring Payments"
              subtitle="Detected subscriptions & regular bills"
              action={<Link to="/analytics" className="text-xs text-[color:var(--color-accent)] flex items-center gap-1 font-medium">View All <ArrowRight size={12} /></Link>}
              defaultHeight={200}
            >
              {recurring.data?.length ? (
                <div className="space-y-2.5">
                  {recurring.data.slice(0, 4).map((r: any, i: number) => (
                    <button key={i} onClick={() => goToSearch(r.merchant)} className="flex items-center justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-0.5 -mx-1.5">
                      <span className="flex items-center gap-2">
                        <Repeat size={14} className="text-muted" />
                        {r.merchant} <span className="text-xs text-muted capitalize">({r.frequency})</span>
                      </span>
                      <span className="font-medium">{formatCurrency(r.average_amount)}</span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No recurring payments detected yet." description="Estimates appear once a merchant charges you on a regular pattern." />}
            </ChartCard>

            <ChartCard
              title="Existing EMIs"
              subtitle={emi.data?.count ? `${formatCurrency(emi.data.total_monthly_emi)}/mo total` : 'Detected loan repayments'}
              action={<Link to="/analytics" className="text-xs text-[color:var(--color-accent)] flex items-center gap-1 font-medium">View All <ArrowRight size={12} /></Link>}
              defaultHeight={200}
            >
              {emi.data?.emis.length ? (
                <div className="space-y-2.5">
                  {emi.data.emis.slice(0, 4).map((e, i) => (
                    <button key={i} onClick={() => goToSearch(e.merchant)} className="flex items-center justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-0.5 -mx-1.5">
                      <span className="flex items-center gap-2 min-w-0">
                        <CreditCard size={14} className="text-muted shrink-0" />
                        <span className="truncate">{e.merchant}</span>
                        <span className="text-xs text-muted capitalize shrink-0">({e.frequency})</span>
                      </span>
                      <span className="font-medium shrink-0">{formatCurrency(e.average_amount)}</span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No existing EMIs detected." description="EMIs appear once a loan repayment shows a regular pattern in your statements." />}
            </ChartCard>

            <ChartCard title="Essential vs Discretionary" subtitle="This period's expense split -- click a row to see its transactions" defaultHeight={200}>
              {expenses.data?.essential_vs_discretionary && (expenses.data.essential_vs_discretionary.essential > 0 || expenses.data.essential_vs_discretionary.discretionary > 0) ? (
                <div className="space-y-4">
                  {(() => {
                    const ed = expenses.data.essential_vs_discretionary
                    const total = ed.essential + ed.discretionary
                    const essentialPct = total ? Math.round((ed.essential / total) * 100) : 0
                    return (
                      <>
                        <div className="h-2.5 rounded-full overflow-hidden flex surface-2">
                          <div style={{ width: `${essentialPct}%`, background: '#2563eb' }} />
                          <div style={{ width: `${100 - essentialPct}%`, background: '#c2410c' }} />
                        </div>
                        <button onClick={() => goToEssential(true)} className="flex justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-0.5 -mx-1.5">
                          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: '#2563eb' }} />Essential</span>
                          <span className="font-medium">{formatCurrency(ed.essential)}</span>
                        </button>
                        <button onClick={() => goToEssential(false)} className="flex justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-0.5 -mx-1.5">
                          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: '#c2410c' }} />Discretionary</span>
                          <span className="font-medium">{formatCurrency(ed.discretionary)}</span>
                        </button>
                      </>
                    )
                  })()}
                </div>
              ) : <EmptyState title="No categorized expenses yet." />}
            </ChartCard>
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
            <InsightCard key={idx} title={i.title} explanation={i.explanation} severity={i.severity} supportingMetric={i.supporting_metric} onClick={() => goToInsightPeriod(i.source_period)} />
          ))}
        </div>
      </div>
    </div>
  )
}
