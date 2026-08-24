import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { ActionProposal } from '@/components/ActionProposal';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE, StatusDot } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatDateTime, formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { Incident, IncidentDetail, Investigation } from '@/lib/types';

type Filter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'resolved';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'critical', label: 'Critical' },
  { key: 'high', label: 'High' },
  { key: 'medium', label: 'Medium' },
  { key: 'low', label: 'Low' },
  { key: 'resolved', label: 'Resolved' },
];

/** Le backend filtre soit par sévérité soit par statut — jamais les deux. */
function queryFor(filter: Filter): string {
  if (filter === 'all') return '';
  if (filter === 'resolved') return '?status=resolved';
  return `?severity=${filter}`;
}

/**
 * Les cinq temps par lesquels passe tout incident.
 *
 * L'ordre n'est pas décoratif : c'est le contrat de l'application. Rien ne
 * s'exécute sur la VM sans être passé par « Action proposée » puis par le clic
 * humain de « Confirmation », et un ticket ne se referme qu'une fois l'effet
 * vérifié. L'afficher permet de voir, sur n'importe quel ticket, où il en est.
 */
const LIFECYCLE = [
  { key: 'detected', label: 'Detected' },
  { key: 'diagnosed', label: 'Diagnosed' },
  { key: 'proposed', label: 'Action proposed' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'resolved', label: 'Resolved' },
] as const;

function reachedStage(incident: IncidentDetail): number {
  if (incident.status === 'resolved' || incident.status === 'closed') return 4;
  if (incident.actions.some((action) => action.status === 'completed')) return 3;
  if (incident.actions.length > 0) return 2;
  if (incident.root_cause) return 1;
  return 0;
}

