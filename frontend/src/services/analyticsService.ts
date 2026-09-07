import { apiClient } from './apiClient'

export interface OverviewMetrics {
  total_income: number
  total_expenses: number
  net_cash_flow: number
  savings_rate: number
  transaction_count: number
  average_daily_expenses: number
  median_transaction: number
  largest_transaction: number
  smallest_transaction: number
}

export interface DateRangeParams {
  start_date?: string
  end_date?: string
  account_id?: string
}

export const analyticsService = {
  async overview(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/overview', { params })
    return res.data.data as OverviewMetrics
  },
  async income(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/income', { params })
    return res.data.data as { total_income: number; monthly: { month: string; income: number; expenses: number }[] }
  },
  async expenses(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/expenses', { params })
    return res.data.data
  },
  async categories(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/categories', { params })
    return res.data.data as {
      category_id: string; category: string; total: number; count: number; percentage: number
      previous_period_amount?: number; change_percent?: number | null
    }[]
  },
  async merchants(params: DateRangeParams & { limit?: number }) {
    const res = await apiClient.get('/analytics/merchants', { params })
    return res.data.data as {
      merchant_id: string; merchant: string; total: number; count: number
      average_transaction: number; percentage_of_expenses: number
      previous_period_amount?: number; change_percent?: number | null
    }[]
  },
  async cashflow(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/cashflow', { params })
    return res.data.data
  },
  async recurring() {
    const res = await apiClient.get('/analytics/recurring')
    return res.data.data
  },
  async emi() {
    const res = await apiClient.get('/analytics/emi')
    return res.data.data as {
      emis: {
        merchant: string; average_amount: number; frequency: string; occurrences: number
        last_charged_date: string; next_expected_date: string; annualized_cost: number
      }[]
      total_monthly_emi: number
      count: number
    }
  },
  async insights(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/insights', { params })
    return res.data.data as {
      type: string; title: string; explanation: string; supporting_metric: string
      severity: string; confidence: number; source_period: string
    }[]
  },
  async weekdayVsWeekend(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/weekday-vs-weekend', { params })
    return res.data.data as { weekday: number; weekend: number }
  },
  async largeTransactions(params: DateRangeParams & { limit?: number }) {
    const res = await apiClient.get('/analytics/large-transactions', { params })
    return res.data.data as { id: string; date: string; description: string; amount: number; category_id: string | null }[]
  },
  async savingsRate(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/savings-rate', { params })
    return res.data.data as { current: number; monthly: { month: string; savings_rate: number | null }[] }
  },
  async categoryTrend(params: DateRangeParams & { category_ids: string[] }) {
    const { category_ids, ...rest } = params
    const res = await apiClient.get('/analytics/categories/trend', {
      params: { ...rest, category_ids: category_ids.join(',') },
    })
    return res.data.data as Record<string, { category: string; points: { month: string; amount: number }[] }>
  },
  async fixedVsVariable(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/expenses/fixed-variable', { params })
    return res.data.data as { fixed: number; variable: number }
  },
  async accountBalanceTrend(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/accounts/balance-trend', { params })
    return res.data.data as {
      account_id: string; bank_name: string; account_type: string; currency: string
      points: { date: string; balance: number }[]
    }[]
  },
  async spendingHeatmap(year: number, account_id?: string) {
    const res = await apiClient.get('/analytics/expenses/heatmap', { params: { year, account_id } })
    return res.data.data as { date: string; amount: number; transaction_count: number }[]
  },
  async anomalies(account_id?: string) {
    const res = await apiClient.get('/analytics/anomalies', { params: { account_id } })
    return res.data.data as {
      anomaly_type: string; severity: string; confidence: number; subject: string
      baseline: number; actual_value: number; deviation_percent: number | null; explanation: string
    }[]
  },
}
