import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Download, Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE, StatusDot } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { LinuxIncidentApi } from '@/lib/types';

type Filter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'resolved';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'critical', label: 'Critical' },
  { key: 'high', label: 'High' },
  { key: 'medium', label: 'Medium' },
  { key: 'low', label: 'Low' },
  { key: 'resolved', label: 'Resolved' },
];

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function IncidentsPage() {
  const notify = useToast();
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<LinuxIncidentApi | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data, error, loading, reload } = useResource<LinuxIncidentApi[]>(
    () => api.get<LinuxIncidentApi[]>('/linux/incidents'),
    [],
  );

  const incidents = (data ?? []).filter((incident) => {
    if (filter === 'all') return true;
    if (filter === 'resolved') return incident.status === 'resolved';
    return incident.severity === filter;
  });

  async function resolveIncident(incident: LinuxIncidentApi) {
    setBusy(`resolve-${incident.id}`);
    try {
      const updated = await api.patch<LinuxIncidentApi>(`/linux/incidents/${incident.id}/resolve`, {});
      setSelected(updated);
      notify({ title: `Incident ${incident.id} marked as resolved` });
      reload();
    } finally {
      setBusy(null);
    }
  }

  async function downloadReport(incident: LinuxIncidentApi) {
    setBusy(`report-${incident.id}`);
    try {
      const blob = await api.download(`/linux/incidents/${incident.id}/report`, { method: 'POST' });
      saveBlob(blob, `rapport_incident_${incident.id}.pdf`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="Linux Incidents"
        subtitle="Monitor backend incidents and investigate them with the Linux AI agent."
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
              <Skeleton key={row} className="h-16" />
            ))}
          </div>
        )}

        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data && !loading && incidents.length === 0 && (
          <EmptyState
            title="No incidents for this filter"
            description="Try another filter or wait for the backend monitoring scheduler."
          />
        )}

        {incidents.length > 0 && (
          <ul className="divide-y divide-line">
            {incidents.map((incident) => (
              <li key={incident.id}>
                <button
                  onClick={() => setSelected(incident)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50"
                >
                  <StatusDot tone={SEVERITY_TONE[incident.severity ?? 'info'] ?? 'neutral'} className="shrink-0" />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-[14px] font-medium text-ink-900">
                        {incident.user_message || incident.response}
                      </span>
                      <span className="font-mono text-[11px] text-ink-400">INC-{incident.id}</span>
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-ink-500">
                      {incident.category ?? incident.source} - raised {formatRelativeTime(incident.created_at)}
                    </span>
                  </span>
                  <span className="hidden shrink-0 items-center gap-2 sm:flex">
                    <Badge tone={SEVERITY_TONE[incident.severity ?? 'info'] ?? 'neutral'}>
                      {incident.severity ?? 'info'}
                    </Badge>
                    <Badge tone={STATUS_TONE[incident.status] ?? 'neutral'}>{incident.status.replace('_', ' ')}</Badge>
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
        title={selected ? `Incident INC-${selected.id}` : ''}
        subtitle={
          selected && (
            <span className="flex flex-wrap items-center gap-2">
              <Badge tone={SEVERITY_TONE[selected.severity ?? 'info'] ?? 'neutral'}>{selected.severity ?? 'info'}</Badge>
              <Badge tone={STATUS_TONE[selected.status] ?? 'neutral'}>{selected.status.replace('_', ' ')}</Badge>
              <span className="text-[12px] text-ink-500">{selected.category ?? selected.source}</span>
            </span>
          )
        }
        footer={
          selected && (
            <>
              <Button
                variant="primary"
                icon={<Sparkles className="h-4 w-4" />}
                onClick={() => navigate('/linux/chat')}
              >
                Investigate with AI
              </Button>
              <Button
                icon={<Download className="h-4 w-4" />}
                loading={busy === `report-${selected.id}`}
                onClick={() => void downloadReport(selected)}
              >
                Download Report
              </Button>
              {selected.status !== 'resolved' && (
                <Button
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  loading={busy === `resolve-${selected.id}`}
                  onClick={() => void resolveIncident(selected)}
                >
                  Resolve
                </Button>
              )}
            </>
          )
        }
      >
        {selected && (
          <div className="space-y-4">
            <Card>
              <div className="p-5">
                <h3 className="card-title">What happened</h3>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-ink-700">
                  {selected.user_message || selected.response}
                </p>
              </div>
            </Card>
            <Card className="border-accent-200 bg-accent-50">
              <div className="p-5">
                <h3 className="flex items-center gap-2 card-title">
                  <Sparkles className="h-4 w-4 text-accent-500" />
                  OASIS Analysis
                </h3>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-ink-700">
                  {selected.diagnosis ?? selected.response}
                </p>
              </div>
            </Card>
            <Card>
              <div className="p-5">
                <h3 className="card-title">Incident metadata</h3>
                <dl className="mt-3 grid gap-3 text-[13px] sm:grid-cols-2">
                  <div>
                    <dt className="text-ink-400">Source</dt>
                    <dd className="font-medium text-ink-800">{selected.source}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400">Created</dt>
                    <dd className="font-medium text-ink-800">{formatRelativeTime(selected.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400">Persona</dt>
                    <dd className="font-medium text-ink-800">{selected.persona}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400">Resolved</dt>
                    <dd className="font-medium text-ink-800">
                      {selected.resolved_at ? formatRelativeTime(selected.resolved_at) : 'Not resolved yet'}
                    </dd>
                  </div>
                </dl>
              </div>
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
}