export default function IncidentsPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<Incident | null>(null);
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const navigate = useNavigate();
  const notify = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const { data, error, loading, reload } = useResource<Incident[]>(
    () => api.get<Incident[]>(`/incidents${queryFor(filter)}`),
    [filter],
  );

  /**
   * Charge le cycle de vie complet du ticket ouvert.
   *
   * La liste ne transporte ni les actions ni les notes : les joindre à chaque
   * ligne coûterait autant de requêtes que d'incidents affichés, pour des
   * données que la liste ne montre pas. Le panneau, lui, en a besoin.
   */
  const loadDetail = useCallback(
    async (incidentId: string) => {
      setDetailError(null);
      try {
        setDetail(await api.get<IncidentDetail>(`/incidents/${incidentId}`));
      } catch (caught) {
        setDetail(null);
        setDetailError(caught instanceof Error ? caught.message : "Couldn't load this incident");
      }
    },
    [],
  );

  useEffect(() => {
    if (selected === null) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    void loadDetail(selected.id);
  }, [selected, loadDetail]);

  // Arrivée depuis la recherche globale : le ticket est rechargé par son id
  // plutôt que cherché dans la liste, qui peut être filtrée ou tronquée.
  const requestedIncident = searchParams.get('incident');
  useEffect(() => {
    if (!requestedIncident) return;
    let cancelled = false;

    void api
      .get<Incident>(`/incidents/${requestedIncident}`)
      .then((incident) => {
        if (!cancelled) setSelected(incident);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        notify({
          tone: 'error',
          title: "Couldn't open this incident",
          detail: caught instanceof Error ? caught.message : undefined,
        });
      });

    // Le paramètre a joué son rôle : le garder rouvrirait le panneau à chaque
    // rendu, et le lien resterait dans l'historique du navigateur.
    setSearchParams({}, { replace: true });
    return () => {
      cancelled = true;
    };
  }, [requestedIncident, setSearchParams, notify]);

  /**
   * Ouvre le fil d'investigation du ticket et y bascule.
   *
   * L'appel est long — l'agent lit la VM en SSH puis interroge le modèle —
   * d'où le bouton en attente plutôt qu'une navigation immédiate vers un fil
   * vide : l'ingénieur arrive sur un diagnostic déjà écrit.
   */
  async function investigate(incident: Incident) {
    setInvestigating(true);
    try {
      const investigation = await api.post<Investigation>(`/incidents/${incident.id}/investigate`);
      navigate(`/storage/chat?conversation=${investigation.conversation_id}`);
    } catch (caught) {
      notify({
        tone: 'error',
        title: "OASIS couldn't investigate this incident",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setInvestigating(false);
    }
  }

  async function markResolved(incident: Incident) {
    setResolving(true);
    try {
      await api.patch<IncidentDetail>(`/incidents/${incident.id}`, { status: 'resolved' });
      notify({ title: 'Incident resolved', detail: `${incident.ticket_number} is now closed out.` });
      setSelected(null);
      reload();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't resolve this incident",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setResolving(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="Storage Incidents"
        subtitle="Monitor and investigate storage-related issues."
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {FILTERS.map((option) => (
          <button
            key={option.key}
            onClick={() => setFilter(option.key)}
            className={cn(
              'focus-ring rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors',
              filter === option.key
                ? 'bg-brand-500 text-white'
                : 'border border-line bg-white text-ink-700 hover:bg-slate-50',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      <Card>
        {loading && (
          <div className="space-y-3 p-5">
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} className="h-14" />
            ))}
          </div>
        )}

        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data && !loading && data.length === 0 && (
          <EmptyState
            icon={<ShieldCheck className="h-7 w-7" />}
            title={filter === 'all' ? 'No incidents right now' : `No ${filter} incidents`}
            description="OASIS raises a ticket automatically when it detects something serious. Quiet here is good news."
          />
        )}

        {data && data.length > 0 && (
          <ul className="divide-y divide-line">
            {data.map((incident) => (
              <li key={incident.id}>
                <button
                  onClick={() => setSelected(incident)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50"
                >
                  <StatusDot
                    tone={SEVERITY_TONE[incident.severity] ?? 'neutral'}
                    className="shrink-0"
                  />

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-[14px] font-medium text-ink-900">
                        {incident.title}
                      </span>
                      <span className="font-mono text-[11px] text-ink-400">
                        {incident.ticket_number}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-ink-500">
                      {incident.affected_system} · raised {formatRelativeTime(incident.created_at)}
                    </span>
                  </span>

                  <span className="hidden shrink-0 items-center gap-2 sm:flex">
                    <Badge tone={SEVERITY_TONE[incident.severity] ?? 'neutral'}>
                      {incident.severity}
                    </Badge>
                    <Badge tone={STATUS_TONE[incident.status] ?? 'neutral'}>
                      {humanize(incident.status)}
                    </Badge>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Drawer
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected?.title ?? ''}
        subtitle={
          selected && (
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[12px]">{selected.ticket_number}</span>
              <Badge tone={SEVERITY_TONE[selected.severity] ?? 'neutral'}>{selected.severity}</Badge>
              <Badge tone={STATUS_TONE[(detail ?? selected).status] ?? 'neutral'}>
                {humanize((detail ?? selected).status)}
              </Badge>
            </span>
          )
        }
        footer={
          selected && (
            <>
              <Button
                variant="primary"
                loading={investigating}
                icon={<Sparkles className="h-4 w-4" />}
                onClick={() => void investigate(selected)}
              >
                {detail?.investigation_conversation_id
                  ? 'Reopen investigation'
                  : 'Investigate with OASIS'}
              </Button>
              <Button onClick={() => navigate('/storage/requests')}>Create Request</Button>
              {selected.status !== 'resolved' && selected.status !== 'closed' && (
                <Button
                  variant="secondary"
                  loading={resolving}
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  onClick={() => void markResolved(selected)}
                >
                  Mark as Resolved
                </Button>
              )}
            </>
          )
        }
      >
        {selected && (
          <IncidentBody
            incident={selected}
            detail={detail}
            detailError={detailError}
            onRetry={() => void loadDetail(selected.id)}
            onActionSettled={() => {
              void loadDetail(selected.id);
              reload();
            }}
          />
        )}
      </Drawer>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[12px] text-ink-500">{label}</dt>
      <dd className="mt-0.5 text-[13px] font-medium text-ink-900">{value}</dd>
    </div>
  );
}

/** Où en est le ticket dans les cinq temps du cycle. */
function Lifecycle({ incident }: { incident: IncidentDetail }) {
  const reached = reachedStage(incident);

  return (
    <Card>
      <div className="p-5">
        <h3 className="card-title">Lifecycle</h3>
        <ol className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2">
          {LIFECYCLE.map((stage, index) => {
            const done = index <= reached;
            return (
              <li key={stage.key} className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                    done ? 'bg-brand-500 text-white' : 'bg-slate-100 text-ink-400',
                  )}
                >
                  {index + 1}
                </span>
                <span
                  className={cn(
                    'text-[12px]',
                    done ? 'font-medium text-ink-900' : 'text-ink-400',
                  )}
                >
                  {stage.label}
                </span>
                {index < LIFECYCLE.length - 1 && (
                  <span className="hidden h-px w-4 bg-line sm:block" aria-hidden />
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </Card>
  );
}

function IncidentBody({
  incident,
  detail,
  detailError,
  onRetry,
  onActionSettled,
}: {
  incident: Incident;
  detail: IncidentDetail | null;
  detailError: string | null;
  onRetry: () => void;
  onActionSettled: () => void;
}) {
  // Le ticket de la liste s'affiche immédiatement ; le cycle de vie complet
  // arrive une requête plus tard. Rien ne clignote entre-temps.
  const current = detail ?? incident;
  const pendingActions = detail?.actions.filter((action) => action.status === 'pending') ?? [];
  const settledActions = detail?.actions.filter((action) => action.status !== 'pending') ?? [];

  return (
    <div className="space-y-4">
      {detail && <Lifecycle incident={detail} />}

      <Card>
        <dl className="grid grid-cols-2 gap-4 p-5">
          <DetailRow label="Affected resource" value={current.affected_system} />
          <DetailRow label="Raised" value={formatDateTime(current.created_at)} />
          <DetailRow label="Status" value={humanize(current.status)} />
          <DetailRow
            label="Resolved"
            value={current.resolved_at ? formatDateTime(current.resolved_at) : 'Not yet'}
          />
        </dl>
      </Card>

      <Card>
        <div className="p-5">
          <h3 className="card-title">What happened</h3>
          <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-ink-700">
            {current.description}
          </p>
        </div>
      </Card>

      {detailError && (
        <ErrorState message={detailError} onRetry={onRetry} />
      )}

      {(current.root_cause || current.impact_summary) && (
        <Card className="border-accent-200 bg-accent-50">
          <div className="p-5">
            <h3 className="flex items-center gap-2 card-title">
              <Sparkles className="h-4 w-4 text-accent-500" />
              OASIS Analysis
            </h3>
            {current.root_cause && (
              <div className="mt-3">
                <p className="text-[12px] font-medium uppercase tracking-wide text-accent-600">
                  Likely root cause
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">
                  {current.root_cause}
                </p>
              </div>
            )}
            {current.impact_summary && (
              <div className="mt-3">
                <p className="text-[12px] font-medium uppercase tracking-wide text-accent-600">
                  Impact
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">
                  {current.impact_summary}
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {!current.root_cause && (
        <Card>
          <div className="p-5">
            <p className="text-[13px] leading-relaxed text-ink-500">
              No diagnosis yet. "Investigate with OASIS" opens a thread where the agent reads the
              VM journals, states the root cause and proposes a remediation for you to confirm.
            </p>
          </div>
        </Card>
      )}

      {pendingActions.length > 0 && (
        <Card>
          <div className="space-y-3 p-5">
            <h3 className="card-title">Waiting on your decision</h3>
            {pendingActions.map((action) => (
              <ActionProposal key={action.id} action={action} onSettled={onActionSettled} />
            ))}
          </div>
        </Card>
      )}

      {current.recommendations.length > 0 && (
        <Card>
          <div className="p-5">
            <h3 className="card-title">Recommended next steps</h3>
            <ol className="mt-3 space-y-2.5">
              {current.recommendations.map((recommendation, index) => (
                <li key={index} className="flex gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-700">
                    {recommendation.order ?? index + 1}
                  </span>
                  <span className="text-[13px] leading-relaxed text-ink-700">
                    {recommendation.description ?? JSON.stringify(recommendation)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </Card>
      )}

      {settledActions.length > 0 && (
        <Card>
          <div className="space-y-3 p-5">
            <h3 className="card-title">Actions already decided</h3>
            {settledActions.map((action) => (
              <ActionProposal key={action.id} action={action} />
            ))}
          </div>
        </Card>
      )}

      {detail && detail.notes.length > 0 && (
        <Card>
          <div className="p-5">
            <h3 className="card-title">History</h3>
            <ol className="mt-3 space-y-3">
              {detail.notes.map((note) => (
                <li key={note.id} className="border-l-2 border-line pl-3">
                  <p className="text-[13px] leading-relaxed text-ink-700">{note.content}</p>
                  <p className="mt-0.5 text-[11px] text-ink-400">
                    {note.author_name ?? 'OASIS'} · {formatDateTime(note.created_at)}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </Card>
      )}
    </div>
  );
}
