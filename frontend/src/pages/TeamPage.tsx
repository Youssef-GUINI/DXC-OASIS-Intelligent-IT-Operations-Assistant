import { useState } from 'react';
import { FileClock, Lock, ShieldCheck, Tags, Users } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useAuth } from '@/auth/AuthContext';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDateTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { AdminUser, AdminRole, AuditLog } from '@/lib/types';

type Tab = 'users' | 'roles' | 'audit';

const TABS: { key: Tab; label: string; icon: typeof Users }[] = [
  { key: 'users', label: 'Users', icon: Users },
  { key: 'roles', label: 'Roles', icon: Tags },
  { key: 'audit', label: 'Audit Logs', icon: FileClock },
];

function roleBadgeTone(role: string): 'brand' | 'ok' | 'neutral' {
  if (role === 'administrator') return 'brand';
  if (role === 'linux_engineer' || role === 'storage_engineer') return 'ok';
  return 'neutral';
}

function UsersTab() {
  const { data, error, loading, reload } = useResource<AdminUser[]>(
    () => api.get<AdminUser[]>('/admin/users'),
    [],
  );

  return (
    <Card>
      <CardHeader title="Users" subtitle="Everyone with an account on this platform." />
      {loading && (
        <div className="space-y-3 p-5">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} className="h-12" />
          ))}
        </div>
      )}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && !loading && <EmptyState title="No users found" />}
      {data && data.length > 0 && (
        <ul className="divide-y divide-line">
          {data.map((user) => (
            <li key={user.id} className="flex items-center gap-3 px-5 py-3.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-[12px] font-semibold text-brand-700">
                {user.full_name
                  .split(' ')
                  .slice(0, 2)
                  .map((p: string) => p.charAt(0).toUpperCase())
                  .join('')}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13px] font-medium text-ink-900">{user.full_name}</span>
                <span className="block truncate text-[12px] text-ink-500">{user.email}</span>
              </span>
              <Badge tone={roleBadgeTone(user.role)}>{humanize(user.role)}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function RolesTab() {
  const { data, error, loading, reload } = useResource<AdminRole[]>(
    () => api.get<AdminRole[]>('/admin/roles'),
    [],
  );

  return (
    <Card>
      <CardHeader title="Roles" subtitle="Roles available for user accounts." />
      {loading && (
        <div className="space-y-3 p-5">
          {[0, 1].map((row) => (
            <Skeleton key={row} className="h-12" />
          ))}
        </div>
      )}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && !loading && <EmptyState title="No roles found" />}
      {data && data.length > 0 && (
        <ul className="divide-y divide-line">
          {data.map((role) => (
            <li key={role.id} className="flex items-center gap-3 px-5 py-3.5">
              <ShieldCheck className="h-4 w-4 shrink-0 text-ink-400" />
              <span className="flex-1 text-[13px] font-medium text-ink-900">{humanize(role.name)}</span>
              <span className="font-mono text-[11px] text-ink-400">#{role.id}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function AuditTab() {
  const { data, error, loading, reload } = useResource<AuditLog[]>(
    () => api.get<AuditLog[]>('/admin/audit-logs?limit=100'),
    [],
  );

  return (
    <Card>
      <CardHeader title="Audit logs" subtitle="Every request handled by the API, most recent first." />
      {loading && (
        <div className="space-y-3 p-5">
          {[0, 1, 2, 3].map((row) => (
            <Skeleton key={row} className="h-14" />
          ))}
        </div>
      )}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && !loading && <EmptyState title="No audit entries yet" />}
      {data && data.length > 0 && (
        <ul className="divide-y divide-line">
          {data.map((entry) => (
            <li key={entry.id} className="flex items-start gap-3 px-5 py-3">
              <span className="mt-0.5 shrink-0 font-mono text-[11px] text-ink-400">#{entry.id}</span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-medium text-ink-900">{entry.action}</span>
                  {entry.resource && (
                    <span className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[11px] text-ink-500">
                      {entry.resource}
                    </span>
                  )}
                </span>
                <span className="mt-0.5 block text-[12px] text-ink-500">
                  {entry.user_id !== null ? `user #${entry.user_id}` : 'system'} · {formatDateTime(entry.timestamp)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function TeamPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('users');

  if (user?.role !== 'administrator') {
    return (
      <div className="mx-auto max-w-[600px]">
        <EmptyState
          icon={<Lock className="h-7 w-7" />}
          title="Administrators only"
          description="This workspace is restricted to accounts with the administrator role."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1000px]">
      <PageHeader title="Team" subtitle="Users, roles and platform audit trail." />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {TABS.map((option) => {
          const Icon = option.icon;
          return (
            <button
              key={option.key}
              onClick={() => setTab(option.key)}
              className={cn(
                'focus-ring flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors',
                tab === option.key
                  ? 'bg-brand-500 text-white'
                  : 'border border-line bg-white text-ink-700 hover:bg-slate-50',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {option.label}
            </button>
          );
        })}
      </div>

      {tab === 'users' && <UsersTab />}
      {tab === 'roles' && <RolesTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  );
}