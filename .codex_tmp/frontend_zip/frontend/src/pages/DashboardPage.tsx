import { Archive, HardDrive, HeartPulse, ShieldAlert } from 'lucide-react';
import { AttentionBanner } from '@/components/dashboard/AttentionBanner';
import { BackupHealthCard, CapacityOverview } from '@/components/dashboard/CapacityOverview';
import { KpiCard, KpiCardSkeleton } from '@/components/dashboard/KpiCard';
import { OasisInsights } from '@/components/dashboard/OasisInsights';
import { PerformanceChart } from '@/components/dashboard/PerformanceChart';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { api } from '@/lib/api';
import { formatCapacity, greeting } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Overview } from '@/lib/types';

export default function DashboardPage() {
  const { data, error, loading, reload } = useResource<Overview>(
    () => api.get<Overview>('/storage/dashboard/overview'),
    [],
  );

  return (
    <div className="mx-auto max-w-[1400px]">
      <header className="mb-6">
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-900">
          {greeting()}, Storage Engineer 👋
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Here's what's happening across your storage environment today.
        </p>
      </header>

      {/* Niveau 1 — ce qui réclame l'attention */}
      {loading && <Skeleton className="h-[92px] rounded-card" />}
      {error && !loading && (
        <div className="card">
          <ErrorState message={error} onRetry={reload} />
        </div>
      )}
      {data && <AttentionBanner overview={data} />}

      {/* Niveau 2 — l'état courant */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading &&
          [0, 1, 2, 3].map((index) => <KpiCardSkeleton key={index} />)}

        {data && (
          <>
            <KpiCard
              label="Storage Capacity"
              value={
                data.capacity.unavailable ? '—' : formatCapacity(data.capacity.total_gb).split(' ')[0]
              }
              unit={
                data.capacity.unavailable ? undefined : formatCapacity(data.capacity.total_gb).split(' ')[1]
              }
              caption={
                data.capacity.unavailable
                  ? 'VM unreachable'
                  : `${data.capacity.percent_used}% in use`
              }
              icon={HardDrive}
              tone={
                data.capacity.percent_used >= 90
                  ? 'danger'
                  : data.capacity.percent_used >= 80
                    ? 'warn'
                    : 'neutral'
              }
            />

            <KpiCard
              label="Active Backups"
              value={data.backups.error ? '—' : String(data.backups.total)}
              caption={
                data.backups.error
                  ? 'VM unreachable'
                  : !data.backups.configured
                    ? 'No backup job set up yet'
                    : data.backups.failed > 0
                      ? `${data.backups.failed} need attention`
                      : 'All jobs completed'
              }
              icon={Archive}
              tone={
                data.backups.error
                  ? 'neutral'
                  : data.backups.failed > 0 || !data.backups.configured
                    ? 'warn'
                    : 'ok'
              }
            />

            <KpiCard
              label="Active Incidents"
              value={String(data.incidents.open)}
              caption={
                data.incidents.needs_attention > 0
                  ? `${data.incidents.needs_attention} high or critical`
                  : `${data.incidents.resolved_last_7d} resolved this week`
              }
              icon={ShieldAlert}
              tone={data.incidents.needs_attention > 0 ? 'danger' : 'ok'}
            />

            <KpiCard
              label="Storage Health"
              value={data.health_score === null ? '—' : String(data.health_score)}
              unit={data.health_score === null ? undefined : '/ 100'}
              caption={
                data.health_score === null
                  ? "Can't measure while the VM is unreachable"
                  : data.overall_status === 'healthy'
                    ? 'Everything within thresholds'
                    : `${data.alerts.length} open alert${data.alerts.length > 1 ? 's' : ''}`
              }
              icon={HeartPulse}
              tone={
                data.overall_status === 'critical'
                  ? 'danger'
                  : data.overall_status === 'warning'
                    ? 'warn'
                    : data.overall_status === 'unknown'
                      ? 'neutral'
                      : 'ok'
              }
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <PerformanceChart />
        </div>
        <div className="space-y-4">
          {loading && <Skeleton className="h-[300px] rounded-card" />}
          {data && <CapacityOverview capacity={data.capacity} />}
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        {loading && <Skeleton className="h-[200px] rounded-card" />}
        {data && <BackupHealthCard backups={data.backups} />}

        {/* Niveau 3 — ce qui s'est passé récemment */}
        <div className="xl:col-span-2">
          <RecentActivity />
        </div>
      </div>

      {/* Niveau 4 — ce qu'il faudrait faire */}
      <div className="mt-4">
        <OasisInsights />
      </div>
    </div>
  );
}
