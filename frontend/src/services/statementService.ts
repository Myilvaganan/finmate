import { apiClient } from './apiClient'

export const statementService = {
  async upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    const res = await apiClient.post('/statements/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data.data as { job_id: string; status: string }
  },
  async getJob(jobId: string) {
    const res = await apiClient.get(`/jobs/${jobId}`)
    return res.data.data
  },
  async list() {
    const res = await apiClient.get('/statements')
    return res.data.data
  },
  async get(id: string) {
    const res = await apiClient.get(`/statements/${id}`)
    return res.data.data
  },
  async confirm(id: string) {
    const res = await apiClient.post(`/statements/${id}/confirm`)
    return res.data.data
  },
  async cancel(id: string) {
    const res = await apiClient.post(`/statements/${id}/cancel`)
    return res.data.data
  },
  async remove(id: string) {
    const res = await apiClient.delete(`/statements/${id}`)
    return res.data.data
  },
}
