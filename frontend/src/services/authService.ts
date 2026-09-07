import { apiClient } from './apiClient'

export interface User {
  id: string
  email: string
  full_name: string
  plan: string
}

export const authService = {
  async login(email: string, password: string) {
    const res = await apiClient.post('/auth/login', { email, password })
    return res.data.data as { token: string; user: User }
  },
  async signup(email: string, password: string, full_name: string) {
    const res = await apiClient.post('/auth/signup', { email, password, full_name })
    return res.data.data as { token: string; user: User }
  },
  async me() {
    const res = await apiClient.get('/auth/me')
    return res.data.data as User
  },
}
