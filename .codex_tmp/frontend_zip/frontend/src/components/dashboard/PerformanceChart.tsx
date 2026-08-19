import { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatNumber } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Performance, PerformanceRange } from '@/lib/types';

const RANGES: { key: PerformanceRange; label: string }[] = [
  { key: '24h', label: '24h' },
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
];

const METRICS = {
  iops: { key: 'iops', label: 'IOPS', color: '#3b66ef', unit: '' },
  throughput: { key: 'throughput_mbps', label: 'Throughput', color: '#ef7c33', unit: ' MB/s' },
  latency: { key: 'latency_ms', label: 'Latency', color: '#10b981', unit: ' ms' },
} as const;

type MetricKey = keyof typeof METRICS;

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { key: T; label: string }[];
  value: T;
  onChange: (key: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-line bg-canvas p-0.5">
      {options.map((option) => (
        <button
          key={option.key}
          onClick={() => onChange(option.key)}
          className={cn(
            'focus-ring rounded-[6px] px-2.5 py-1 text-[12px] font-medium transition-colors',
            value === option.key
              ? 'bg-white text-ink-900 shadow-sm'
              : 'text-ink-500 hover:text-ink-900',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function formatTick(iso: string, range: PerformanceRange): string {
  const date = new Date(iso);
  if (range === '30d') return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  if (range === '7d')
    return date.toLocaleDateString('en-GB', { weekday: 'short', hour: '2-digit', hour12: false });
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function PerformanceChart() {
  const [range, setRange] = useState<PerformanceRange>('24h');
  const [metric, setMetric] = useState<MetricKey>('iops');

  const { data, error, loading, reload } = useResource<Performance>(
    () => api.get<Performance>(`/storage/dashboard/performance?range=${range}`),
    [range],
  );

  const active = METRICS[metric];
  const average =
    data &&
    ({ iops: data.iops_avg, throughput: data.throughput_avg_mbps, latency: data.latency_avg_ms }[
      metric
    ] as number);

  return (
    <Card>
      <CardHeader
        title="Storage Performance"
        subtitle={
          data
            ? `Averaging ${formatNumber(average ?? 0)}${active.unit || ' IOPS'} over the last ${
                RANGES.find((option) => option.key === range)?.label
              }`
            : 'Reading performance counters…'
        }
        action={<Segmented options={RANGES} value={range} onChange={setRange} />}
      />

      <div className="flex flex-wrap items-center gap-1 px-5 pt-4">
        <Segmented
          options={(Object.keys(METRICS) as MetricKey[]).map((key) => ({
            key,
            label: METRICS[key].label,
          }))}
          value={metric}
          onChange={setMetric}
        />
      </div>

      <div className="px-2 pb-4 pt-4">
        {loading && <Skeleton className="mx-3 h-[260px]" />}
        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data?.collecting && !loading && (
          <EmptyState
            icon={<Activity className="h-6 w-6" />}
            title="No measurements for this period yet"
            description="OASIS samples the disk counters on your VM every few minutes. The chart fills in as readings accumulate — make sure the VM is reachable."
          />
        )}

        {data && !data.collecting && !loading && (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data.points} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`fill-${metric}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={active.color} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={active.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f8" vertical={false} />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value: string) => formatTick(value, range)}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                axisLine={false}
                tickLine={false}
                minTickGap={28}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                axisLine={false}
                tickLine={false}
                width={48}
                tickFormatter={(value: number) => formatNumber(value)}
              />
              <Tooltip
                cursor={{ stroke: '#cbd5e1', strokeDasharray: '3 3' }}
                contentStyle={{
                  borderRadius: 12,
                  border: '1px solid #e6ebf4',
                  boxShadow: '0 12px 32px rgba(15,23,42,0.08)',
                  fontSize: 12,
                }}
                labelFormatter={(value: string) =>
                  new Date(value).toLocaleString('en-GB', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                }
                formatter={(value: number) => [`${formatNumber(value)}${active.unit}`, active.label]}
              />
              <Area
                type="monotone"
                dataKey={active.key}
                stroke={active.color}
                strokeWidth={2}
                fill={`url(#fill-${metric})`}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

    </Card>
  );
}
