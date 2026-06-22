import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { SearchPage } from './pages/SearchPage'
import { BulkPage } from './pages/BulkPage'
import { ProspectsPage } from './pages/ProspectsPage'
import { ThemeProvider } from './theme/ThemeProvider'
import { queryClient } from './services/queryClient'

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="bulk" element={<BulkPage />} />
            <Route path="prospects" element={<ProspectsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
