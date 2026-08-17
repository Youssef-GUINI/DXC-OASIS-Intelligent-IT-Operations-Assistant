import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import { formatCapacity } from '@/lib/format';
import type { Backups, Capacity } from '@/lib/types';

const SEGMENTS = [
  { key: 'used', label: 'Used', color: 'bg-brand-500', dot: 'bg-brand-500' },
  { key: 'available', label: 'Available', color: 'bg-brand-100', dot: 'bg-brand-100' },
  { key: 'reserved', label: 'Reserved', color: 'bg-slate-200', dot: 'bg-slate-200' },
] as const;

export function CapacityOverview({ capacity }: { capacity: Capacity }) {
  if (capacity.unavailable) {
    return (
      <Card>
        <CardHeader title="Capacity Overview" />
        <EmptyState
          title="Capacity readings are unavailable"
          description={
            capacity.error ??
            'OASIS could not reach your storage VM. Everything else on this page is still up to date.'
          }
        />
      </Card>
    );
  }

  const sizes = {
    used: capacity.used_gb,
    available: capacity.available_gb,
    reserved: capacity.reserved_gb,
  };
  const total = capacity.total_gb || 1;

  return (
    <Card>
      <CardHeader
        title="Capacity Overview"
        subtitle={`${formatCapacity(capacity.used_gb)} of ${formatCapacity(capacity.total_gb)} in use`}
      />
      <CardBody className="pt-4">
        <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-100">
          {SEGMENTS.map((segment) => {
            const share = (sizes[segment.key] / total) * 100;
            if (share <= 0) return null;
            return (
              <div
                key={segment.key}
                className={segment.color}
                style={{ width: `${share}%` }}
                title={`${segment.label}: ${formatCapacity(sizes[segment.key])}`}
              />
            );
          })}
        </div>

        <dl className="mt-4 grid grid-cols-3 gap-3">
          {SEGMENTS.map((segment) => (
            <div key={segment.key}>
              <dt className="flex items-center gap-1.5 text-[12px] text-ink-500">
                <span className={cn('h-2 w-2 rounded-full', segment.dot)} />
                {segment.label}
              </dt>
              <dd className="mt-1 text-sm font-semibold text-ink-900">
                {formatCapacity(sizes[segment.key])}
              </dd>
            </div>
          ))}
        </dl>

        {capacity.volumes.length > 0 && (
          <ul className="mt-5 space-y-2.5 border-t border-line pt-4">
            {capacity.volumes.slice(0, 4).map((volume) => (
              <li key={volume.volume_id ?? volume.mountpoint} className="flex items-center gap-3">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium text-ink-900">
                    {volume.mountpoint}
                  </span>
                  <span className="block text-[12px] text-ink-500">
                    {formatCapacity(volume.available_gb)} available
                  </span>
                </span>
                <span className="h-1.5 w-20 shrink-0 overflow-hidden rounded-full bg-slate-100">
                  <span
                    className={cn(
                      'block h-full rounded-full',
                      volume.status === 'critical'
                        ? 'bg-danger-500'
                        : volume.status === 'warning'
                          ? 'bg-warn-500'
                          : 'bg-brand-500',
                    )}
                    style={{ width: `${Math.min(volume.percent_used, 100)}%` }}
                  />
                </span>
                <span className="w-9 shrink-0 text-right text-[12px] font-medium text-ink-700">
                  {volume.percent_used}%
                </span>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-4 rounded-lg bg-brand-50 px-3 py-2.5 text-[13px] leading-relaxed text-brand-800">
          {capacity.volumes_near_limit > 0 ? (
            <>
              {capacity.volumes_near_limit} volume
              {capacity.volumes_near_limit > 1 ? 's are' : ' is'} getting close to its capacity limit.{' '}
              <Link to="/storage/requests" className="font-medium underline underline-offset-2">
                Request more capacity
              </Link>
              .
            </>
          ) : (
            <>
              Every volume has room to breathe — the fullest one sits at{' '}
              {Math.max(0, ...capacity.volumes.map((volume) => volume.percent_used))}%.
            </>
          )}
        </p>
      </CardBody>
    </Card>
  );
}

export function BackupHealthCard({ backups }: { backups: Backups }) {
  if (backups.error) {
    return (
      <Card>
        <CardHeader title="Backup Health" />
        <EmptyState title="Backup status is unavailable" description={backups.error} />
      </Card>
    );
  }

  if (!backups.configured) {
    return (
      <Card>
        <CardHeader title="Backup Health" />
        <EmptyState
          icon={<ShieldOff className="h-6 w-6" />}
          title="No backup job is set up yet"
          description="Your volumes have no restore point. Any systemd timer on the VM whose name contains “backup” appears here automatically."
        />
      </Card>
    );
  }

  const tiles = [
    { label: 'Successful', value: backups.successful, tone: 'ok' as const },
    { label: 'Failed', value: backups.failed, tone: 'danger' as const },
    { label: 'Running', value: backups.running, tone: 'brand' as const },
    { label: 'Scheduled', value: backups.scheduled, tone: 'neutral' as const },
  ];

  const surface = {
    ok: 'bg-ok-50 text-ok-600',
    danger: 'bg-danger-50 text-danger-600',
    brand: 'bg-brand-50 text-brand-700',
    neutral: 'bg-slate-50 text-ink-700',
  };

  return (
    <Card>
      <CardHeader
        title="Backup Health"
        subtitle={
          backups.failed > 0
            ? `${backups.failed} job${backups.failed > 1 ? 's need' : ' needs'} your attention`
            : 'Every job completed on its last run'
        }
        action={<Badge tone={backups.failed > 0 ? 'danger' : 'ok'}>{backups.failed > 0 ? 'attention' : 'healthy'}</Badge>}
      />
      <CardBody className="grid grid-cols-2 gap-3 pt-4">
        {tiles.map((tile) => (
          <div key={tile.label} className={cn('rounded-xl px-4 py-3', surface[tile.tone])}>
            <p className="text-[22px] font-semibold leading-none">{tile.value}</p>
            <p className="mt-1.5 text-[12px] font-medium opacity-80">{tile.label}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
