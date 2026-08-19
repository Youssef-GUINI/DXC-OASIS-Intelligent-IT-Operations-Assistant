import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';

export function KpiCard({
  label,
  value,
  caption,
  icon: Icon,
  tone = 'brand',
}: {
  label: string;
  value: string | number;
  caption?: string;
  icon: LucideIcon;
  tone?: 'brand' | 'ok' | 'warn';
}) {
  const toneClass = {
    brand: 'bg-brand-50 text-brand-500',
    ok: 'bg-ok-50 text-ok-600',
    warn: 'bg-warn-50 text-warn-600',
  }[tone];

  return (
    <article className="rounded-xl border border-line bg-white p-5 shadow-card">
      <span className={cn('inline-flex h-8 w-8 items-center justify-center rounded-lg', toneClass)}>
        <Icon className="h-4 w-4" />
      </span>
      <p className="mt-3 text-[13px] font-medium text-ink-500">{label}</p>
      <p className="mt-2 text-[28px] font-semibold leading-none text-ink-900">{value}</p>
      {caption && <p className="mt-3 text-[12px] text-ink-500">{caption}</p>}
    </article>
  );
}
