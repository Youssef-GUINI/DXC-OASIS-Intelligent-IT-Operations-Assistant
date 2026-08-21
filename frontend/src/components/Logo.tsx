import { useState } from 'react';
import { cn } from '@/lib/cn';

/**
 * Marque carrée, dessinée aux mêmes lettres que le logo.
 *
 * Elle sert de repli si public/dxc-logo.png manque, et de variante assumée
 * partout où la largeur est comptée : le logo est un logotype de rapport 6:1,
 * illisible dans une pastille d'avatar ou dans un rail replié de 72 px.
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
  /**
   * Hauteur du symbole en pixels ; la largeur suit ses proportions.
   *
   * Le fichier est recadré sur la marque elle-même (478 × 80, soit un rapport
   * de 6:1) : la hauteur demandée est donc celle du logo visible, sans marge
   * morte autour.
   */
  size?: number;
  /** Affiche « DXC OASIS » et un sous-titre à côté du symbole. */
  withWordmark?: boolean;
  subtitle?: string;
  /**
   * `wordmark` (défaut) affiche le logo DXC, large ; `mark` la version carrée,
   * pour les emplacements étroits où le logotype ne tiendrait pas.
   */
  variant?: 'wordmark' | 'mark';
  className?: string;
};

export function Logo({
  size = 32,
  withWordmark = false,
  subtitle,
  variant = 'wordmark',
  className,
}: LogoProps) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      {variant === 'mark' || imageFailed ? (
        <FallbackMark size={size} />
      ) : (
        <img
          src="/dxc-logo.png"
          alt=""
          onError={() => setImageFailed(true)}
          // Le fichier est détouré : pas de cadre blanc à masquer, la marque
          // se pose telle quelle sur le fond de la page.
          //
          // `min-w-0 max-w-full` plutôt que `shrink-0` : un logotype de 6:1
          // devient vite plus large que son emplacement, mieux vaut qu'il se
          // réduise (object-contain conserve les proportions) que de pousser
          // le texte hors du cadre.
          className="min-w-0 max-w-full object-contain"
          style={{ height: size, width: 'auto' }}
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
