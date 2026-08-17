import { Link } from 'react-router-dom';
import { CheckCircle2, ChevronRight, TriangleAlert, WifiOff } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { Overview } from '@/lib/types';

type AttentionItem = { label: string; to: string };

/** Niveau 1 de la hiérarchie : ce qui réclame l'attention, tout de suite. */
export function AttentionBanner({ overview }: { overview: Overview }) {
  const items: AttentionItem[] = [];

  if (overview.incidents.needs_attention > 0) {
    const count = overview.incidents.needs_attention;
    items.push({
      label: `${count} incident${count > 1 ? 's' : ''} waiting on you`,
      to: '/storage/incidents',
    });
  }
  if (overview.backups.failed > 0) {
    const count = overview.backups.failed;
    items.push({
      label: `${count} backup job${count > 1 ? 's' : ''} failed`,
      to: '/storage/chat',
    });
  }
  if (overview.capacity.volumes_near_limit > 0) {
    const count = overview.capacity.volumes_near_limit;
    items.push({
      label: `${count} volume${count > 1 ? 's' : ''} near capacity`,
      to: '/storage/requests',
    });
  }
  if (!overview.backups.configured && !overview.backups.error) {
    items.push({ label: 'No backup job is set up yet', to: '/storage/chat' });
  }

  const unreachable = overview.capacity.unavailable;
  const healthy = !unreachable && items.length === 0;

  const Icon = unreachable ? WifiOff : healthy ? CheckCircle2 : TriangleAlert;

  return (
    <div
      className={cn(
        'card flex flex-wrap items-center gap-x-5 gap-y-3 p-5',
        healthy && 'border-ok-200 bg-ok-50',
        !healthy && !unreachable && 'border-warn-200 bg-warn-50',
        unreachable && 'border-line bg-white',
      )}
    >
      <Icon
        className={cn(
          'h-5 w-5 shrink-0',
          healthy && 'text-ok-600',
          !healthy && !unreachable && 'text-warn-600',
          unreachable && 'text-ink-400',
        )}
      />

      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-semibold text-ink-900">{overview.headline}</p>
        {unreachable ? (
          <p className="mt-0.5 text-[13px] text-ink-500">
            Capacity, backups and performance stay unknown until the VM answers again. Incidents and
            requests below come from OASIS itself and are still accurate.
          </p>
        ) : items.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
            {items.map((item) => (
              <Link
                key={item.to + item.label}
                to={item.to}
                className="inline-flex items-center gap-0.5 text-[13px] font-medium text-ink-700 underline-offset-4 hover:text-brand-700 hover:underline"
              >
                {item.label}
                <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-0.5 text-[13px] text-ink-500">
            Capacity, backups and replication are all within their thresholds.
          </p>
        )}
      </div>
    </div>
  );
}
