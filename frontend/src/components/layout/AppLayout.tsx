import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { AdminSidebar } from '@/components/layout/AdminSidebar';
import { Topbar } from '@/components/layout/Topbar';

export function AppLayout({ variant = 'linux' }: { variant?: 'linux' | 'admin' }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();
  const basePath = variant === 'admin' ? '/admin' : '/linux';

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 lg:block">
        <div className="fixed inset-y-0 w-64">
          {variant === 'admin' ? <AdminSidebar /> : <Sidebar />}
        </div>
      </aside>

      {mobileNavOpen && (
        <div className="lg:hidden">
          <div onClick={() => setMobileNavOpen(false)} className="fixed inset-0 z-40 bg-ink-900/25 backdrop-blur-[2px]" aria-hidden="true" />
          <div className="fixed inset-y-0 left-0 z-50 w-64 shadow-lift">
            {variant === 'admin' ? (
              <AdminSidebar onNavigate={() => setMobileNavOpen(false)} />
            ) : (
              <Sidebar onNavigate={() => setMobileNavOpen(false)} />
            )}
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMenu={() => setMobileNavOpen(true)} basePath={basePath} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}