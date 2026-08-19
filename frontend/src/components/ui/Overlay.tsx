import type { ReactNode } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/cn';

function OverlayBackdrop({ onClose }: { onClose: () => void }) {
  return <button aria-label="Close overlay" onClick={onClose} className="fixed inset-0 bg-ink-900/25 backdrop-blur-[2px]" />;
}

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <OverlayBackdrop onClose={onClose} />
      <section className={cn('relative max-h-[88vh] w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-white shadow-lift', className)}>
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-[16px] font-semibold text-ink-900">{title}</h2>
            {subtitle && <p className="mt-1 text-[13px] text-ink-500">{subtitle}</p>}
          </div>
          <button onClick={onClose} aria-label="Close" className="focus-ring rounded-lg p-2 text-ink-400 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </header>
        {children}
      </section>
    </div>,
    document.body,
  );
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  footer,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}) {
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50">
      <OverlayBackdrop onClose={onClose} />
      <aside className="fixed inset-y-0 right-0 flex w-full max-w-xl flex-col border-l border-line bg-canvas shadow-lift">
        <header className="flex items-start justify-between gap-4 border-b border-line bg-white px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-[17px] font-semibold text-ink-900">{title}</h2>
            {subtitle && <div className="mt-2">{subtitle}</div>}
          </div>
          <button onClick={onClose} aria-label="Close" className="focus-ring rounded-lg p-2 text-ink-400 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
        {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-line bg-white px-5 py-4">{footer}</footer>}
      </aside>
    </div>,
    document.body,
  );
}
