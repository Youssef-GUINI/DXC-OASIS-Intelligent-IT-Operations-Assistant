import { Link } from 'react-router-dom';
import { Activity, PlayCircle, ShieldAlert } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge, STATUS_TONE } from '@/components/ui/Badge';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { api } from '@/lib/api';
import { formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { ActivityItem } from '@/lib/types';

export function RecentActivity() {
  const { data, error, loading, reload } = useResource<ActivityItem[]>(
    () => api.get<ActivityItem[]>('/storage/dashboard/activity?limit=6'),
    [],
  );

  return (
    <Card>
      <CardHeader
        title="Recent Storage Activity"
        subtitle="What has happened across your environment"
        action={
          <Link
            to="/storage/incidents"
            className="text-[13px] font-medium text-brand-600 hover:text-brand-700"
          >
            View all
          </Link>
        }
      />

      {loading && (
        <div className="space-y-3 p-5">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-lg" />
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      )}

      {error && !loading && <ErrorState message={error} onRetry={reload} />}

      {data && !loading && data.length === 0 && (
        <EmptyState
          icon={<Activity className="h-6 w-6" />}
          title="Nothing has happened yet"
          description="Incidents raised by OASIS and requests you submit will show up here."
        />
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line">
          {data.map((item) => {
            const Icon = item.kind === 'incident' ? ShieldAlert : PlayCircle;
            return (
              <li key={`${item.kind}-${item.id}`} className="flex items-center gap-3 px-5 py-3.5">
                <span
                  className={
                    item.kind === 'incident'
                      ? 'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-danger-50 text-danger-500'
                      : 'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-500'
                  }
                >
                  <Icon className="h-4 w-4" />
                </span>

                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium text-ink-900">
                    {item.title}
                  </span>
                  <span className="block truncate text-[12px] text-ink-500">
                    {item.resource ?? '—'} · {formatRelativeTime(item.timestamp)}
                  </span>
                </span>

                <Badge tone={STATUS_TONE[item.status] ?? 'neutral'}>{humanize(item.status)}</Badge>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
