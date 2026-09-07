import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { AppLayout } from '@/layouts/AppLayout'
import { LoginPage } from '@/pages/Login'
import { DashboardPage } from '@/pages/Dashboard'
import { TransactionsPage } from '@/pages/Transactions'
import { StatementsPage } from '@/pages/Statements'
import { AnalyticsPage } from '@/pages/Analytics'
import { CategoriesPage } from '@/pages/Categories'
import { AccountsPage } from '@/pages/Accounts'
import { ReportsPage } from '@/pages/Reports'
import { AIAssistantPage } from '@/pages/AIAssistant'
import { SettingsPage } from '@/pages/Settings'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="transactions" element={<TransactionsPage />} />
                <Route path="statements" element={<StatementsPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="categories" element={<CategoriesPage />} />
                <Route path="accounts" element={<AccountsPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="assistant" element={<AIAssistantPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
