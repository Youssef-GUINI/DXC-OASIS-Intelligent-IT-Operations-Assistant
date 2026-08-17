import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type Tone = 'neutral' | 'brand' | 'ok' | 'warn' | 'danger';

const TONES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-ink-700 ring-slate-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  ok: 'bg-ok-50 text-ok-600 ring-ok-200',
  warn: 'bg-warn-50 text-warn-600 ring-warn-200',
  danger: 'bg-danger-50 text-danger-600 ring-danger-200',
};

/** Correspondances partagées par les incidents, backups et demandes. */
export const SEVERITY_TONE: Record<string, Tone> = {
  critical: 'danger',
  high: 'warn',
  medium: 'brand',
  low: 'neutral',
  info: 'brand',
};

export const STATUS_TONE: Record<string, Tone> = {
  open: 'danger',
  in_progress: 'warn',
  resolved: 'ok',
  closed: 'neutral',
  pending: 'warn',
  confirmed: 'brand',
  completed: 'ok',
  failed: 'danger',
  rejected: 'neutral',
  success: 'ok',
  successful: 'ok',
  running: 'brand',
  scheduled: 'neutral',
  indexed: 'ok',
  healthy: 'ok',
  warning: 'warn',
};

export function Badge({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1 ring-inset',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusDot({ tone = 'neutral', className }: { tone?: Tone; className?: string }) {
  const colors: Record<Tone, string> = {
    neutral: 'bg-ink-400',
    brand: 'bg-brand-500',
    ok: 'bg-ok-500',
    warn: 'bg-warn-500',
    danger: 'bg-danger-500',
  };
  return <span className={cn('inline-block h-2 w-2 shrink-0 rounded-full', colors[tone], className)} />;
}
