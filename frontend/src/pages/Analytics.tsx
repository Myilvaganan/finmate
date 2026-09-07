import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { analyticsService } from '@/services/analyticsService'
import {
  DateRangePicker, defaultCustomRange, resolveDateRange, type CustomRange, type RangePreset,
} from '@/components/ui/DateRangePicker'
import { ChartCard } from '@/components/ui/ChartCard'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { CategoryBadge, BankTag } from '@/components/ui/Badges'
import { SpendingHeatmap } from '@/components/ui/SpendingHeatmap'
import { formatCurrency, formatCompactNumber, formatDate, monthEndDate } from '@/lib/format'
import { getCategoryColor } from '@/lib/colors'

const MAX_TREND_CATEGORIES = 5

const chartTooltip = { background: 'var(--color-surface)', border: '1px solid var(--color-border)' }
const TABS = ['Overview', 'Cash Flow', 'Financial Health'] as const
type Tab = (typeof TABS)[number]

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'var(--color-negative)', warning: 'var(--color-warning)', info: 'var(--color-text-muted)',
}

export function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>('Overview')
  const [preset, setPreset] = useState<RangePreset>('last_3_months')
  const [customRange, setCustomRange] = useState<CustomRange>(defaultCustomRange())
  const range = resolveDateRange(preset, customRange)
  const params = { start_date: range.start, end_date: range.end }
  const navigate = useNavigate()

  const categories = useQuery({ queryKey: ['a-categories', params], queryFn: () => analyticsService.categories(params) })
  const merchants = useQuery({ queryKey: ['a-merchants', params], queryFn: () => analyticsService.merchants(params) })
  const recurring = useQuery({ queryKey: ['a-recurring'], queryFn: analyticsService.recurring })
  const emi = useQuery({ queryKey: ['a-emi'], queryFn: analyticsService.emi })
  const expenses = useQuery({ queryKey: ['a-expenses', params], queryFn: () => analyticsService.expenses(params) })
  const cashflow = useQuery({ queryKey: ['a-cashflow', params], queryFn: () => analyticsService.cashflow(params) })
  const weekday = useQuery({ queryKey: ['a-weekday', params], queryFn: () => analyticsService.weekdayVsWeekend(params) })
  const largeTxns = useQuery({ queryKey: ['a-large', params], queryFn: () => analyticsService.largeTransactions({ ...params, limit: 8 }) })
  const savingsRate = useQuery({ queryKey: ['a-savings', params], queryFn: () => analyticsService.savingsRate(params) })
  const fixedVariable = useQuery({ queryKey: ['a-fixed-var', params], queryFn: () => analyticsService.fixedVsVariable(params) })
  const balanceTrend = useQuery({ queryKey: ['a-balance-trend', params], queryFn: () => analyticsService.accountBalanceTrend(params) })
  const anomalies = useQuery({ queryKey: ['a-anomalies'], queryFn: () => analyticsService.anomalies() })

  const [customTrendCategories, setCustomTrendCategories] = useState<string[] | null>(null)
  const defaultTrendCategories = (categories.data ?? []).slice(0, MAX_TREND_CATEGORIES).map((c) => c.category_id)
  const trendCategoryIds = customTrendCategories ?? defaultTrendCategories
  const categoryTrend = useQuery({
    queryKey: ['a-category-trend', params, trendCategoryIds],
    queryFn: () => analyticsService.categoryTrend({ ...params, category_ids: trendCategoryIds }),
    enabled: trendCategoryIds.length > 0,
  })
  const toggleTrendCategory = (categoryId: string) => {
    const base = customTrendCategories ?? defaultTrendCategories
    if (base.includes(categoryId)) {
      setCustomTrendCategories(base.filter((id) => id !== categoryId))
    } else if (base.length < MAX_TREND_CATEGORIES) {
      setCustomTrendCategories([...base, categoryId])
    }
  }

  const heatmapYear = range.end ? new Date(range.end).getFullYear() : new Date().getFullYear()
  const heatmap = useQuery({ queryKey: ['a-heatmap', heatmapYear], queryFn: () => analyticsService.spendingHeatmap(heatmapYear) })

  const essentialData = expenses.data?.essential_vs_discretionary
    ? [
        { name: 'Essential', value: expenses.data.essential_vs_discretionary.essential },
        { name: 'Discretionary', value: expenses.data.essential_vs_discretionary.discretionary },
      ]
    : []

  const fixedVariableData = fixedVariable.data
    ? [{ name: 'Fixed', value: fixedVariable.data.fixed }, { name: 'Variable', value: fixedVariable.data.variable }]
    : []

  const weekdayData = weekday.data
    ? [{ name: 'Weekday', value: weekday.data.weekday }, { name: 'Weekend', value: weekday.data.weekend }]
    : []

  const categoryLookup = Object.fromEntries((categories.data ?? []).map((c) => [c.category_id, c.category]))

  const goToCategory = (categoryId: string | null, categoryLabel: string) => {
    if (!categoryId) return
    navigate(`/transactions?category_id=${categoryId}&category_label=${encodeURIComponent(categoryLabel)}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToMerchant = (merchantId: string | null, merchantLabel: string) => {
    if (!merchantId) return
    navigate(`/transactions?merchant_id=${merchantId}&merchant_label=${encodeURIComponent(merchantLabel)}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToMonth = (month: string) => {
    navigate(`/transactions?start_date=${month}-01&end_date=${monthEndDate(month)}`)
  }
  const goToDay = (day: string) => {
    navigate(`/transactions?start_date=${day}&end_date=${day}`)
  }
  const goToPaymentMethod = (method: string) => {
    navigate(`/transactions?payment_method=${method}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToAccount = (accountId: string) => {
    navigate(`/transactions?account_id=${accountId}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToEssential = (isEssential: boolean) => {
    navigate(`/transactions?is_essential=${isEssential}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToWeekday = (which: 'weekday' | 'weekend') => {
    navigate(`/transactions?weekday=${which}&start_date=${range.start}&end_date=${range.end}`)
  }
  const goToSearch = (text: string) => {
    if (!text) return
    navigate(`/transactions?search=${encodeURIComponent(text)}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <DateRangePicker value={preset} onChange={setPreset} customRange={customRange} onCustomRangeChange={setCustomRange} />
      </div>

      <div className="flex gap-1 border-b border-default">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]' : 'border-transparent text-muted hover:text-[color:var(--color-text)]'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && (
        <>
          <ChartCard title="Expense by Category" subtitle="Click a category to see its transactions" defaultHeight={360}>
            {categories.isLoading && <LoadingState />}
            {categories.data && categories.data.length === 0 && <EmptyState title="No category data for this period." />}
            {categories.data && categories.data.length > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories.data} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tickFormatter={formatCompactNumber} fontSize={12} stroke="var(--color-text-muted)" />
                  <YAxis type="category" dataKey="category" width={140} fontSize={12} stroke="var(--color-text-muted)" />
                  <Tooltip
                    formatter={(v, key, entry: any) => key === 'total' ? [
                      `${formatCurrency(Number(v))} (${entry.payload.percentage}%)`, 'Amount',
                    ] : v}
                    contentStyle={chartTooltip}
                  />
                  <Bar dataKey="total" radius={[0, 4, 4, 0]} cursor="pointer" animationDuration={800} animationEasing="ease-out"
                    onClick={(d: any) => goToCategory(d.category_id, d.category)}>
                    {categories.data.map((c, i) => <Cell key={i} fill={getCategoryColor(c.category)} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Category Spending Trend" subtitle="Monthly spend for up to 5 categories -- click a pill to swap categories in or out" defaultHeight={360}>
            {categories.data && categories.data.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-4">
                {categories.data.map((c) => {
                  const active = trendCategoryIds.includes(c.category_id)
                  return (
                    <button
                      key={c.category_id}
                      onClick={() => toggleTrendCategory(c.category_id)}
                      className="text-xs px-2 py-1 rounded-full border transition-colors"
                      style={active
                        ? { background: getCategoryColor(c.category), borderColor: getCategoryColor(c.category), color: '#fff' }
                        : { borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
                    >
                      {c.category}
                    </button>
                  )
                })}
              </div>
            )}
            {categoryTrend.isLoading && <LoadingState />}
            {categoryTrend.data && Object.keys(categoryTrend.data).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="month" type="category" allowDuplicatedCategory={false} fontSize={12} stroke="var(--color-text-muted)" />
                  <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                  {Object.entries(categoryTrend.data).map(([cid, series]) => (
                    <Line
                      key={cid} data={series.points} dataKey="amount" name={series.category}
                      stroke={getCategoryColor(series.category)} strokeWidth={2} dot={false}
                      animationDuration={900} animationEasing="ease-out"
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : !categoryTrend.isLoading && <EmptyState title="No category data for this period." />}
          </ChartCard>

          <div className="grid lg:grid-cols-3 gap-4">
            <ChartCard title="Top Merchants" subtitle="Click a merchant to see its transactions" defaultHeight={260}>
              {merchants.data?.length ? (
                <div className="space-y-2">
                  {merchants.data.map((m) => (
                    <button
                      key={m.merchant_id ?? m.merchant}
                      onClick={() => goToMerchant(m.merchant_id, m.merchant)}
                      className="flex justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5"
                    >
                      <span>{m.merchant}</span>
                      <span className="font-medium">{formatCurrency(m.total)} <span className="text-muted">({m.count})</span></span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No merchant data yet." />}
            </ChartCard>

            <ChartCard title="Recurring Payments" subtitle="Estimated based on transaction history -- click one to see its transactions" defaultHeight={260}>
              {recurring.data?.length ? (
                <div className="space-y-2">
                  {recurring.data.map((r: any, i: number) => (
                    <button key={i} onClick={() => goToSearch(r.merchant)} className="flex justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5">
                      <span>{r.merchant} <span className="text-muted text-xs">({r.frequency})</span></span>
                      <span className="font-medium">{formatCurrency(r.average_amount)}</span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No recurring payments detected yet." />}
            </ChartCard>

            <ChartCard title="Existing EMIs" subtitle={emi.data?.count ? `${formatCurrency(emi.data.total_monthly_emi)}/mo total` : 'Detected loan repayments'} defaultHeight={260}>
              {emi.data?.emis.length ? (
                <div className="space-y-2">
                  {emi.data.emis.map((e, i) => (
                    <button key={i} onClick={() => goToSearch(e.merchant)} className="flex justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5">
                      <span>{e.merchant} <span className="text-muted text-xs">({e.frequency})</span></span>
                      <span className="font-medium">{formatCurrency(e.average_amount)}</span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No existing EMIs detected." />}
            </ChartCard>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <ChartCard title="Essential vs Discretionary" subtitle="Where necessity ends and choice begins -- click a slice to see its transactions" defaultHeight={320}>
              {essentialData.some((d) => d.value > 0) ? (
                <div className="flex flex-wrap items-center gap-4">
                  <div className="w-[180px] h-[180px] shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={essentialData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}
                          cursor="pointer" onClick={(_, i) => goToEssential(i === 0)} animationDuration={800} animationEasing="ease-out">
                          <Cell fill="#2563eb" />
                          <Cell fill="#c2410c" />
                        </Pie>
                        <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex-1 min-w-[120px] space-y-3 text-sm">
                    <button onClick={() => goToEssential(true)} className="flex items-center gap-2 w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#2563eb' }} /> Essential <span className="ml-auto font-medium">{formatCurrency(essentialData[0].value)}</span></button>
                    <button onClick={() => goToEssential(false)} className="flex items-center gap-2 w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#c2410c' }} /> Discretionary <span className="ml-auto font-medium">{formatCurrency(essentialData[1].value)}</span></button>
                  </div>
                </div>
              ) : <EmptyState title="No categorized expenses yet." />}
            </ChartCard>

            <ChartCard title="Weekday vs Weekend Spending" subtitle="Click a bar to see its transactions" defaultHeight={240}>
              {weekdayData.some((d) => d.value > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weekdayData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="name" fontSize={12} stroke="var(--color-text-muted)" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]} cursor="pointer" animationDuration={800} animationEasing="ease-out"
                      onClick={(d: any) => goToWeekday(d.name === 'Weekday' ? 'weekday' : 'weekend')}>
                      <Cell fill="#2563eb" />
                      <Cell fill="#7c3aed" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No spending recorded for this period." />}
            </ChartCard>
          </div>

          <ChartCard title="Spending Heatmap" subtitle={`Daily spending across ${heatmapYear} -- click a day to see its transactions`} defaultHeight={220}>
            {heatmap.isLoading && <LoadingState />}
            {heatmap.data && heatmap.data.some((d) => d.amount > 0) ? (
              <SpendingHeatmap data={heatmap.data} year={heatmapYear} onDayClick={goToDay} />
            ) : !heatmap.isLoading && <EmptyState title="No spending recorded for this year." />}
          </ChartCard>

          <div className="grid lg:grid-cols-2 gap-4">
            <ChartCard title="Spending by Payment Method" subtitle="Click a bar to see its transactions" defaultHeight={260}>
              {cashflow.data?.payment_methods?.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cashflow.data.payment_methods}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="method" fontSize={12} stroke="var(--color-text-muted)" className="capitalize" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                    <Bar dataKey="total" fill="#0891b2" radius={[4, 4, 0, 0]} cursor="pointer" animationDuration={800} animationEasing="ease-out"
                      onClick={(d: any) => goToPaymentMethod(d.method)} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No payment method data yet." />}
            </ChartCard>

            <ChartCard title="Account Balances" subtitle="Current balance per account -- click one to see its transactions" defaultHeight={260}>
              {cashflow.data?.accounts?.length ? (
                <div className="space-y-3">
                  {cashflow.data.accounts.map((a: any) => (
                    <button key={a.account_id} onClick={() => goToAccount(a.account_id)} className="flex items-center justify-between text-sm w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 py-1 -mx-1.5">
                      <BankTag name={a.bank_name} />
                      <span className="font-medium">{formatCurrency(a.balance, a.currency)}</span>
                    </button>
                  ))}
                </div>
              ) : <EmptyState title="No accounts yet." />}
            </ChartCard>
          </div>

          <ChartCard title="Large Transactions" subtitle="Biggest expenses in the selected period -- click one to see that day's transactions" defaultHeight={320}>
            {largeTxns.data?.length ? (
              <div className="divide-y divide-[color:var(--color-border)]">
                {largeTxns.data.map((t) => (
                  <button key={t.id} onClick={() => goToDay(t.date)} className="flex items-center justify-between py-2.5 text-sm gap-3 w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 -mx-1.5">
                    <span className="text-muted whitespace-nowrap">{formatDate(t.date)}</span>
                    <span className="flex-1 truncate">{t.description}</span>
                    {t.category_id && categoryLookup[t.category_id] && <CategoryBadge name={categoryLookup[t.category_id]} />}
                    <span className="font-medium text-[color:var(--color-negative)] whitespace-nowrap">{formatCurrency(t.amount)}</span>
                  </button>
                ))}
              </div>
            ) : <EmptyState title="No large transactions in this period." />}
          </ChartCard>
        </>
      )}

      {tab === 'Cash Flow' && (
        <>
          <ChartCard title="Net Cash Flow" subtitle="Income minus expenses, per month -- click a bar to see that month's transactions" defaultHeight={300}>
            {cashflow.data?.monthly?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashflow.data.monthly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="month" fontSize={12} stroke="var(--color-text-muted)" />
                  <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                  <Bar dataKey="net_cash_flow" radius={[4, 4, 4, 4]} cursor="pointer" animationDuration={800} animationEasing="ease-out"
                    onClick={(d: any) => goToMonth(d.month)}>
                    {cashflow.data.monthly.map((row: any, i: number) => (
                      <Cell key={i} fill={row.net_cash_flow >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState title="No cash flow data for this period." />}
          </ChartCard>

          <ChartCard title="Cumulative Cash Flow" subtitle="Running total across the selected period -- click the chart to see a month's transactions" defaultHeight={260}>
            {cashflow.data?.monthly?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cashflow.data.monthly} onClick={(d: any) => d?.activeLabel && goToMonth(d.activeLabel)} style={{ cursor: 'pointer' }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="month" fontSize={12} stroke="var(--color-text-muted)" />
                  <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                  <Area type="monotone" dataKey="cumulative_cash_flow" stroke="var(--color-accent)" fill="var(--color-accent)" fillOpacity={0.15} animationDuration={900} animationEasing="ease-out" />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyState title="No cash flow data for this period." />}
          </ChartCard>

          <ChartCard title="Account Balance Trend" subtitle="Each account's own running balance -- never summed across account types" defaultHeight={340}>
            {balanceTrend.data?.some((a) => a.points.length > 0) ? (
              <>
                <ResponsiveContainer width="100%" height="85%">
                  <LineChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" type="category" allowDuplicatedCategory={false} fontSize={12} stroke="var(--color-text-muted)" />
                    <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={formatCompactNumber} />
                    <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                    {balanceTrend.data.map((a, i) => (
                      <Line key={a.account_id} data={a.points} dataKey="balance" name={a.bank_name}
                        stroke={['#2563eb', '#c2410c', '#059669', '#7c3aed'][i % 4]} dot={false}
                        animationDuration={900} animationEasing="ease-out" />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {balanceTrend.data.map((a, i) => (
                    <button
                      key={a.account_id}
                      onClick={() => goToAccount(a.account_id)}
                      className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border border-default hover:bg-[color:var(--color-surface-2)]"
                    >
                      <span className="h-2 w-2 rounded-full" style={{ background: ['#2563eb', '#c2410c', '#059669', '#7c3aed'][i % 4] }} />
                      {a.bank_name}
                    </button>
                  ))}
                </div>
              </>
            ) : <EmptyState title="No balance history yet." description="Balances appear once statements with a running balance column are imported." />}
          </ChartCard>
        </>
      )}

      {tab === 'Financial Health' && (
        <>
          <ChartCard title="Savings Rate Trend" subtitle="(Income − Expenses) / Income, per month -- click the chart to see a month's transactions" defaultHeight={260}>
            {savingsRate.data?.monthly?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={savingsRate.data.monthly} onClick={(d: any) => d?.activeLabel && goToMonth(d.activeLabel)} style={{ cursor: 'pointer' }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="month" fontSize={12} stroke="var(--color-text-muted)" />
                  <YAxis fontSize={12} stroke="var(--color-text-muted)" tickFormatter={(v) => `${v}%`} />
                  <Tooltip formatter={(v) => v == null ? 'No income' : `${v}%`} contentStyle={chartTooltip} />
                  <Line type="monotone" dataKey="savings_rate" stroke="var(--color-accent)" strokeWidth={2} dot connectNulls={false} animationDuration={900} animationEasing="ease-out" />
                </LineChart>
              </ResponsiveContainer>
            ) : <EmptyState title="No income data for this period." />}
          </ChartCard>

          <ChartCard title="Fixed vs Variable Expenses" subtitle="Fixed = payments that already look recurring (rent, EMIs, subscriptions, utilities)" defaultHeight={320}>
            {fixedVariableData.some((d) => d.value > 0) ? (
              <div className="flex flex-wrap items-center gap-4">
                <div className="w-[180px] h-[180px] shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={fixedVariableData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2} animationDuration={800} animationEasing="ease-out">
                        <Cell fill="#0891b2" />
                        <Cell fill="#a3a3a3" />
                      </Pie>
                      <Tooltip formatter={(v) => formatCurrency(Number(v))} contentStyle={chartTooltip} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 min-w-[120px] space-y-3 text-sm">
                  <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#0891b2' }} /> Fixed <span className="ml-auto font-medium">{formatCurrency(fixedVariableData[0].value)}</span></div>
                  <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#a3a3a3' }} /> Variable <span className="ml-auto font-medium">{formatCurrency(fixedVariableData[1].value)}</span></div>
                </div>
              </div>
            ) : <EmptyState title="No categorized expenses yet." />}
          </ChartCard>

          <ChartCard title="Anomalies" subtitle="Deterministic detection: category spikes, unusual transactions, income drops -- click one to see related transactions" defaultHeight={320}>
            {anomalies.isLoading && <LoadingState />}
            {anomalies.data && anomalies.data.length === 0 && <EmptyState title="Nothing unusual detected." description="You'll see flagged spikes, outlier transactions, and income drops here." />}
            {anomalies.data && anomalies.data.length > 0 && (
              <div className="divide-y divide-[color:var(--color-border)]">
                {anomalies.data.map((a, i) => (
                  <button key={i} onClick={() => goToSearch(a.subject)} className="flex items-start gap-3 py-3 w-full text-left hover:bg-[color:var(--color-surface-2)] rounded-md px-1.5 -mx-1.5">
                    <span
                      className="mt-1 h-2 w-2 rounded-full shrink-0"
                      style={{ background: SEVERITY_COLOR[a.severity] ?? 'var(--color-text-muted)' }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{a.subject}</div>
                      <div className="text-xs text-muted mt-0.5">{a.explanation}</div>
                    </div>
                    <div className="text-sm font-medium text-right whitespace-nowrap">
                      {formatCurrency(a.actual_value)}
                      {a.deviation_percent != null && (
                        <div className="text-xs text-muted">vs {formatCurrency(a.baseline)} baseline</div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </ChartCard>
        </>
      )}
    </div>
  )
}
