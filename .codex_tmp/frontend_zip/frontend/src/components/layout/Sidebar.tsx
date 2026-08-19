import { NavLink } from 'react-router-dom';
import {
  Database,
  LayoutGrid,
  type LucideIcon,
  MessageSquare,
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
];

function NavRow({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'focus-ring flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive ? 'bg-brand-50 text-brand-700' : 'text-ink-500 hover:bg-slate-100 hover:text-ink-900',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-[18px] w-[18px] shrink-0', isActive && 'text-brand-500')} />
          {item.label}
        </>
      )}
    </NavLink>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const initials = (user?.full_name || 'Storage Engineer')
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  return (
    <div className="flex h-full flex-col border-r border-line bg-white">
      <div className="px-5 py-5">
        <Logo size={30} withWordmark subtitle="Storage Operations" />
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {NAV.map((item) => (
          <NavRow key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="space-y-1 border-t border-line p-3">
        <NavRow item={{ to: '/storage/settings', label: 'Settings', icon: Settings }} onNavigate={onNavigate} />

        <div className="flex items-center gap-3 rounded-lg px-3 py-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-[13px] font-semibold text-brand-700">
            {initials || 'SE'}
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-[13px] font-medium text-ink-900">
              Storage Engineer
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-ink-500">
              <span className="h-1.5 w-1.5 rounded-full bg-ok-500" />
              Online
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}
