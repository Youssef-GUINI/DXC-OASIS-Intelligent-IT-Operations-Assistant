import { Sparkles } from 'lucide-react';

export function OasisInsights({ children }: { children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-white p-5 shadow-card">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold text-ink-900">
        <Sparkles className="h-4 w-4 text-brand-500" />
        OASIS Insights
      </h2>
      <div className="mt-4 text-[13px] leading-relaxed text-ink-600">{children}</div>
    </section>
  );
}
