import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE, StatusDot } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDateTime, formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Incident } from '@/lib/types';

type Filter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'resolved';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'critical', label: 'Critical' },
  { key: 'high', label: 'High' },
  { key: 'medium', label: 'Medium' },
  { key: 'low', label: 'Low' },
  { key: 'resolved', label: 'Resolved' },
];

/** Le backend filtre soit par sévérité soit par statut — jamais les deux. */
function queryFor(filter: Filter): string {
  if (filter === 'all') return '';
  if (filter === 'resolved') return '?status=resolved';
  return `?severity=${filter}`;
}

export default function IncidentsPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<Incident | null>(null);
  const [resolving, setResolving] = useState(false);
  const navigate = useNavigate();
  const notify = useToast();

  const { data, error, loading, reload } = useResource<Incident[]>(
    () => api.get<Incident[]>(`/incidents${queryFor(filter)}`),
    [filter],
  );

  async function markResolved(incident: Incident) {
    setResolving(true);
    try {
      await api.patch<Incident>(`/incidents/${incident.id}`, { status: 'resolved' });
      notify({ title: 'Incident resolved', detail: `${incident.ticket_number} is now closed out.` });
      setSelected(null);
      reload();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't resolve this incident",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setResolving(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="Storage Incidents"
        subtitle="Monitor and investigate storage-related issues."
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {FILTERS.map((option) => (
          <button
            key={option.key}
            onClick={() => setFilter(option.key)}
            className={cn(
              'focus-ring rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors',
              filter === option.key
                ? 'bg-brand-500 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-slate-50',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      <Card>
        {loading && (
          <div className="space-y-3 p-5">
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} className="h-14" />
            ))}
          </div>
        )}

        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data && !loading && data.length === 0 && (
          <EmptyState
            icon={<ShieldCheck className="h-7 w-7" />}
            title={filter === 'all' ? 'No incidents right now' : `No ${filter} incidents`}
            description="OASIS raises a ticket automatically when it detects something serious. Quiet here is good news."
          />
        )}

        {data && data.length > 0 && (
          <ul className="divide-y divide-line">
            {data.map((incident) => (
              <li key={incident.id}>
                <button
                  onClick={() => setSelected(incident)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50"
                >
                  <StatusDot
                    tone={SEVERITY_TONE[incident.severity] ?? 'neutral'}
                    className="shrink-0"
                  />

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-[14px] font-medium text-ink-900">
                        {incident.title}
                      </span>
                      <span className="font-mono text-[11px] text-ink-400">
                        {incident.ticket_number}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-ink-500">
                      {incident.affected_system} · raised {formatRelativeTime(incident.created_at)}
                    </span>
                  </span>

                  <span className="hidden shrink-0 items-center gap-2 sm:flex">
                    <Badge tone={SEVERITY_TONE[incident.severity] ?? 'neutral'}>
                      {incident.severity}
                    </Badge>
                    <Badge tone={STATUS_TONE[incident.status] ?? 'neutral'}>
                      {humanize(incident.status)}
                    </Badge>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Drawer
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected?.title ?? ''}
        subtitle={
          selected && (
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[12px]">{selected.ticket_number}</span>
              <Badge tone={SEVERITY_TONE[selected.severity] ?? 'neutral'}>{selected.severity}</Badge>
              <Badge tone={STATUS_TONE[selected.status] ?? 'neutral'}>
                {humanize(selected.status)}
              </Badge>
            </span>
          )
        }
        footer={
          selected && (
            <>
              <Button
                variant="primary"
                icon={<Sparkles className="h-4 w-4" />}
                onClick={() => navigate('/storage/chat')}
              >
                Investigate with OASIS
              </Button>
              <Button onClick={() => navigate('/storage/requests')}>Create Request</Button>
              {selected.status !== 'resolved' && selected.status !== 'closed' && (
                <Button
                  variant="secondary"
                  loading={resolving}
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  onClick={() => void markResolved(selected)}
                >
                  Mark as Resolved
                </Button>
              )}
            </>
          )
        }
      >
        {selected && <IncidentDetail incident={selected} />}
      </Drawer>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[12px] text-ink-500">{label}</dt>
      <dd className="mt-0.5 text-[13px] font-medium text-ink-900">{value}</dd>
    </div>
  );
}

function IncidentDetail({ incident }: { incident: Incident }) {
  return (
    <div className="space-y-4">
      <Card>
        <dl className="grid grid-cols-2 gap-4 p-5">
          <DetailRow label="Affected resource" value={incident.affected_system} />
          <DetailRow label="Raised" value={formatDateTime(incident.created_at)} />
          <DetailRow label="Status" value={humanize(incident.status)} />
          <DetailRow
            label="Resolved"
            value={incident.resolved_at ? formatDateTime(incident.resolved_at) : 'Not yet'}
          />
        </dl>
      </Card>

      <Card>
        <div className="p-5">
          <h3 className="card-title">What happened</h3>
          <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-ink-700">
            {incident.description}
          </p>
        </div>
      </Card>

      {(incident.root_cause || incident.impact_summary) && (
        <Card className="border-accent-200 bg-accent-50">
          <div className="p-5">
            <h3 className="flex items-center gap-2 card-title">
              <Sparkles className="h-4 w-4 text-accent-500" />
              OASIS Analysis
            </h3>
            {incident.root_cause && (
              <div className="mt-3">
                <p className="text-[12px] font-medium uppercase tracking-wide text-accent-600">
                  Likely root cause
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">
                  {incident.root_cause}
                </p>
              </div>
            )}
            {incident.impact_summary && (
              <div className="mt-3">
                <p className="text-[12px] font-medium uppercase tracking-wide text-accent-600">
                  Impact
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">
                  {incident.impact_summary}
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {incident.recommendations.length > 0 && (
        <Card>
          <div className="p-5">
            <h3 className="card-title">Recommended next steps</h3>
            <ol className="mt-3 space-y-2.5">
              {incident.recommendations.map((recommendation, index) => (
                <li key={index} className="flex gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-700">
                    {recommendation.order ?? index + 1}
                  </span>
                  <span className="text-[13px] leading-relaxed text-ink-700">
                    {recommendation.description ?? JSON.stringify(recommendation)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </Card>
      )}
    </div>
  );
}
