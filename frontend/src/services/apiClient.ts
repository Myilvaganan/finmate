import axios from 'axios'

export const apiClient = axios.create({ baseURL: '/api' })

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('finmate_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export interface ApiError {
  code: string
  message: string
  details?: unknown
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('finmate_token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    const apiError: ApiError = error.response?.data?.error ?? {
      code: 'NETWORK_ERROR',
      message: 'Could not reach the server. Please check your connection.',
    }
    return Promise.reject(apiError)
  }
)
