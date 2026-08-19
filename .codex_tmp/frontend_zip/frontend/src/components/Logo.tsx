import { useState } from 'react';
import { cn } from '@/lib/cn';

/**
 * Affiche le logo fourni (public/dxc-logo.png). Tant que le fichier n'a pas
 * été déposé, on retombe sur une marque abstraite neutre plutôt que de
 * casser la mise en page ou d'afficher une image brisée.
 */
function FallbackMark({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} className="shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id="oasis-mark" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#5f8bfa" />
          <stop offset="0.5" stopColor="#ef7c33" />
          <stop offset="1" stopColor="#5f8bfa" />
        </linearGradient>
      </defs>
      <g fill="none" stroke="url(#oasis-mark)" strokeWidth="2.4" strokeLinecap="round">
        <path d="M9 8h3.5a8 8 0 0 1 0 16H9" />
        <path d="M23 8h-3.5a8 8 0 0 0 0 16H23" />
        <path d="m13.5 12.5 5 7M18.5 12.5l-5 7" />
      </g>
    </svg>
  );
}

type LogoProps = {
  /** Taille du symbole en pixels. */
  size?: number;
  /** Affiche « DXC OASIS » et un sous-titre à côté du symbole. */
  withWordmark?: boolean;
  subtitle?: string;
  className?: string;
};

export function Logo({ size = 32, withWordmark = false, subtitle, className }: LogoProps) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      {imageFailed ? (
        <FallbackMark size={size} />
      ) : (
        <img
          src="/dxc-logo.png"
          alt=""
          onError={() => setImageFailed(true)}
          className="shrink-0 object-contain"
          style={{ width: size, height: size }}
        />
      )}

      {withWordmark && (
        <span className="min-w-0 leading-tight">
          <span className="block text-[15px] font-bold tracking-tight text-ink-900">DXC OASIS</span>
          {subtitle && <span className="block truncate text-[11px] text-ink-500">{subtitle}</span>}
        </span>
      )}
    </span>
  );
}
