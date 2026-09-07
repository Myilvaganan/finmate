import { apiClient } from './apiClient'

export interface CategoryRecord {
  id: string
  name: string
  parent_type: 'income' | 'expense' | 'transfer' | 'investment'
  group_name: string
  is_essential: boolean
  is_system: boolean
}

export const categoryService = {
  async list() {
    const res = await apiClient.get('/categories')
    return res.data.data as CategoryRecord[]
  },
  async create(payload: { name: string; group_name?: string; parent_type?: string; is_essential?: boolean }) {
    const res = await apiClient.post('/categories', payload)
    return res.data.data as CategoryRecord
  },
  async update(id: string, payload: Partial<{ name: string; group_name: string; is_essential: boolean }>) {
    const res = await apiClient.patch(`/categories/${id}`, payload)
    return res.data.data as CategoryRecord
  },
  async remove(id: string) {
    await apiClient.delete(`/categories/${id}`)
  },
}
