import { NavLink } from 'react-router-dom';
import { ClipboardList, LayoutGrid, MessageSquare, Settings, ShieldAlert, Users, type LucideIcon } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { useAuth } from '@/auth/AuthContext';
import { cn } from '@/lib/cn';

type NavItem = { to: string; label: string; icon: LucideIcon };

const NAV: NavItem[] = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/admin/chat', label: 'AI Chat', icon: MessageSquare },
  { to: '/admin/incidents', label: 'Global Incidents', icon: ShieldAlert },
  { to: '/admin/requests', label: 'Requests', icon: ClipboardList },
  { to: '/admin/team', label: 'Team', icon: Users },
];

function NavRow({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'focus-ring flex h-10 items-center gap-3 rounded-lg px-3 text-[13px] font-medium transition-colors',
          isActive ? 'bg-brand-50 text-brand-700 shadow-sm' : 'text-ink-500 hover:bg-slate-100 hover:text-ink-900',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-[17px] w-[17px] shrink-0', isActive && 'text-brand-500')} />
          <span className="truncate">{item.label}</span>
        </>
      )}
    </NavLink>
  );
}

export function AdminSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const displayName = user?.full_name || 'Administrator';
  const initials = displayName
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  return (
    <div className="flex h-full flex-col border-r border-line bg-white px-3">
      <div className="px-2 py-5">
        <Logo size={30} withWordmark subtitle="Admin Workspace" />
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto pb-4">
        {NAV.map((item) => (
          <NavRow key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="mb-3 rounded-xl border border-line bg-canvas p-3">
        <p className="text-[11px] font-semibold text-ink-700">Admin Scope</p>
        <p className="mt-1 text-[11px] text-ink-500">
          Platform-wide view: incidents, access requests, users, roles and audit trail.
        </p>
        <p className="mt-2 text-[11px] font-medium text-brand-700">Backend connected</p>
      </div>

      <div className="space-y-1 border-t border-line py-3">
        <NavRow item={{ to: '/admin/settings', label: 'Settings', icon: Settings }} onNavigate={onNavigate} />
        <div className="flex items-center gap-3 rounded-lg px-3 py-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-[13px] font-semibold text-brand-700">
            {initials || 'AD'}
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-[13px] font-medium text-ink-900">{displayName}</span>
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