import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, HelpCircle, LogOut, Menu, Search, Settings } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { cn } from '@/lib/cn';

function useDismissOnOutsideClick(onDismiss: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onDismiss();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onDismiss]);
  return ref;
}

export function Topbar({
  onOpenMenu,
  attentionCount = 0,
}: {
  onOpenMenu: () => void;
  attentionCount?: number;
}) {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useDismissOnOutsideClick(() => setMenuOpen(false));

  const initials = (user?.full_name || 'Storage Engineer')
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-line bg-white/85 px-4 backdrop-blur-md sm:px-6">
      <button
        onClick={onOpenMenu}
        aria-label="Open navigation"
        className="focus-ring rounded-lg p-2 text-ink-500 hover:bg-slate-100 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
        <input
          type="search"
          placeholder="Search storage resources, incidents, volumes..."
          className="h-9 w-full rounded-lg border border-line bg-canvas pl-9 pr-3 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
      </div>

      <div className="ml-auto flex items-center gap-0.5">
        <Link
          to="/storage/incidents"
          aria-label="Notifications"
          className="focus-ring relative rounded-lg p-2 text-ink-500 transition-colors hover:bg-slate-100 hover:text-ink-900"
        >
          <Bell className="h-[18px] w-[18px]" />
          {attentionCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-semibold text-white">
              {attentionCount > 9 ? '9+' : attentionCount}
            </span>
          )}
        </Link>

        <button
          aria-label="Help"
          className="focus-ring rounded-lg p-2 text-ink-500 transition-colors hover:bg-slate-100 hover:text-ink-900"
        >
          <HelpCircle className="h-[18px] w-[18px]" />
        </button>

        <div className="relative ml-1" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            className={cn(
              'focus-ring flex items-center gap-2.5 rounded-lg py-1.5 pl-1.5 pr-2.5 transition-colors hover:bg-slate-100',
              menuOpen && 'bg-slate-100',
            )}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-[12px] font-semibold text-brand-700">
              {initials || 'SE'}
            </span>
            <span className="hidden text-left leading-tight sm:block">
              <span className="block text-[13px] font-medium text-ink-900">Storage Engineer</span>
              <span className="block text-[11px] text-ink-500">{user?.email}</span>
            </span>
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-56 overflow-hidden rounded-xl border border-line bg-white py-1 shadow-lift animate-fade-up">
              <div className="border-b border-line px-3 py-2.5">
                <p className="truncate text-[13px] font-medium text-ink-900">{user?.full_name}</p>
                <p className="truncate text-[12px] text-ink-500">{user?.email}</p>
              </div>
              <Link
                to="/storage/settings"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-[13px] text-ink-700 hover:bg-slate-50"
              >
                <Settings className="h-4 w-4 text-ink-400" />
                Settings
              </Link>
              <button
                onClick={signOut}
                className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[13px] text-ink-700 hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4 text-ink-400" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
