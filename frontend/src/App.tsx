import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/auth/AuthContext';
import { ToastProvider } from '@/components/ui/Toast';
import { AppLayout } from '@/components/layout/AppLayout';
import { Logo } from '@/components/Logo';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ChatPage from '@/pages/ChatPage';
import IncidentsPage from '@/pages/IncidentsPage';
import RequestsPage from '@/pages/RequestsPage';
import ReportsPage from '@/pages/ReportsPage';
import DataHubPage from '@/pages/DataHubPage';
import TeamPage from '@/pages/TeamPage';
import AdminDashboardPage from '@/pages/AdminDashboardPage';
import SettingsPage from '@/pages/SettingsPage';

function SplashScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Logo size={40} withWordmark subtitle="Loading your workspace..." />
    </div>
  );
}

/** Workspace Linux : reserve aux linux_engineer et storage_engineer, jamais aux admins. */
function RequireLinuxWorkspace() {
  const { user, initializing } = useAuth();
  if (initializing) return <SplashScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'administrator') return <Navigate to="/admin/dashboard" replace />;
  return <AppLayout variant="linux" />;
}

/** Workspace Admin : reserve exclusivement aux administrator. */
function RequireAdminWorkspace() {
  const { user, initializing } = useAuth();
  if (initializing) return <SplashScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'administrator') return <Navigate to="/linux/dashboard" replace />;
  return <AppLayout variant="admin" />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Workspace Linux */}
            <Route path="/linux" element={<RequireLinuxWorkspace />}>
              <Route index element={<Navigate to="/linux/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="incidents" element={<IncidentsPage />} />
              <Route path="requests" element={<RequestsPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="data-hub" element={<DataHubPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Workspace Admin - composants partages avec Linux (memes donnees
                backend pour l'instant), mais layout et navigation separes. */}
            <Route path="/admin" element={<RequireAdminWorkspace />}>
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="incidents" element={<IncidentsPage />} />
              <Route path="requests" element={<RequestsPage />} />
              <Route path="team" element={<TeamPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}