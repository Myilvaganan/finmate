import { apiClient } from './apiClient'

export interface Transaction {
  id: string
  transaction_date: string
  description: string
  normalized_description: string
  merchant: string
  category: string
  category_id: string | null
  transaction_type: string
  debit: number
  credit: number
  amount: number
  balance: number | null
  account_id: string
  payment_method: string
  is_duplicate: boolean
  is_excluded: boolean
  notes: string | null
}

export interface TransactionFilters {
  page?: number
  page_size?: number
  start_date?: string
  end_date?: string
  account_id?: string
  category_id?: string
  search?: string
  txn_type?: string
  min_amount?: number
  max_amount?: number
}

export const transactionService = {
  async list(filters: TransactionFilters) {
    const res = await apiClient.get('/transactions', { params: filters })
    return { data: res.data.data as Transaction[], meta: res.data.meta }
  },
  async update(id: string, payload: Partial<{ category_id: string; notes: string; is_excluded: boolean }>) {
    const res = await apiClient.patch(`/transactions/${id}`, payload)
    return res.data.data as Transaction
  },
  async remove(id: string) {
    await apiClient.delete(`/transactions/${id}`)
  },
  async bulk(transaction_ids: string[], action: string, category_id?: string) {
    const res = await apiClient.post('/transactions/bulk', { transaction_ids, action, category_id })
    return res.data.data
  },
}
