import { useState, type FormEvent } from 'react';
import { CheckCircle2, Clock, Send, ShieldQuestion, XCircle } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Badge, type Tone } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/auth/AuthContext';
import { api } from '@/lib/api';
import { formatDateTime, formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { AccessRequest } from '@/lib/types';

const WORKSPACES = ['storage', 'linux', 'admin'];

function statusTone(status: string): Tone {
  if (status === 'approved') return 'ok';
  if (status === 'rejected') return 'danger';
  if (status === 'pending') return 'warn';
  return 'neutral';
}

/** Vue admin : approuve ou rejette les demandes en attente. */
function AdminRequestsView() {
  const notify = useToast();
  const [busy, setBusy] = useState<number | null>(null);
  const { data, error, loading, reload } = useResource<AccessRequest[]>(
    () => api.get<AccessRequest[]>('/cross-domain/requests/pending'),
    [],
  );

  async function decide(request: AccessRequest, approve: boolean) {
    setBusy(request.id);
    try {
      await api.post(`/cross-domain/requests/${request.id}/decision`, { approve });
      notify({ title: approve ? `Request #${request.id} approved` : `Request #${request.id} rejected` });
      reload();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't update this request",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Pending access requests"
        subtitle="Cross-domain access requests waiting for a decision."
      />

      {loading && (
        <div className="space-y-3 p-5">
          {[0, 1].map((row) => (
            <Skeleton key={row} className="h-16" />
          ))}
        </div>
      )}

      {error && !loading && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && !loading && (
        <EmptyState
          icon={<ShieldQuestion className="h-7 w-7" />}
          title="No pending requests"
          description="Nothing waiting for your review right now."
        />
      )}

      {data && data.length > 0 && (
        <ul className="divide-y divide-line">
          {data.map((request) => (
            <li key={request.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-medium text-ink-900">
                    User #{request.requested_by_id} → {humanize(request.target_workspace)}
                  </span>
                  <Badge tone={statusTone(request.status)}>{request.status}</Badge>
                </span>
                {request.reason && (
                  <span className="mt-0.5 block text-[12.5px] text-ink-500">{request.reason}</span>
                )}
                <span className="mt-0.5 block text-[11px] text-ink-400">
                  requested {formatRelativeTime(request.created_at)}
                </span>
              </span>
              <span className="flex shrink-0 gap-2">
                <Button
                  size="sm"
                  icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                  loading={busy === request.id}
                  onClick={() => void decide(request, true)}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={<XCircle className="h-3.5 w-3.5" />}
                  loading={busy === request.id}
                  onClick={() => void decide(request, false)}
                >
                  Reject
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Vue ingénieur : demande l'accès à un autre workspace. */
function CreateRequestView() {
  const notify = useToast();
  const [targetWorkspace, setTargetWorkspace] = useState(WORKSPACES[0]);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState<AccessRequest[]>([]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.post<AccessRequest>('/cross-domain/requests', {
        target_workspace: targetWorkspace,
        reason,
      });
      setSent((current) => [created, ...current]);
      setReason('');
      notify({ title: 'Access request sent', detail: 'An administrator will review it shortly.' });
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't send the request",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Request cross-domain access"
          subtitle="Ask an administrator for temporary access to another workspace."
        />
        <CardBody className="pt-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-ink-700">Target workspace</label>
              <select
                value={targetWorkspace}
                onChange={(event) => setTargetWorkspace(event.target.value)}
                className="h-10 w-full rounded-lg border border-line bg-white px-3 text-[14px] text-ink-900 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
              >
                {WORKSPACES.map((workspace) => (
                  <option key={workspace} value={workspace}>
                    {humanize(workspace)}
                  </option>
                ))}
              </select>
            </div>

            <TextField
              label="Reason"
              as="textarea"
              rows={3}
              required
              placeholder="Why do you need access to this workspace?"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />

            <Button type="submit" variant="primary" loading={submitting} icon={<Send className="h-4 w-4" />}>
              Send request
            </Button>
          </form>
        </CardBody>
      </Card>

      {sent.length > 0 && (
        <Card>
          <CardHeader title="Sent this session" />
          <ul className="divide-y divide-line">
            {sent.map((request) => (
              <li key={request.id} className="flex items-center gap-3 px-5 py-3.5">
                <Clock className="h-4 w-4 shrink-0 text-ink-400" />
                <span className="min-w-0 flex-1 text-[13px] text-ink-700">
                  Access to <span className="font-medium">{humanize(request.target_workspace)}</span>
                </span>
                <Badge tone={statusTone(request.status)}>{request.status}</Badge>
                <span className="shrink-0 text-[12px] text-ink-400">
                  {formatDateTime(request.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

export default function RequestsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'administrator';

  return (
    <div className="mx-auto max-w-[900px]">
      <PageHeader
        title="Requests"
        subtitle={
          isAdmin
            ? 'Review and decide on cross-domain access requests.'
            : 'Request temporary access to another workspace.'
        }
      />
      {isAdmin ? <AdminRequestsView /> : <CreateRequestView />}
    </div>
  );
}