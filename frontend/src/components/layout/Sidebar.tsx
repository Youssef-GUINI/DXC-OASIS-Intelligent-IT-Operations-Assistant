import { NavLink } from 'react-router-dom';
import {
  Database,
  FileText,
  LayoutGrid,
  type LucideIcon,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  ShieldAlert,
  ClipboardList,
} from 'lucide-react';
import { Logo } from '@/components/Logo';
import { cn } from '@/lib/cn';
import { useAuth } from '@/auth/AuthContext';

type NavItem = { to: string; label: string; icon: LucideIcon };

const NAV: NavItem[] = [
  { to: '/storage/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/storage/chat', label: 'Chat', icon: MessageSquare },
  { to: '/storage/incidents', label: 'Incidents', icon: ShieldAlert },
  { to: '/storage/requests', label: 'Requests', icon: ClipboardList },
  { to: '/storage/data-hub', label: 'Data Hub', icon: Database },
  { to: '/storage/reports', label: 'Reports', icon: FileText },
];

function NavRow({
  item,
  collapsed = false,
  onNavigate,
}: {
  item: NavItem;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      // Replié, l'icône seule ne dit pas où elle mène : le libellé reste
      // accessible en infobulle et pour les lecteurs d'écran.
      title={collapsed ? item.label : undefined}
      aria-label={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'focus-ring flex items-center rounded-lg py-2 text-sm font-medium transition-colors',
          collapsed ? 'justify-center px-0' : 'gap-3 px-3',
          isActive ? 'bg-brand-50 text-brand-700' : 'text-ink-500 hover:bg-slate-100 hover:text-ink-900',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-[18px] w-[18px] shrink-0', isActive && 'text-brand-500')} />
          {!collapsed && item.label}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar({
  collapsed = false,
  onToggle,
  onNavigate,
}: {
  collapsed?: boolean;
  /** Absent dans le tiroir mobile : on l'y ferme par le fond, pas en le repliant. */
  onToggle?: () => void;
  onNavigate?: () => void;
}) {
  const { user } = useAuth();
  const fullName = user?.full_name || 'Storage Engineer';
  const initials = fullName
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  const toggle = onToggle && (
    <button
      onClick={onToggle}
      aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      aria-expanded={!collapsed}
      title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      className="focus-ring rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-slate-100 hover:text-ink-700"
    >
      {collapsed ? (
        <PanelLeftOpen className="h-[18px] w-[18px]" />
      ) : (
        <PanelLeftClose className="h-[18px] w-[18px]" />
      )}
    </button>
  );

  return (
    <div className="flex h-full flex-col border-r border-line bg-white">
      <div className={cn('py-5', collapsed ? 'px-3' : 'px-5')}>
        {collapsed ? (
          <div className="flex flex-col items-center gap-3">
            <Logo variant="mark" size={26} />
            {toggle}
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2">
            <Logo size={14} withWordmark subtitle="Storage Operations" />
            {toggle}
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {NAV.map((item) => (
          <NavRow key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="space-y-1 border-t border-line p-3">
        <NavRow
          item={{ to: '/storage/settings', label: 'Settings', icon: Settings }}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />

        <div
          className={cn(
            'flex items-center rounded-lg py-2.5',
            collapsed ? 'justify-center px-0' : 'gap-3 px-3',
          )}
          title={collapsed ? `${fullName} — online` : undefined}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-[13px] font-semibold text-brand-700">
            {initials || 'SE'}
          </span>
          {!collapsed && (
            <span className="min-w-0 leading-tight">
              <span className="block truncate text-[13px] font-medium text-ink-900">
                Storage Engineer
              </span>
              <span className="flex items-center gap-1.5 text-[11px] text-ink-500">
                <span className="h-1.5 w-1.5 rounded-full bg-ok-500" />
                Online
              </span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
