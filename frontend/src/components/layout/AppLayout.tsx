import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { Topbar, type Notification } from '@/components/layout/Topbar';
import { SEVERITY_TONE } from '@/components/ui/Badge';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Overview } from '@/lib/types';

/** Le pli de la barre latérale est un réglage d'espace de travail : il suit
 *  l'utilisateur d'une session à l'autre plutôt que de se réinitialiser à
 *  chaque rechargement. */
const COLLAPSED_KEY = 'oasis.sidebar.collapsed';

export function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSED_KEY) === 'true',
  );
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem(COLLAPSED_KEY, String(collapsed));
  }, [collapsed]);

  // La pastille de notification suit le nombre de sujets réellement urgents.
  const { data: overview } = useResource<Overview>(
    () => api.get<Overview>('/storage/dashboard/overview'),
    [],
  );

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  // Chaque ligne du panneau est cliquable et mène là où le sujet se traite.
  // La pastille compte exactement ce que le panneau affiche : auparavant elle
  // additionnait les sauvegardes en échec, que la page Incidents ne montre
  // pas — on cliquait sur « 2 » pour ne trouver qu'un seul élément.
  const notifications: Notification[] = [];

  for (const alert of overview?.alerts ?? []) {
    notifications.push({
      id: `${alert.type}:${alert.target ?? ''}`,
      title: alert.message,
      detail: humanize(alert.type),
      tone: SEVERITY_TONE[alert.severity] ?? 'warn',
      // Capacité et sauvegardes se lisent sur le dashboard : il n'existe pas
      // de page dédiée aux volumes. L'ancre amène directement sur la carte,
      // sinon on atterrit en haut de page sans savoir quoi regarder.
      to: alert.type.startsWith('backup')
        ? '/storage/dashboard#backup-health'
        : '/storage/dashboard#capacity',
    });
  }

  const needsAttention = overview?.incidents.needs_attention ?? 0;
  if (needsAttention > 0) {
    notifications.push({
      id: 'incidents:needs-attention',
      title:
        needsAttention > 1
          ? `${needsAttention} incidents need your attention`
          : '1 incident needs your attention',
      detail: 'Critical and high severity, still open',
      tone: 'danger',
      to: '/storage/incidents',
    });
  }

  return (
    <div className="flex min-h-screen">
      {/* La largeur est portée deux fois : par le bloc en flux, qui réserve
          la place, et par le panneau fixe qui l'occupe. */}
      <aside
        className={cn(
          'hidden shrink-0 transition-[width] duration-200 lg:block',
          collapsed ? 'w-[72px]' : 'w-64',
        )}
      >
        <div
          className={cn(
            'fixed inset-y-0 transition-[width] duration-200',
            collapsed ? 'w-[72px]' : 'w-64',
          )}
        >
          <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
        </div>
      </aside>

      {mobileNavOpen && (
        <div className="lg:hidden">
          <div
            onClick={() => setMobileNavOpen(false)}
            className="fixed inset-0 z-40 bg-ink-900/25 backdrop-blur-[2px]"
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 z-50 w-64 shadow-lift">
            <Sidebar onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMenu={() => setMobileNavOpen(true)} notifications={notifications} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
