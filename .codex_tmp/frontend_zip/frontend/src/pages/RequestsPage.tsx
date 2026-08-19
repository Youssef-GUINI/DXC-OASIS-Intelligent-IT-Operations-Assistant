import { useState, type FormEvent } from 'react';
import { ClipboardList, Plus } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, STATUS_TONE, StatusDot } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { Modal } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { RequestStatus, StorageRequest } from '@/lib/types';

type Filter = 'all' | RequestStatus;

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'confirmed', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'completed', label: 'Completed' },
];

const REQUEST_TYPES = [
  { value: 'increase_capacity', label: 'Increase capacity' },
  { value: 'create_volume', label: 'Create volume' },
  { value: 'create_snapshot', label: 'Create snapshot' },
  { value: 'restore_backup', label: 'Restore backup' },
  { value: 'modify_replication', label: 'Modify replication' },
  { value: 'other', label: 'Other' },
];

const PRIORITIES = ['low', 'medium', 'high', 'critical'];

export default function RequestsPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [formOpen, setFormOpen] = useState(false);

  const { data, error, loading, reload } = useResource<StorageRequest[]>(
    () => api.get<StorageRequest[]>(`/storage/actions${filter === 'all' ? '' : `?status=${filter}`}`),
    [filter],
  );

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="My Requests"
        subtitle="Track requests submitted to the administrator."
        action={
          <Button variant="primary" icon={<Plus className="h-4 w-4" />} onClick={() => setFormOpen(true)}>
            New Request
          </Button>
        }
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
            icon={<ClipboardList className="h-7 w-7" />}
            title={filter === 'all' ? "You haven't submitted any requests yet" : `No ${filter} requests`}
            description="When you need more capacity, a new volume or a restore, send it here and the administrator will review it."
            action={
              <Button variant="primary" icon={<Plus className="h-4 w-4" />} onClick={() => setFormOpen(true)}>
                New Request
              </Button>
            }
          />
        )}

        {data && data.length > 0 && (
          <ul className="divide-y divide-line">
            {data.map((request) => (
              <li key={request.id} className="flex items-center gap-4 px-5 py-4">
                <StatusDot tone={STATUS_TONE[request.status] ?? 'neutral'} />

                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium text-ink-900">
                    {humanize(request.action_type)}
                  </p>
                  <p className="mt-0.5 truncate text-[12px] text-ink-500">
                    {request.target} · submitted {formatRelativeTime(request.created_at)}
                    {request.parameters.priority && ` · ${request.parameters.priority} priority`}
                  </p>
                </div>

                <Badge tone={STATUS_TONE[request.status] ?? 'neutral'}>
                  {request.status === 'confirmed' ? 'approved' : humanize(request.status)}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <NewRequestModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmitted={() => {
          setFormOpen(false);
          reload();
        }}
      />
    </div>
  );
}

function NewRequestModal({
  open,
  onClose,
  onSubmitted,
}: {
  open: boolean;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const notify = useToast();
  const [actionType, setActionType] = useState(REQUEST_TYPES[0].value);
  const [target, setTarget] = useState('');
  const [priority, setPriority] = useState('medium');
  const [description, setDescription] = useState('');
  const [justification, setJustification] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setActionType(REQUEST_TYPES[0].value);
    setTarget('');
    setPriority('medium');
    setDescription('');
    setJustification('');
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.post<StorageRequest>('/storage/actions/', {
        action_type: actionType,
        target: target.trim(),
        parameters: { priority, description: description.trim(), justification: justification.trim() },
      });
      notify({
        title: 'Request submitted successfully',
        detail: `${created.id.slice(0, 8).toUpperCase()} has been sent to the administrator for review.`,
      });
      reset();
      onSubmitted();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Your request couldn't be submitted",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New request"
      subtitle="The administrator reviews every request before anything changes."
    >
      <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
        <SelectField
          label="Request type"
          value={actionType}
          onChange={(event) => setActionType(event.target.value)}
        >
          {REQUEST_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </SelectField>

        <TextField
          label="Resource"
          required
          placeholder="e.g. /data/prod or vol-prod-db01"
          hint="The volume, mountpoint or backup job this concerns."
          value={target}
          onChange={(event) => setTarget(event.target.value)}
        />

        <SelectField
          label="Priority"
          value={priority}
          onChange={(event) => setPriority(event.target.value)}
        >
          {PRIORITIES.map((level) => (
            <option key={level} value={level}>
              {humanize(level)}
            </option>
          ))}
        </SelectField>

        <TextAreaField
          label="Description"
          required
          rows={3}
          placeholder="What needs to change?"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />

        <TextAreaField
          label="Justification"
          rows={2}
          placeholder="Why now? What happens if it waits?"
          hint="This is what the administrator reads first."
          value={justification}
          onChange={(event) => setJustification(event.target.value)}
        />

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={submitting}>
            Submit Request
          </Button>
        </div>
      </form>
    </Modal>
  );
}
