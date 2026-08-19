import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';

function useEscapeToClose(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);
}

function Backdrop({ onClose }: { onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-40 bg-ink-900/25 backdrop-blur-[2px]"
      aria-hidden="true"
    />
  );
}

function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      onClick={onClose}
      aria-label="Close"
      className="focus-ring rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-slate-100 hover:text-ink-700"
    >
      <X className="h-4 w-4" />
    </button>
  );
}

/** Panneau latéral — utilisé pour le détail d'un incident. */
export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEscapeToClose(open, onClose);
  if (!open) return null;

  return createPortal(
    <>
      <Backdrop onClose={onClose} />
      <aside
        role="dialog"
        aria-modal="true"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-canvas shadow-lift animate-fade-up"
      >
        <header className="flex items-start justify-between gap-4 border-b border-line bg-white px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-ink-900">{title}</h2>
            {subtitle && <div className="mt-1 text-[13px] text-ink-500">{subtitle}</div>}
          </div>
          <CloseButton onClose={onClose} />
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <footer className="flex flex-wrap gap-2 border-t border-line bg-white px-6 py-4">{footer}</footer>
        )}
      </aside>
    </>,
    document.body,
  );
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
  useEscapeToClose(open, onClose);
  if (!open) return null;

  return createPortal(
    <>
      <Backdrop onClose={onClose} />
      <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
        <div
          role="dialog"
          aria-modal="true"
          className={cn(
            'w-full max-w-lg rounded-card bg-white shadow-lift animate-fade-up',
            className,
          )}
        >
          <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-ink-900">{title}</h2>
              {subtitle && <p className="mt-1 text-[13px] text-ink-500">{subtitle}</p>}
            </div>
            <CloseButton onClose={onClose} />
          </header>
          {children}
        </div>
      </div>
    </>,
    document.body,
  );
}
