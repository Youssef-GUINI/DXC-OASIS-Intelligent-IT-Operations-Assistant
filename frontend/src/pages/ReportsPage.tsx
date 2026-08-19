import { useState } from 'react';
import { Download, FileText, RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { api } from '@/lib/api';
import { formatRelativeTime } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { LinuxIncidentApi } from '@/lib/types';

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

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);
  const { data, error, loading, reload } = useResource<LinuxIncidentApi[]>(
    () => api.get<LinuxIncidentApi[]>('/linux/incidents'),
    [],
  );

  async function downloadGlobalReport() {
    setDownloading('global');
    try {
      const blob = await api.download('/linux/reports/global', { method: 'POST' });
      saveBlob(blob, 'rapport_global_linux.pdf');
    } finally {
      setDownloading(null);
    }
  }

  async function downloadIncidentReport(incidentId: number) {
    setDownloading(String(incidentId));
    try {
      const blob = await api.download(`/linux/incidents/${incidentId}/report`, { method: 'POST' });
      saveBlob(blob, `rapport_incident_${incidentId}.pdf`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        title="Reports"
        subtitle="Generate PDF reports from the Linux backend."
        action={
          <Button
            variant="primary"
            icon={<Download className="h-4 w-4" />}
            loading={downloading === 'global'}
            onClick={() => void downloadGlobalReport()}
          >
            Download Global Report
          </Button>
        }
      />

      <Card>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <h2 className="card-title">Incident Reports</h2>
            <p className="card-sub">Choose an incident and download its PDF report.</p>
          </div>
          <Button size="sm" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={reload}>
            Refresh
          </Button>
        </div>

        {loading && (
          <div className="space-y-3 p-5">
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} className="h-16" />
            ))}
          </div>
        )}

        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data && !loading && data.length === 0 && (
          <EmptyState
            icon={<FileText className="h-7 w-7" />}
            title="No incidents yet"
            description="When the backend detects Linux incidents, their reports will appear here."
          />
        )}

        {data && data.length > 0 && (
          <ul className="divide-y divide-line">
            {data.map((incident) => (
              <li key={incident.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <FileText className="h-4 w-4" />
                </span>
                <div className="min-w-[220px] flex-1">
                  <p className="line-clamp-1 text-[14px] font-medium text-ink-900">
                    {incident.user_message || incident.response}
                  </p>
                  <p className="mt-0.5 text-[12px] text-ink-500">
                    INC-{incident.id} · {incident.category ?? 'linux'} · {formatRelativeTime(incident.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={SEVERITY_TONE[incident.severity ?? 'info'] ?? 'neutral'}>
                    {incident.severity ?? 'info'}
                  </Badge>
                  <Badge tone={STATUS_TONE[incident.status] ?? 'neutral'}>{incident.status}</Badge>
                </div>
                <Button
                  size="sm"
                  icon={<Download className="h-3.5 w-3.5" />}
                  loading={downloading === String(incident.id)}
                  onClick={() => void downloadIncidentReport(incident.id)}
                >
                  Download
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
