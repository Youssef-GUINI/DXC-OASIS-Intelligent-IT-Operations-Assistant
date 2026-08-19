import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn('card overflow-hidden', className)}>{children}</section>;
}

export function CardHeader({
  children,
  className,
  title,
  subtitle,
}: {
  children?: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
}) {
  return (
    <div className={cn('border-b border-line px-5 py-4', className)}>
      {title && <h2 className="card-title">{title}</h2>}
      {subtitle && <p className="card-sub mt-1">{subtitle}</p>}
      {children}
    </div>
  );
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('p-5', className)}>{children}</div>;
}
