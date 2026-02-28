import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import { Layout } from '@/components/layout/Layout'

// Pages
import DashboardPage from '@/features/dashboard'
import DocumentsPage from '@/features/documents'
import GraphPage from '@/features/graph'
import RetrievalPage from '@/features/retrieval'
import LoginPage from '@/features/login'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="graph" element={<GraphPage />} />
          <Route path="retrieval" element={<RetrievalPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
