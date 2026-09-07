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
    return res.data.data as { category_id: string; category: string; total: number; count: number }[]
  },
  async merchants(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/merchants', { params })
    return res.data.data as { merchant_id: string; merchant: string; total: number; count: number }[]
  },
  async cashflow(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/cashflow', { params })
    return res.data.data
  },
  async recurring() {
    const res = await apiClient.get('/analytics/recurring')
    return res.data.data
  },
  async insights(params: DateRangeParams) {
    const res = await apiClient.get('/analytics/insights', { params })
    return res.data.data as {
      type: string; title: string; explanation: string; supporting_metric: string
      severity: string; confidence: number; source_period: string
    }[]
  },
}
