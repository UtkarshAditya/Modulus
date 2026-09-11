import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { LoginPage } from './pages/LoginPage'
import { CasePage } from './pages/moderation/CasePage'
import { QueuePage } from './pages/moderation/QueuePage'
import { NewPostingPage } from './pages/postings/NewPostingPage'
import { PostingDetailPage } from './pages/postings/PostingDetailPage'
import { PostingListPage } from './pages/postings/PostingListPage'

function HomeRedirect() {
  const { user } = useAuth()
  const isModerator = user?.role === 'MODERATOR' || user?.role === 'ADMIN'
  return <Navigate to={isModerator ? '/moderation' : '/postings'} replace />
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<HomeRedirect />} />
            <Route path="/postings" element={<PostingListPage />} />
            <Route path="/postings/new" element={<NewPostingPage />} />
            <Route path="/postings/:id" element={<PostingDetailPage />} />
          </Route>

          <Route
            element={
              <ProtectedRoute requireModerator>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/moderation" element={<QueuePage />} />
            <Route path="/moderation/:id" element={<CasePage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App
