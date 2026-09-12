import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider } from './hooks/useAuth'
import { LandingPage } from './pages/landing/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'
import { CasePage } from './pages/moderation/CasePage'
import { QueuePage } from './pages/moderation/QueuePage'
import { NewPostingPage } from './pages/postings/NewPostingPage'
import { PostingDetailPage } from './pages/postings/PostingDetailPage'
import { PostingListPage } from './pages/postings/PostingListPage'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
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
