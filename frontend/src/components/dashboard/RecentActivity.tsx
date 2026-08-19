import type { LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';

export function RecentActivity({
  items,
}: {
  items: { title: string; detail: string; status: string; time: string; icon: LucideIcon; tone: 'brand' | 'ok' | 'warn' }[];
}) {
  return (
    <ul className="divide-y divide-line">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <li key={`${item.title}-${item.time}`} className="flex items-center gap-4 py-3">
            <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', item.tone === 'ok' && 'bg-ok-50 text-ok-600', item.tone === 'warn' && 'bg-warn-50 text-warn-600', item.tone === 'brand' && 'bg-brand-50 text-brand-600')}>
              <Icon className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-semibold text-ink-900">{item.title}</span>
              <span className="block truncate text-[12px] text-ink-500">{item.detail}</span>
            </span>
            <Badge tone={item.status === 'Completed' ? 'ok' : 'brand'}>{item.status}</Badge>
            <span className="hidden w-20 text-right text-[12px] text-ink-400 sm:block">{item.time}</span>
          </li>
        );
      })}
    </ul>
  );
}
