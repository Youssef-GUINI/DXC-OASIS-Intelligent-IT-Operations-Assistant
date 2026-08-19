import type { LucideIcon } from 'lucide-react';
import { TrendingDown, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Skeleton } from '@/components/ui/States';

type Trend = { value: number; label: string; goodWhenUp?: boolean };

export function KpiCard({
  label,
  value,
  unit,
  caption,
  icon: Icon,
  trend,
  sparkline,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  unit?: string;
  caption?: string;
  icon: LucideIcon;
  trend?: Trend;
  sparkline?: number[];
  tone?: 'neutral' | 'ok' | 'warn' | 'danger';
}) {
  const iconTone = {
    neutral: 'bg-brand-50 text-brand-500',
    ok: 'bg-ok-50 text-ok-600',
    warn: 'bg-warn-50 text-warn-600',
    danger: 'bg-danger-50 text-danger-600',
  }[tone];

  const trendUp = trend ? trend.value >= 0 : false;
  const trendIsGood = trend ? (trend.goodWhenUp ?? true) === trendUp : true;

  return (
    <article className="card flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-medium text-ink-500">{label}</p>
        <span className={cn('flex h-8 w-8 items-center justify-center rounded-lg', iconTone)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>

      <p className="flex items-baseline gap-1">
        <span className="text-[28px] font-semibold leading-none tracking-tight text-ink-900">
          {value}
        </span>
        {unit && <span className="text-sm font-medium text-ink-500">{unit}</span>}
      </p>

      {sparkline && sparkline.length > 1 && <Sparkline values={sparkline} tone={tone} />}

      <div className="flex items-center gap-2 text-[12px]">
        {trend && (
          <span
            className={cn(
              'inline-flex items-center gap-1 font-medium',
              trendIsGood ? 'text-ok-600' : 'text-warn-600',
            )}
          >
            {trendUp ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            {trendUp ? '+' : ''}
            {trend.value}%
          </span>
        )}
        {caption && <span className="truncate text-ink-500">{caption}</span>}
        {trend && !caption && <span className="text-ink-500">{trend.label}</span>}
      </div>
    </article>
  );
}

function Sparkline({ values, tone }: { values: number[]; tone: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 24 - ((value - min) / span) * 22 - 1;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  const stroke = {
    neutral: 'stroke-brand-400',
    ok: 'stroke-ok-500',
    warn: 'stroke-warn-500',
    danger: 'stroke-danger-500',
  }[tone as 'neutral'];

  return (
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" className="h-6 w-full" aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        className={stroke}
      />
    </svg>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8" />
      </div>
      <Skeleton className="h-7 w-20" />
      <Skeleton className="h-3 w-28" />
    </div>
  );
}
