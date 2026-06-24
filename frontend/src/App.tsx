import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import AuthLayout from './components/layout/AuthLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoadingState } from './components/shared/LoadingState'
import HomePage from './pages/HomePage'

// ---------------------------------------------------------------------------
// Route-based code splitting
// ---------------------------------------------------------------------------
// HomePage is the LCP candidate for / and is loaded eagerly; every other
// page is lazy-loaded so it is fetched only on navigation. Combined with
// vite.config.ts manualChunks this keeps the initial JS payload small
// (only the shell + first-paint dependencies are downloaded).
// ---------------------------------------------------------------------------

const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))

// Authenticated pages — loaded after login
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const AssetsPage = lazy(() => import('./pages/AssetsPage'))
const AgentsPage = lazy(() => import('./pages/AgentsPage'))
const SkillsPage = lazy(() => import('./pages/SkillsPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const WorkspacePage = lazy(() => import('./pages/WorkspacePage'))
const WorkflowsPage = lazy(() => import('./pages/WorkflowsPage'))
const RevisionPage = lazy(() => import('./pages/RevisionPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

// Suspense fallback shown while a lazy chunk is being fetched.
// Keeps the visual layout stable so CLS does not spike on route change.
function PageLoading() {
  return <LoadingState label="Loading page…" size="md" />
}

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
        </Route>

        {/* Public home page — standalone, has its own nav. */}
        <Route path="/" element={<HomePage />} />

        {/* Authenticated routes with AppShell */}
        <Route element={<AppShell />}>
          <Route path="dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="assets" element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
          <Route path="cult">
            <Route index element={<Navigate to="/cult/agents" replace />} />
            <Route path="agents" element={<ProtectedRoute><AgentsPage /></ProtectedRoute>} />
            <Route path="skills" element={<ProtectedRoute><SkillsPage /></ProtectedRoute>} />
            <Route path="chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          </Route>
          <Route path="workflows" element={<ProtectedRoute><WorkflowsPage /></ProtectedRoute>} />
          <Route path="revisions/:id" element={<ProtectedRoute><RevisionPage /></ProtectedRoute>} />
          <Route path="workspaces/:id" element={<ProtectedRoute><WorkspacePage /></ProtectedRoute>} />
          <Route path="settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        </Route>
      </Routes>
    </Suspense>
  )
}
