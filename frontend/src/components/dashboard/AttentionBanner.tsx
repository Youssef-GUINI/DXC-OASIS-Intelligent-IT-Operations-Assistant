import { AlertTriangle } from 'lucide-react';

export function AttentionBanner({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-warn-200 bg-warn-50 px-4 py-3">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warn-600" />
      <div>
        <p className="text-[13px] font-semibold text-ink-900">{title}</p>
        <p className="mt-0.5 text-[12px] text-ink-600">{detail}</p>
      </div>
    </div>
  );
}
