import { apiClient } from './apiClient'

export interface Account {
  id: string
  bank_name: string
  account_type: string
  masked_account_number: string
  currency: string
  opening_balance: number
  closing_balance: number
  is_demo: boolean
}

export const accountService = {
  async list() {
    const res = await apiClient.get('/accounts')
    return res.data.data as Account[]
  },
  async create(payload: { bank_name: string; account_type: string; account_number?: string; opening_balance?: number }) {
    const res = await apiClient.post('/accounts', payload)
    return res.data.data as Account
  },
  async remove(id: string) {
    const res = await apiClient.delete(`/accounts/${id}`)
    return res.data.data
  },
}
