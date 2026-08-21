import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, HelpCircle, LogOut, Menu, Settings } from 'lucide-react';
import { GlobalSearch } from '@/components/layout/GlobalSearch';
import { useAuth } from '@/auth/AuthContext';
import { cn } from '@/lib/cn';
import type { Tone } from '@/components/ui/Badge';

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

/** Une ligne du panneau de notifications, déjà résolue vers sa destination. */
export type Notification = {
  id: string;
  title: string;
  detail?: string | null;
  tone: Tone;
  to: string;
};

const TONE_DOT: Record<Tone, string> = {
  neutral: 'bg-ink-300',
  brand: 'bg-brand-500',
  ok: 'bg-ok-500',
  warn: 'bg-warn-500',
  danger: 'bg-danger-500',
};

export function Topbar({
  onOpenMenu,
  notifications = [],
}: {
  onOpenMenu: () => void;
  notifications?: Notification[];
}) {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const menuRef = useDismissOnOutsideClick(() => setMenuOpen(false));
  const bellRef = useDismissOnOutsideClick(() => setBellOpen(false));

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

      <GlobalSearch />

      <div className="ml-auto flex items-center gap-0.5">
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen((open) => !open)}
            aria-label="Notifications"
            aria-expanded={bellOpen}
            className={cn(
              'focus-ring relative rounded-lg p-2 text-ink-500 transition-colors hover:bg-slate-100 hover:text-ink-900',
              bellOpen && 'bg-slate-100 text-ink-900',
            )}
          >
            <Bell className="h-[18px] w-[18px]" />
            {notifications.length > 0 && (
              <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-semibold text-white">
                {notifications.length > 9 ? '9+' : notifications.length}
              </span>
            )}
          </button>

          {bellOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-80 overflow-hidden rounded-xl border border-line bg-white shadow-lift animate-fade-up">
              <div className="border-b border-line px-3 py-2.5">
                <p className="text-[13px] font-medium text-ink-900">Notifications</p>
                <p className="text-[11px] text-ink-500">
                  {notifications.length > 0
                    ? 'What needs your attention right now.'
                    : 'Everything is quiet.'}
                </p>
              </div>

              {notifications.length === 0 ? (
                <p className="px-3 py-6 text-center text-[13px] text-ink-500">
                  Nothing needs your attention.
                </p>
              ) : (
                <ul className="max-h-80 overflow-y-auto">
                  {notifications.map((notification) => (
                    <li key={notification.id}>
                      <Link
                        to={notification.to}
                        onClick={() => setBellOpen(false)}
                        className="flex gap-2.5 border-b border-line px-3 py-2.5 last:border-b-0 hover:bg-slate-50"
                      >
                        <span
                          className={cn(
                            'mt-1.5 h-2 w-2 shrink-0 rounded-full',
                            TONE_DOT[notification.tone],
                          )}
                        />
                        <span className="min-w-0">
                          <span className="block text-[13px] text-ink-900">
                            {notification.title}
                          </span>
                          {notification.detail && (
                            <span className="block truncate text-[11px] text-ink-500">
                              {notification.detail}
                            </span>
                          )}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

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
