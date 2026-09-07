import { apiClient } from './apiClient'

export const reportService = {
  async generate(payload: { report_type: string; start_date: string; end_date: string; account_id?: string; export_format?: string }) {
    const res = await apiClient.post('/reports/generate', payload)
    return res.data.data
  },
}
