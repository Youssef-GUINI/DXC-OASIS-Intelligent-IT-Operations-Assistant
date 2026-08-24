import { useState } from 'react';
import { CheckCircle2, ShieldAlert, XCircle } from 'lucide-react';
import { Badge, STATUS_TONE } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { formatDateTime, humanize } from '@/lib/format';
import type { ActionRequest } from '@/lib/types';

/**
 * Une remédiation proposée par OASIS, avec les deux seuls boutons qui
 * l'exécutent ou l'écartent.
 *
 * L'agent n'exécute jamais lui-même un outil qui modifie la VM : relancer une
 * sauvegarde, prendre un snapshot ou restaurer passent tous par une
 * proposition, et par ce clic. Le composant est partagé entre le chat
 * d'investigation et le panneau d'incident pour que la décision se prenne au
 * même endroit que la lecture, quel que soit l'écran.
 */

/** Ce que l'action fera, en une phrase, avant de la confirmer. */
const ACTION_LABELS: Record<string, (target: string) => string> = {
  run_backup: (target) => `Re-run backup job ${target} now`,
  create_snapshot: (target) => `Take a snapshot of volume ${target}`,
  restore_from_backup: (target) => `Restore ${target} from a backup`,
  repair_backup_repository: (target) =>
    `Repair the backup repository configured for ${target}`,
};

/** Les actions qui écrasent des données méritent un avertissement explicite. */
const DESTRUCTIVE_ACTIONS = new Set(['restore_from_backup']);

function describe(action: ActionRequest): string {
  const label = ACTION_LABELS[action.action_type];
  return label ? label(action.target) : `${humanize(action.action_type)} — ${action.target}`;
}

function resultText(action: ActionRequest): string | null {
  if (!action.result) return null;
  const { error, status, action: outcome } = action.result as Record<string, unknown>;
  if (typeof error === 'string') return error;
  if (typeof outcome === 'string') return humanize(outcome);
  if (typeof status === 'string') return humanize(status);
  return null;
}

export function ActionProposal({
  action,
  onSettled,
}: {
  action: ActionRequest;
  /** Rejoué après confirmation ou rejet : l'appelant recharge ce qu'il affiche. */
  onSettled?: (updated: ActionRequest) => void;
}) {
  const [busy, setBusy] = useState<'confirm' | 'reject' | null>(null);
  const notify = useToast();

  const pending = action.status === 'pending';
  const destructive = DESTRUCTIVE_ACTIONS.has(action.action_type);

  async function settle(decision: 'confirm' | 'reject') {
    setBusy(decision);
    try {
      const updated = await api.post<ActionRequest>(
        `/storage/actions/${action.id}/${decision}`,
        decision === 'reject' ? { reason: null } : undefined,
      );
      notify(
        decision === 'confirm'
          ? updated.status === 'failed'
            ? {
                tone: 'error',
                title: 'The action ran but failed',
                detail: resultText(updated) ?? undefined,
              }
            : { title: 'Action executed', detail: describe(updated) }
          : { title: 'Action rejected', detail: 'Nothing was run on the VM.' },
      );
      onSettled?.(updated);
    } catch (caught) {
      notify({
        tone: 'error',
        title: decision === 'confirm' ? "Couldn't run this action" : "Couldn't reject this action",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      className={`rounded-xl border p-4 ${
        pending ? 'border-accent-200 bg-accent-50' : 'border-line bg-canvas'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <ShieldAlert
          className={`h-4 w-4 shrink-0 ${pending ? 'text-accent-500' : 'text-ink-400'}`}
        />
        <span className="text-[12px] font-medium uppercase tracking-wide text-ink-500">
          {pending ? 'Proposed action' : 'Action'}
        </span>
        <Badge tone={STATUS_TONE[action.status] ?? 'neutral'}>{humanize(action.status)}</Badge>
      </div>

      <p className="mt-2 text-[13px] leading-relaxed text-ink-900">{describe(action)}</p>
      <p className="mt-0.5 font-mono text-[11px] text-ink-400">
        {action.action_type}({action.target})
      </p>

      {pending && destructive && (
        <p className="mt-2 text-[12px] leading-relaxed text-danger-600">
          This action overwrites existing data. Check the target before confirming.
        </p>
      )}

      {!pending && (
        <p className="mt-2 text-[12px] text-ink-500">
          {resultText(action) ?? 'No result recorded.'}
          {action.completed_at ? ` · ${formatDateTime(action.completed_at)}` : ''}
        </p>
      )}

      {pending && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="primary"
            loading={busy === 'confirm'}
            disabled={busy !== null}
            icon={<CheckCircle2 className="h-3.5 w-3.5" />}
            onClick={() => void settle('confirm')}
          >
            Confirm
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={busy === 'reject'}
            disabled={busy !== null}
            icon={<XCircle className="h-3.5 w-3.5" />}
            onClick={() => void settle('reject')}
          >
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}
