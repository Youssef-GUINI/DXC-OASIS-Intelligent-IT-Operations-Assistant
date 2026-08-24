import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, ClipboardList, FileClock, ShieldAlert, Users } from 'lucide-react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { formatDateTime, formatRelativeTime, greeting, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { AccessRequest, AdminUser, AuditLog, LinuxKPIs } from '@/lib/types';

const SEVERITY_PALETTE: Record<string, string> = {
  critical: '#f0466f',
  high: '#eda32f',
  medium: '#6c4ce8',
  low: '#22c079',
};

function StatTile({
  icon: Icon,
  label,
  value,
  caption,
  tone = 'neutral',
}: {
  icon: typeof Users;
  label: string;
  value: string;
  caption?: string;
  tone?: 'neutral' | 'ok' | 'warn' | 'danger';
}) {
  const toneClass = {
    neutral: 'bg-brand-50 text-brand-600',
    ok: 'bg-ok-50 text-ok-600',
    warn: 'bg-warn-50 text-warn-600',
    danger: 'bg-danger-50 text-danger-600',
  }[tone];

  return (
    <article className="rounded-xl border border-line bg-white p-5 shadow-card">
      <span className={`inline-flex h-9 w-9 items-center justify-center rounded-full ${toneClass}`}>
        <Icon className="h-4 w-4" />
      </span>
      <p className="mt-3 text-[13px] font-medium text-ink-500">{label}</p>
      <p className="mt-1 text-[26px] font-semibold leading-none tracking-tight text-ink-900">{value}</p>
      {caption && <p className="mt-2 text-[12px] text-ink-500">{caption}</p>}
    </article>
  );
}

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const notify = useToast();

  const { data: users, loading: usersLoading } = useResource<AdminUser[]>(
    () => api.get<AdminUser[]>('/admin/users'),
    [],
  );
  const { data: pending, loading: pendingLoading, reload: reloadPending } = useResource<AccessRequest[]>(
    () => api.get<AccessRequest[]>('/cross-domain/requests/pending'),
    [],
  );
  const { data: kpis, loading: kpisLoading } = useResource<LinuxKPIs>(
    () => api.get<LinuxKPIs>('/linux/dashboard/kpis'),
    [],
  );
  const { data: audit, loading: auditLoading } = useResource<AuditLog[]>(
    () => api.get<AuditLog[]>('/admin/audit-logs?limit=8'),
    [],
  );

  const todayCount = (audit ?? []).filter((entry) => {
    const entryDate = new Date(entry.timestamp);
    const now = new Date();
    return (
      entryDate.getFullYear() === now.getFullYear() &&
      entryDate.getMonth() === now.getMonth() &&
      entryDate.getDate() === now.getDate()
    );
  }).length;

  const severityEntries = Object.entries(kpis?.incidents_by_severity ?? {}).sort((a, b) => b[1] - a[1]);
  const severityTotal = severityEntries.reduce((sum, [, count]) => sum + count, 0);

  async function decide(request: AccessRequest, approve: boolean) {
    try {
      await api.post(`/cross-domain/requests/${request.id}/decision`, { approve });
      notify({ title: approve ? `Request #${request.id} approved` : `Request #${request.id} rejected` });
      reloadPending();
    } catch (caught) {
      notify({ tone: 'error', title: "Couldn't update this request" });
    }
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <header className="mb-6">
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-900">{greeting()}, Administrator</h1>
        <p className="mt-1 text-sm text-ink-500">
          A platform-wide view — you oversee users, access and audit trail rather than operating a
          workspace directly.
        </p>
      </header>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {usersLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatTile icon={Users} label="Users" value={String(users?.length ?? 0)} caption="registered accounts" />
        )}
        {pendingLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatTile
            icon={ClipboardList}
            label="Pending Requests"
            value={String(pending?.length ?? 0)}
            caption="awaiting your decision"
            tone={pending && pending.length > 0 ? 'warn' : 'ok'}
          />
        )}
        {kpisLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatTile
            icon={ShieldAlert}
            label="Open Incidents (Linux)"
            value={String(kpis?.open_incidents ?? 0)}
            caption="only Linux workspace reports so far"
            tone={kpis && kpis.open_incidents > 0 ? 'warn' : 'ok'}
          />
        )}
        {auditLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <StatTile icon={FileClock} label="Audit Events Today" value={String(todayCount)} caption="requests logged today" />
        )}
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader title="Incidents by severity" subtitle="Linux workspace — platform-wide once Storage is merged." />
          <div className="flex items-center gap-4 px-5 pb-5 pt-2">
            {kpisLoading ? (
              <Skeleton className="h-[150px] w-[150px] rounded-full" />
            ) : severityTotal === 0 ? (
              <p className="py-8 text-center text-[13px] text-ink-500">No incident data yet.</p>
            ) : (
              <>
                <div className="relative h-[150px] w-[150px] shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={severityEntries.map(([name, value]) => ({ name, value }))}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={48}
                        outerRadius={70}
                        paddingAngle={2}
                        stroke="none"
                      >
                        {severityEntries.map(([name]) => (
                          <Cell key={name} fill={SEVERITY_PALETTE[name] ?? '#94a3b8'} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e9e6f7', fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-[22px] font-semibold leading-none text-ink-900">{severityTotal}</span>
                    <span className="text-[11px] text-ink-500">Total</span>
                  </div>
                </div>
                <ul className="min-w-0 flex-1 space-y-2">
                  {severityEntries.map(([name, count]) => (
                    <li key={name} className="flex items-center gap-2 text-[12.5px]">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: SEVERITY_PALETTE[name] ?? '#94a3b8' }}
                      />
                      <span className="min-w-0 flex-1 truncate text-ink-700">{humanize(name)}</span>
                      <span className="shrink-0 font-medium text-ink-900">{count}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between gap-3 px-5 pt-5">
            <div>
              <h3 className="card-title">Recent audit activity</h3>
              <p className="mt-0.5 text-[12.5px] text-ink-500">Every request handled by the API.</p>
            </div>
            <Link to="/admin/team" className="shrink-0 text-[13px] font-medium text-brand-600 hover:text-brand-700">
              View all
            </Link>
          </div>
          {auditLoading && (
            <div className="space-y-3 p-5">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-12" />
              ))}
            </div>
          )}
          {audit && audit.length === 0 && !auditLoading && <EmptyState title="No audit entries yet" />}
          {audit && audit.length > 0 && (
            <ul className="divide-y divide-line">
              {audit.map((entry) => (
                <li key={entry.id} className="flex items-start gap-3 px-5 py-3">
                  <span className="mt-0.5 shrink-0 font-mono text-[11px] text-ink-400">#{entry.id}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] font-medium text-ink-900">{entry.action}</span>
                    <span className="block text-[12px] text-ink-500">
                      {entry.user_id !== null ? `user #${entry.user_id}` : 'system'} · {formatDateTime(entry.timestamp)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <div className="flex items-start justify-between gap-3 px-5 pt-5">
          <div>
            <h3 className="card-title">Pending access requests</h3>
            <p className="mt-0.5 text-[12.5px] text-ink-500">Cross-domain access requests waiting for your decision.</p>
          </div>
          <Link to="/admin/requests" className="shrink-0 text-[13px] font-medium text-brand-600 hover:text-brand-700">
            View all
          </Link>
        </div>
        {pendingLoading && (
          <div className="space-y-3 p-5">
            {[0, 1].map((row) => (
              <Skeleton key={row} className="h-14" />
            ))}
          </div>
        )}
        {pending && pending.length === 0 && !pendingLoading && (
          <EmptyState icon={<CheckCircle2 className="h-7 w-7" />} title="Nothing pending" description="No access requests need your attention right now." />
        )}
        {pending && pending.length > 0 && (
          <ul className="divide-y divide-line">
            {pending.slice(0, 5).map((request) => (
              <li key={request.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                <AlertTriangle className="h-4 w-4 shrink-0 text-warn-500" />
                <span className="min-w-0 flex-1">
                  <span className="text-[13px] font-medium text-ink-900">
                    User #{request.requested_by_id} → {humanize(request.target_workspace)}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-ink-400">
                    requested {formatRelativeTime(request.created_at)}
                  </span>
                </span>
                <span className="flex shrink-0 gap-2">
                  <Button size="sm" onClick={() => void decide(request, true)}>Approve</Button>
                  <Button size="sm" variant="secondary" onClick={() => void decide(request, false)}>Reject</Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}