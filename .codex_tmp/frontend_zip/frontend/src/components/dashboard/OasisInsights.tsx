import { Link } from 'react-router-dom';
import { ChevronRight, Sparkles } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE } from '@/components/ui/Badge';
import { ErrorState, Skeleton } from '@/components/ui/States';
import { api } from '@/lib/api';
import { useResource } from '@/lib/useResource';
import type { Insight } from '@/lib/types';

export function OasisInsights() {
  const { data, error, loading, reload } = useResource<Insight[]>(
    () => api.get<Insight[]>('/storage/dashboard/insights'),
    [],
  );

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent-500" />
            OASIS Insights
          </span>
        }
        subtitle="What OASIS noticed while watching your environment"
      />

      {loading && (
        <div className="space-y-4 p-5">
          {[0, 1].map((row) => (
            <div key={row} className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
      )}

      {error && !loading && <ErrorState message={error} onRetry={reload} />}

      {data && !loading && (
        <ul className="divide-y divide-line">
          {data.map((insight) => (
            <li key={insight.id} className="px-5 py-4">
              <div className="flex items-start gap-3">
                <Badge tone={SEVERITY_TONE[insight.priority] ?? 'neutral'} className="mt-0.5">
                  {insight.priority}
                </Badge>
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug text-ink-900">
                    {insight.title}
                  </p>
                  <p className="mt-1 text-[13px] leading-relaxed text-ink-500">{insight.detail}</p>
                  {insight.action_label && insight.action_target && (
                    <Link
                      to={insight.action_target}
                      className="mt-2 inline-flex items-center gap-0.5 text-[13px] font-medium text-brand-600 hover:text-brand-700"
                    >
                      {insight.action_label}
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
