import { apiClient } from './apiClient'

export interface ChatAnswer {
  session_id: string
  answer: string
  fact_type: string
  structured_data: Record<string, unknown>
  ai_available: boolean
  disclaimer: string
}

export const chatService = {
  async ask(question: string, session_id?: string) {
    const res = await apiClient.post('/ai/chat', { question, session_id })
    return res.data.data as ChatAnswer
  },
  async sessions() {
    const res = await apiClient.get('/ai/sessions')
    return res.data.data as { id: string; title: string; created_at: string }[]
  },
  async getSession(id: string) {
    const res = await apiClient.get(`/ai/sessions/${id}`)
    return res.data.data as { id: string; title: string; messages: { role: string; content: string; created_at: string }[] }
  },
}
