import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import PapersPage from './pages/PapersPage'
import CultPage from './pages/CultPage'
import WorkspacePage from './pages/WorkspacePage'
import WorkflowsPage from './pages/WorkflowsPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="papers" element={<ProtectedRoute><PapersPage /></ProtectedRoute>} />
        <Route path="cult" element={<ProtectedRoute><CultPage /></ProtectedRoute>} />
        <Route path="workflows" element={<ProtectedRoute><WorkflowsPage /></ProtectedRoute>} />
        <Route path="workspaces/:id" element={<ProtectedRoute><WorkspacePage /></ProtectedRoute>} />
        <Route path="settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      </Route>
    </Routes>
  )
}
