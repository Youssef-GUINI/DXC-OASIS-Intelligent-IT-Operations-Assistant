import { useState } from 'react';
import { FileDown, FileText } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api, ApiError } from '@/lib/api';
import { formatDateTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Incident } from '@/lib/types';

export default function ReportsPage() {
  const notify = useToast();
  // Un identifiant par téléchargement en cours : plusieurs rapports peuvent
  // être demandés à la suite sans que tous les boutons se figent.
  const [pending, setPending] = useState<string | null>(null);

  const { data, error, loading } = useResource<Incident[]>(
    () => api.get<Incident[]>('/incidents?limit=50'),
    [],
  );

  async function download(key: string, path: string, filename: string, label: string) {
    setPending(key);
    try {
      await api.download(path, filename);
      notify({ title: `${label} downloaded`, detail: 'Check your downloads folder.' });
    } catch (caught) {
      notify({
        tone: 'error',
        title: `${label} could not be generated`,
        detail:
          caught instanceof ApiError
            ? caught.message
            : 'OASIS could not reach the storage environment.',
      });
    } finally {
      setPending(null);
    }
  }

  const incidents = data ?? [];

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Generate PDF reports for a single incident or for your whole storage environment."
      />

      <Card>
        <CardHeader
          title="Global report"
          subtitle="KPIs, capacity, backup jobs and open incidents across your storage environment."
        />
        <CardBody>
          <Button
            variant="primary"
            icon={<FileDown className="h-4 w-4" />}
            loading={pending === 'global'}
            onClick={() =>
              download('global', '/storage/reports/global', 'oasis-rapport-storage.pdf', 'Global report')
            }
          >
            Download global report (PDF)
          </Button>
          <p className="mt-3 text-[13px] text-ink-500">
            Data is read from the storage environment when you click — the report reflects its state
            at that moment, not a cached snapshot.
          </p>
        </CardBody>
      </Card>

      <Card className="mt-6">
        <CardHeader
          title="Incident reports"
          subtitle="One report per incident: diagnosis, recommendations, actions taken and the measurements behind them."
        />
        <CardBody>
          {loading && <Skeleton className="h-24" />}
          {error && <ErrorState message={error} />}
          {!loading && !error && incidents.length === 0 && (
            <EmptyState
              icon={<FileText className="h-5 w-5" />}
              title="No incident yet"
              description="Incident reports appear here once OASIS opens a ticket."
            />
          )}

          {incidents.length > 0 && (
            <ul className="divide-y divide-line">
              {incidents.map((incident) => (
                <li
                  key={incident.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-900">
                      <span className="text-ink-500">{incident.ticket_number}</span> {incident.title}
                    </p>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-ink-500">
                      <Badge tone={SEVERITY_TONE[incident.severity]}>
                        {humanize(incident.severity)}
                      </Badge>
                      <Badge tone={STATUS_TONE[incident.status]}>{humanize(incident.status)}</Badge>
                      <span>{incident.affected_system}</span>
                      <span>·</span>
                      <span>{formatDateTime(incident.created_at)}</span>
                    </p>
                  </div>
                  <Button
                    size="sm"
                    icon={<FileDown className="h-4 w-4" />}
                    loading={pending === incident.id}
                    onClick={() =>
                      download(
                        incident.id,
                        `/storage/reports/incidents/${incident.id}`,
                        `oasis-incident-${incident.ticket_number}.pdf`,
                        `Report ${incident.ticket_number}`,
                      )
                    }
                  >
                    Download PDF
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </>
  );
}
