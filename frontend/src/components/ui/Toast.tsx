import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, XCircle } from 'lucide-react';

type Toast = { id: number; tone: 'success' | 'error'; title: string; detail?: string };
type ToastInput = { tone?: 'success' | 'error'; title: string; detail?: string };

const ToastContext = createContext<{
  notify: (toast: ToastInput) => void;
} | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((toast: ToastInput) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { tone: 'success', ...toast, id }]);
    setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      {createPortal(
        <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-full max-w-sm flex-col gap-2">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className="pointer-events-auto flex items-start gap-3 rounded-card border border-line bg-white p-4 shadow-lift animate-fade-up"
            >
              {toast.tone === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok-500" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger-500" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink-900">{toast.title}</p>
                {toast.detail && <p className="mt-0.5 text-[13px] text-ink-500">{toast.detail}</p>}
              </div>
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used inside ToastProvider');
  return context.notify;
}
