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
import DataHubPage from '@/pages/DataHubPage';
import SettingsPage from '@/pages/SettingsPage';

function SplashScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Logo size={40} withWordmark subtitle="Loading your workspace…" />
    </div>
  );
}

/**
 * Cette version ne dessert qu'un seul espace de travail. Les autres rôles sont
 * renvoyés vers Storage plutôt que de se voir proposer une liste de personas.
 */
function RequireAuth() {
  const { user, initializing } = useAuth();
  if (initializing) return <SplashScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/storage" element={<RequireAuth />}>
              <Route index element={<Navigate to="/storage/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="incidents" element={<IncidentsPage />} />
              <Route path="requests" element={<RequestsPage />} />
              <Route path="data-hub" element={<DataHubPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/storage/dashboard" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
