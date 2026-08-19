import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

function FieldShell({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-ink-700">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-[12px] text-ink-400">{hint}</span>}
    </label>
  );
}

const fieldClass =
  'w-full rounded-lg border border-line bg-canvas px-3 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100';

export function TextField({ label, hint, className, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <FieldShell label={label} hint={hint}>
      <input {...props} className={cn('h-10', fieldClass, className)} />
    </FieldShell>
  );
}

export function TextAreaField({ label, hint, className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string }) {
  return (
    <FieldShell label={label} hint={hint}>
      <textarea {...props} className={cn('min-h-24 resize-y py-2.5', fieldClass, className)} />
    </FieldShell>
  );
}

export function SelectField({ label, hint, className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: string }) {
  return (
    <FieldShell label={label} hint={hint}>
      <select {...props} className={cn('h-10', fieldClass, className)}>
        {children}
      </select>
    </FieldShell>
  );
}
