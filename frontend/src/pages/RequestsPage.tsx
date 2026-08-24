import {
  useCallback, useEffect, useRef, useState,
  type DragEvent, type FormEvent, type ReactNode,
} from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ClipboardList, Download, File as FileIcon, FileArchive, FileImage, FileSpreadsheet,
  FileText, FileType, Inbox, Paperclip, Pencil, Plus, Send, Trash2, Upload, X,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, SEVERITY_TONE, STATUS_TONE, StatusDot, type Tone } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { Modal } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/auth/AuthContext';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatBytes, formatDateTime, formatRelativeTime, humanize } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type {
  RequestAttachment,
  RequestDirection,
  ServiceRequest,
  ServiceRequestDetail,
  ServiceRequestStatus,
  UserBrief,
} from '@/lib/types';

type Box = 'sent' | 'received';

/**
 * Transitions autorisées, en miroir de request_service.ALLOWED_TRANSITIONS.
 *
 * Cette copie ne sert qu'à décider quels boutons afficher : le backend reste
 * seul juge et refuse toute transition invalide, même si l'interface se
 * trompait.
 */
const NEXT_STATUSES: Record<RequestDirection, Partial<Record<ServiceRequestStatus, ServiceRequestStatus[]>>> = {
  engineer_to_admin: {
    pending: ['in_review', 'approved', 'rejected'],
    in_review: ['approved', 'rejected'],
    approved: ['completed'],
  },
  admin_to_engineer: {
    pending: ['acknowledged', 'in_progress'],
    acknowledged: ['in_progress', 'completed'],
    in_progress: ['completed'],
  },
};

const STATUSES: Record<RequestDirection, ServiceRequestStatus[]> = {
  engineer_to_admin: ['pending', 'in_review', 'approved', 'rejected', 'completed'],
  admin_to_engineer: ['pending', 'acknowledged', 'in_progress', 'completed'],
};

const REQUEST_TYPES = [
  { value: 'increase_capacity', label: 'Increase capacity' },
  { value: 'create_volume', label: 'Create volume' },
  { value: 'create_snapshot', label: 'Create snapshot' },
  { value: 'restore_backup', label: 'Restore backup' },
  { value: 'modify_replication', label: 'Modify replication' },
  { value: 'access_rights', label: 'Access rights' },
  { value: 'other', label: 'Other' },
];

const PRIORITIES = ['low', 'medium', 'high', 'critical'];

/** Miroir de request_service.ATTACHMENT_EXTENSIONS, pour filtrer le sélecteur. */
const ATTACHMENT_ACCEPT = [
  '.pdf', '.txt', '.md', '.log', '.csv', '.json', '.yaml', '.yml',
  '.png', '.jpg', '.jpeg', '.gif', '.webp',
  '.xlsx', '.xls', '.docx', '.doc', '.pptx', '.zip',
].join(',');

/**
 * Libellé affiché pour un statut.
 *
 * « rejected » se lit « Refused » côté interface : le verbe reste sur le
 * bouton d'action, l'état porte le mot que l'utilisateur attend.
 */
const STATUS_LABEL: Record<ServiceRequestStatus, string> = {
  pending: 'Pending',
  in_review: 'In review',
  approved: 'Approved',
  rejected: 'Refused',
  acknowledged: 'Acknowledged',
  in_progress: 'In progress',
  completed: 'Completed',
};

/** Déclinaisons texte et surface des tons, pour la ligne d'état du détail. */
const TONE_TEXT: Record<Tone, string> = {
  neutral: 'text-ink-700',
  brand: 'text-brand-700',
  ok: 'text-ok-600',
  warn: 'text-warn-600',
  danger: 'text-danger-600',
};

const TONE_SURFACE: Record<Tone, string> = {
  neutral: 'border-line bg-slate-50',
  brand: 'border-brand-200 bg-brand-50',
  ok: 'border-ok-200 bg-ok-50',
  warn: 'border-warn-200 bg-warn-50',
  danger: 'border-danger-200 bg-danger-50',
};

/** Libellé d'un bouton d'action, plus parlant que le nom du statut. */
const ACTION_LABEL: Record<ServiceRequestStatus, string> = {
  pending: 'Reopen',
  in_review: 'Start review',
  approved: 'Approve',
  rejected: 'Reject',
  acknowledged: 'Acknowledge',
  in_progress: 'Mark in progress',
  completed: 'Mark completed',
};

/**
 * Quand le statut courant a-t-il été posé, et comment l'annoncer.
 *
 * Une demande tranchée porte sa date de décision (`decided_at`), figée au
 * verdict : la compléter plus tard ne doit pas déplacer le « Refused le… ».
 * Les états intermédiaires n'ont pas d'horodatage dédié en base et se
 * rabattent sur la dernière modification, ou sur la création tant que rien
 * n'a bougé.
 */
function statusMoment(request: ServiceRequest): { verb: string; at: string } {
  switch (request.status) {
    case 'approved':
      return { verb: 'Approved on', at: request.decided_at ?? request.updated_at };
    case 'rejected':
      return { verb: 'Refused on', at: request.decided_at ?? request.updated_at };
    case 'completed':
      return { verb: 'Completed on', at: request.completed_at ?? request.updated_at };
    case 'acknowledged':
      return { verb: 'Acknowledged on', at: request.acknowledged_at ?? request.updated_at };
    case 'in_review':
      return { verb: 'Under review since', at: request.updated_at };
    case 'in_progress':
      return { verb: 'In progress since', at: request.updated_at };
    default:
      return { verb: 'Waiting since', at: request.created_at };
  }
}

/**
 * ISO → valeur d'un `<input type="datetime-local">`.
 *
 * L'input attend une heure locale sans fuseau : `toISOString()` donnerait de
 * l'UTC et décalerait l'échéance affichée à la réouverture du formulaire.
 */
function toDateTimeLocal(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (value: number) => String(value).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function displayName(user: UserBrief | null | undefined): string {
  if (!user) return 'Unknown';
  return user.full_name?.trim() || user.email;
}

export default function RequestsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'administrator';

  const [box, setBox] = useState<Box>('sent');
  const [status, setStatus] = useState<ServiceRequestStatus | 'all'>('all');
  const [formOpen, setFormOpen] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  // Le sens dépend du rôle : ce que j'envoie et ce que je reçois ne suivent
  // pas le même cycle de vie, donc pas les mêmes filtres ni les mêmes actions.
  const sentDirection: RequestDirection = isAdmin ? 'admin_to_engineer' : 'engineer_to_admin';
  const receivedDirection: RequestDirection = isAdmin ? 'engineer_to_admin' : 'admin_to_engineer';
  const direction = box === 'sent' ? sentDirection : receivedDirection;

  const [searchParams, setSearchParams] = useSearchParams();
  useEffect(() => {
    const focus = searchParams.get('request');
    if (focus) {
      setOpenId(focus);
      searchParams.delete('request');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const requests = useResource<ServiceRequest[]>(
    () => api.get<ServiceRequest[]>(`/requests?box=${box}${status === 'all' ? '' : `&status=${status}`}`),
    [box, status],
  );

  // Remettre le filtre à zéro en changeant de section : un statut choisi pour
  // l'une n'existe pas forcément dans l'autre.
  function switchBox(next: Box) {
    setBox(next);
    setStatus('all');
  }

  const sections: { key: Box; label: string; icon: typeof Send }[] = [
    { key: 'sent', label: 'My Requests', icon: Send },
    {
      key: 'received',
      label: isAdmin ? 'Requests From Storage Engineers' : 'Requests From Administrator',
      icon: Inbox,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requests"
        subtitle={
          isAdmin
            ? 'Handle requests from Storage Engineers and send them your own.'
            : 'Track requests sent to the Administrator and handle what they send you.'
        }
        action={
          <Button variant="primary" onClick={() => setFormOpen(true)}>
            <Plus className="h-4 w-4" />
            New Request
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2 border-b border-line pb-px">
        {sections.map((section) => (
          <button
            key={section.key}
            type="button"
            onClick={() => switchBox(section.key)}
            className={cn(
              'inline-flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
              box === section.key
                ? 'border-brand-500 text-brand-700'
                : 'border-transparent text-ink-500 hover:text-ink-700',
            )}
          >
            <section.icon className="h-4 w-4" />
            {section.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {(['all', ...STATUSES[direction]] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setStatus(option as ServiceRequestStatus | 'all')}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-[13px] font-medium transition-colors',
              status === option
                ? 'border-brand-500 bg-brand-500 text-white'
                : 'border-line bg-white text-ink-600 hover:border-brand-200',
            )}
          >
            {option === 'all' ? 'All' : STATUS_LABEL[option]}
          </button>
        ))}
      </div>

      {requests.loading && <Skeleton className="h-28" />}
      {requests.error && <ErrorState message={requests.error} onRetry={requests.reload} />}

      {requests.data && requests.data.length === 0 && (
        <EmptyState
          icon={<ClipboardList className="h-6 w-6" />}
          title={
            box === 'sent'
              ? "You haven't sent any requests yet"
              : 'Nothing has been sent to you yet'
          }
          description={
            box === 'sent'
              ? 'Use New Request to send your first one.'
              : 'Requests addressed to you will appear here.'
          }
        />
      )}

      {requests.data && requests.data.length > 0 && (
        <div className="space-y-3">
          {requests.data.map((request) => (
            <RequestRow key={request.id} request={request} onOpen={() => setOpenId(request.id)} />
          ))}
        </div>
      )}

      <NewRequestModal
        open={formOpen}
        isAdmin={isAdmin}
        onClose={() => setFormOpen(false)}
        onCreated={() => {
          setFormOpen(false);
          switchBox('sent');
          requests.reload();
        }}
      />

      {openId && (
        <RequestDetailModal
          requestId={openId}
          currentUserId={user?.id ?? -1}
          onClose={() => setOpenId(null)}
          onChanged={requests.reload}
          onDeleted={() => {
            setOpenId(null);
            requests.reload();
          }}
        />
      )}
    </div>
  );
}

function RequestRow({ request, onOpen }: { request: ServiceRequest; onOpen: () => void }) {
  const overdue =
    request.deadline !== null &&
    request.status !== 'completed' &&
    new Date(request.deadline).getTime() < Date.now();

  return (
    <Card>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-slate-50"
      >
        <StatusDot tone={STATUS_TONE[request.status] ?? 'neutral'} className="mt-1.5" />

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink-900">{request.title}</p>

          <p className="mt-0.5 truncate text-[13px] text-ink-500">
            {request.request_type && <>{humanize(request.request_type)} &middot; </>}
            created {formatRelativeTime(request.created_at)}
            {' · updated '}
            {formatRelativeTime(request.updated_at)}
            {request.attachment_count > 0 && (
              <>
                {' · '}
                <Paperclip className="inline h-3.5 w-3.5 align-[-2px]" />
                {' '}
                {request.attachment_count}
              </>
            )}
          </p>

          {request.description && (
            <p className="mt-1.5 line-clamp-1 text-[13px] text-ink-600">{request.description}</p>
          )}

          {request.administrator_response && (
            <p className="mt-1.5 line-clamp-1 text-[13px] text-ink-700">
              <span className="font-medium">Response:</span> {request.administrator_response}
            </p>
          )}

          {request.deadline && (
            <p className={cn('mt-1.5 text-[12px]', overdue ? 'text-danger-600' : 'text-ink-500')}>
              Due {formatDateTime(request.deadline)}
              {overdue && ' — overdue'}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Badge tone={SEVERITY_TONE[request.priority] ?? 'neutral'}>{request.priority}</Badge>
          <Badge tone={STATUS_TONE[request.status] ?? 'neutral'}>{STATUS_LABEL[request.status]}</Badge>
        </div>
      </button>
    </Card>
  );
}

/**
 * L'état de la demande en une ligne : où elle en est, et depuis quand.
 *
 * Remplace l'historique déroulant : sur ce canal à deux interlocuteurs, seul
 * le verdict et sa date comptent une fois la demande tranchée.
 */
function StatusLine({ request }: { request: ServiceRequest }) {
  const tone = STATUS_TONE[request.status] ?? 'neutral';
  const { verb, at } = statusMoment(request);

  return (
    <section
      className={cn(
        'flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border px-3 py-2',
        TONE_SURFACE[tone],
      )}
    >
      <StatusDot tone={tone} />
      <span className={cn('text-[13px] font-semibold', TONE_TEXT[tone])}>
        {STATUS_LABEL[request.status]}
      </span>
      <span className="text-[13px] text-ink-600">
        {verb} {formatDateTime(at)}
      </span>
      <span className="text-[13px] text-ink-400">({formatRelativeTime(at)})</span>
    </section>
  );
}

/**
 * Les champs communs à la création et à la correction d'une demande.
 *
 * Le sens de circulation décide de deux d'entre eux : un ingénieur qualifie sa
 * demande par un type, l'administrateur assortit la sienne d'une échéance. Le
 * backend ignore de toute façon celui qui n'a pas cours.
 */
type RequestDraft = {
  title: string;
  requestType: string;
  priority: string;
  description: string;
  deadline: string;
};

const emptyDraft = (): RequestDraft => ({
  title: '',
  requestType: REQUEST_TYPES[0].value,
  priority: 'medium',
  description: '',
  deadline: '',
});

function RequestFields({
  value,
  onChange,
  fromAdmin,
}: {
  value: RequestDraft;
  onChange: (next: RequestDraft) => void;
  fromAdmin: boolean;
}) {
  function set<K extends keyof RequestDraft>(key: K, next: RequestDraft[K]) {
    onChange({ ...value, [key]: next });
  }

  return (
    <>
      <TextField
        label="Title"
        required
        maxLength={200}
        value={value.title}
        onChange={(event) => set('title', event.target.value)}
        placeholder={fromAdmin ? 'Provide the monthly capacity report' : 'Increase capacity on /data'}
      />

      {!fromAdmin && (
        <SelectField
          label="Request type"
          value={value.requestType}
          onChange={(event) => set('requestType', event.target.value)}
        >
          {REQUEST_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </SelectField>
      )}

      <SelectField
        label="Priority"
        value={value.priority}
        onChange={(event) => set('priority', event.target.value)}
      >
        {PRIORITIES.map((option) => (
          <option key={option} value={option}>
            {humanize(option)}
          </option>
        ))}
      </SelectField>

      {fromAdmin && (
        <TextField
          label="Deadline"
          type="datetime-local"
          hint="Optional."
          value={value.deadline}
          onChange={(event) => set('deadline', event.target.value)}
        />
      )}

      <TextAreaField
        label="Description"
        hint="Optional."
        rows={4}
        value={value.description}
        onChange={(event) => set('description', event.target.value)}
      />
    </>
  );
}

/** Formulaire de correction, pré-rempli avec la demande telle qu'elle est. */
function EditRequestForm({
  request,
  onCancel,
  onSaved,
}: {
  request: ServiceRequestDetail;
  onCancel: () => void;
  onSaved: (updated: ServiceRequestDetail) => void;
}) {
  const notify = useToast();
  const fromAdmin = request.direction === 'admin_to_engineer';
  const [draft, setDraft] = useState<RequestDraft>({
    title: request.title,
    requestType: request.request_type ?? REQUEST_TYPES[0].value,
    priority: request.priority,
    description: request.description ?? '',
    deadline: toDateTimeLocal(request.deadline),
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await api.patch<ServiceRequestDetail>(`/requests/${request.id}`, {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        priority: draft.priority,
        // Champs propres à un sens : on ne les envoie que là où ils comptent,
        // pour laisser l'autre intact plutôt que de l'écraser avec null.
        ...(fromAdmin
          ? { deadline: draft.deadline ? new Date(draft.deadline).toISOString() : null }
          : { request_type: draft.requestType }),
      });
      notify({ title: 'Request updated' });
      onSaved(updated);
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Your changes weren't saved",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-6 py-5">
        <RequestFields value={draft} onChange={setDraft} fromAdmin={fromAdmin} />
      </div>
      <div className="flex justify-end gap-2 border-t border-line px-6 py-4">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={saving} disabled={!draft.title.trim()}>
          Save changes
        </Button>
      </div>
    </form>
  );
}

/**
 * Icône d'un fichier d'après son extension.
 *
 * Le type MIME renvoyé par le navigateur est trop irrégulier pour ça — vide
 * sur certains .csv, générique sur les formats Office — alors que l'extension
 * est justement ce que le backend valide.
 */
function fileIcon(filename: string) {
  const extension = filename.slice(filename.lastIndexOf('.')).toLowerCase();
  if (extension === '.pdf') return { Icon: FileType, tone: 'text-danger-600' };
  if (['.png', '.jpg', '.jpeg', '.gif', '.webp'].includes(extension)) {
    return { Icon: FileImage, tone: 'text-brand-600' };
  }
  if (['.csv', '.xlsx', '.xls'].includes(extension)) {
    return { Icon: FileSpreadsheet, tone: 'text-ok-600' };
  }
  if (['.doc', '.docx', '.pptx'].includes(extension)) {
    return { Icon: FileText, tone: 'text-brand-600' };
  }
  if (extension === '.zip') return { Icon: FileArchive, tone: 'text-ink-500' };
  return { Icon: FileIcon, tone: 'text-ink-500' };
}

/** Carte compacte : icône du type, nom, taille, et ce qu'on peut en faire. */
function FileCard({
  filename,
  sizeBytes,
  meta,
  action,
}: {
  filename: string;
  sizeBytes: number;
  meta?: ReactNode;
  action?: ReactNode;
}) {
  const { Icon, tone } = fileIcon(filename);
  return (
    <li className="flex items-center gap-3 rounded-lg border border-line bg-white px-3 py-2">
      <Icon className={cn('h-5 w-5 shrink-0', tone)} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-ink-800">{filename}</p>
        <p className="text-[12px] text-ink-500">
          {formatBytes(sizeBytes)}
          {meta}
        </p>
      </div>
      {action}
    </li>
  );
}

/**
 * Zone de dépôt : glisser-déposer, ou clic pour ouvrir le sélecteur.
 *
 * Purement présentationnelle — elle remonte les fichiers choisis et ne décide
 * pas de leur sort. Des deux côtés, ils attendent une validation explicite :
 * l'envoi du formulaire à la création, l'action ou le bouton Attach dans le
 * détail. Rien ne part sur un simple glisser-déposer.
 */
function DropZone({
  onFiles,
  busy,
  label,
}: {
  onFiles: (files: FileList | null) => void;
  busy?: boolean;
  label: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      onDragOver={(event: DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event: DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        setDragging(false);
        onFiles(event.dataTransfer.files);
      }}
      className={cn(
        'flex flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-4 text-center transition-colors',
        dragging ? 'border-brand-400 bg-brand-50' : 'border-line bg-slate-50',
      )}
    >
      <Upload className="h-5 w-5 text-brand-500" />
      <div>
        <p className="text-[13px] font-medium text-ink-700">{label}</p>
        <p className="mt-0.5 text-[12px] text-ink-500">
          PDF, PNG, JPG, CSV, DOCX, XLSX, TXT — max 10 MB per file.
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ATTACHMENT_ACCEPT}
        className="hidden"
        onChange={(event) => {
          onFiles(event.target.files);
          // Remis à zéro pour que redéposer le même fichier déclenche bien
          // un nouveau change.
          event.target.value = '';
        }}
      />
      {/* type="button" explicite : la zone de dépôt vit aussi dans le
          formulaire de création, où un bouton sans type l'enverrait. */}
      <Button type="button" size="sm" loading={busy} onClick={() => inputRef.current?.click()}>
        Browse
      </Button>
    </div>
  );
}

/** Les fichiers choisis mais pas encore envoyés — retirables un par un. */
function StagedFileList({
  files,
  onRemove,
  busy,
}: {
  files: File[];
  onRemove: (index: number) => void;
  busy?: boolean;
}) {
  return (
    <ul className="space-y-1.5">
      {files.map((file, index) => (
        <FileCard
          key={`${file.name}-${file.lastModified}-${index}`}
          filename={file.name}
          sizeBytes={file.size}
          meta=" · not sent yet"
          action={
            <button
              type="button"
              disabled={busy}
              onClick={() => onRemove(index)}
              aria-label={`Remove ${file.name}`}
              className="focus-ring rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-danger-50 hover:text-danger-600 disabled:opacity-50"
            >
              <X className="h-4 w-4" />
            </button>
          }
        />
      ))}
    </ul>
  );
}

/** Les fichiers déjà déposés sur une demande, avec téléchargement et retrait. */
function AttachmentList({
  requestId,
  attachments,
  currentUserId,
  onRemove,
  busy,
}: {
  requestId: string;
  attachments: RequestAttachment[];
  currentUserId: number;
  onRemove: (attachment: RequestAttachment) => void;
  busy?: boolean;
}) {
  const notify = useToast();
  const [downloading, setDownloading] = useState<string | null>(null);

  async function download(attachment: RequestAttachment) {
    setDownloading(attachment.id);
    try {
      // Passe par un blob : un <a href> n'emporterait pas l'en-tête
      // Authorization et la route répondrait 401.
      await api.download(
        `/requests/${requestId}/attachments/${attachment.id}`,
        attachment.filename,
      );
    } catch (caught) {
      notify({
        tone: 'error',
        title: "That file couldn't be downloaded",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setDownloading(null);
    }
  }

  return (
    <ul className="space-y-1.5">
      {attachments.map((attachment) => (
        <FileCard
          key={attachment.id}
          filename={attachment.filename}
          sizeBytes={attachment.size_bytes}
          meta={
            <>
              {' · '}
              {displayName(attachment.uploader)} · {formatRelativeTime(attachment.created_at)}
            </>
          }
          action={
            <div className="flex shrink-0 items-center gap-1">
              <Button
                type="button"
                size="sm"
                loading={downloading === attachment.id}
                icon={<Download className="h-4 w-4" />}
                onClick={() => void download(attachment)}
              >
                Download
              </Button>
              {/* Retirer un dépôt reste l'affaire de celui qui l'a fait. */}
              {attachment.uploader?.id === currentUserId && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onRemove(attachment)}
                  aria-label={`Remove ${attachment.filename}`}
                  className="focus-ring rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-danger-50 hover:text-danger-600 disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          }
        />
      ))}
    </ul>
  );
}

function RequestDetailModal({
  requestId,
  currentUserId,
  onClose,
  onChanged,
  onDeleted,
}: {
  requestId: string;
  currentUserId: number;
  onClose: () => void;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const notify = useToast();
  const [detail, setDetail] = useState<ServiceRequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState('');
  // Fichiers choisis mais pas encore envoyés : ils partent avec l'action, ou
  // sur le bouton Attach, jamais sur un simple glisser-déposer.
  const [staged, setStaged] = useState<File[]>([]);
  // 'view' lit la demande, 'edit' la corrige, 'delete' demande confirmation.
  const [mode, setMode] = useState<'view' | 'edit' | 'delete'>('view');

  const load = useCallback(async () => {
    try {
      const found = await api.get<ServiceRequestDetail>(`/requests/${requestId}`);
      setDetail(found);
      setResponse(found.administrator_response ?? '');
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong.');
    }
  }, [requestId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(work: () => Promise<ServiceRequestDetail>, success: string) {
    setBusy(true);
    try {
      const updated = await work();
      setDetail(updated);
      onChanged();
      notify({ title: success });
    } catch (caught) {
      notify({
        tone: 'error',
        title: "That didn't work",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  /**
   * Envoie les fichiers en attente, un par un.
   *
   * Ce qui est passé quitte la file, ce qui reste y demeure : un échec au
   * troisième fichier ne fait pas redéposer les deux premiers.
   */
  async function flushStaged(): Promise<ServiceRequestDetail | null> {
    if (!detail || staged.length === 0) return null;
    let latest = detail;
    const remaining = [...staged];
    try {
      while (remaining.length > 0) {
        latest = await api.upload<ServiceRequestDetail>(
          `/requests/${detail.id}/attachments`,
          remaining[0],
        );
        remaining.shift();
      }
      return latest;
    } finally {
      setStaged(remaining);
      setDetail(latest);
    }
  }

  /** Dépose les fichiers en attente sans toucher au statut. */
  async function attachNow() {
    const count = staged.length;
    const first = staged[0]?.name;
    setBusy(true);
    try {
      await flushStaged();
      onChanged();
      notify({ title: count > 1 ? `${count} files attached` : `${first} attached` });
    } catch (caught) {
      notify({
        tone: 'error',
        title: "That file couldn't be attached",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  /**
   * Fait avancer le statut, en emportant les fichiers en attente.
   *
   * C'est le cas courant : on dépose le rapport demandé, puis on clique
   * « Mark completed ». Les fichiers partent d'abord — si l'envoi échoue, le
   * statut ne bouge pas et la demande n'est pas marquée terminée sans sa
   * pièce justificative.
   */
  async function applyStatus(target: ServiceRequestStatus) {
    if (!detail) return;
    setBusy(true);
    try {
      await flushStaged();
      const updated = await api.patch<ServiceRequestDetail>(
        `/requests/${detail.id}/status`,
        {
          status: target,
          ...(isAdmin && response.trim() ? { administrator_response: response.trim() } : {}),
        },
      );
      setDetail(updated);
      onChanged();
      notify({ title: `Request marked ${STATUS_LABEL[target].toLowerCase()}` });
    } catch (caught) {
      notify({
        tone: 'error',
        title: "That didn't work",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function detach(attachment: RequestAttachment) {
    if (!detail) return;
    await run(
      () =>
        api.delete<ServiceRequestDetail>(
          `/requests/${detail.id}/attachments/${attachment.id}`,
        ),
      `${attachment.filename} removed`,
    );
  }

  async function remove() {
    if (!detail) return;
    setBusy(true);
    try {
      await api.delete(`/requests/${detail.id}`);
      notify({ title: 'Request deleted' });
      // La modale se ferme dans la foulée : pas de setBusy(false) à faire.
      onDeleted();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "The request wasn't deleted",
        detail: caught instanceof Error ? caught.message : undefined,
      });
      setBusy(false);
    }
  }

  const isAssignee = detail?.assignee?.id === currentUserId;
  const isAdmin = detail?.assignee?.role === 'administrator' && isAssignee;
  const nextStatuses = detail ? NEXT_STATUSES[detail.direction][detail.status] ?? [] : [];
  // Corriger ou retirer sa propre demande reste possible tant que le
  // destinataire ne s'en est pas saisi — au-delà, le backend refuse.
  const canManage = detail?.creator?.id === currentUserId && detail?.status === 'pending';
  const canAct = isAssignee && nextStatuses.length > 0;

  return (
    <Modal
      open
      onClose={onClose}
      title={detail?.title ?? 'Request'}
      subtitle={
        detail
          ? `${displayName(detail.creator)} → ${displayName(detail.assignee)} · created ${formatDateTime(detail.created_at)}`
          : undefined
      }
      className="max-w-xl"
    >
      {detail && mode === 'edit' && (
        <EditRequestForm
          request={detail}
          onCancel={() => setMode('view')}
          onSaved={(updated) => {
            setDetail(updated);
            onChanged();
            setMode('view');
          }}
        />
      )}

      {detail && mode === 'delete' && (
        <>
          <div className="px-6 py-5">
            <p className="text-sm text-ink-700">
              Delete this request? It leaves your list and {displayName(detail.assignee)}
              &rsquo;s inbox, and cannot be recovered.
            </p>
          </div>
          <div className="flex justify-end gap-2 border-t border-line px-6 py-4">
            <Button type="button" onClick={() => setMode('view')}>
              Keep it
            </Button>
            <Button variant="danger" loading={busy} onClick={() => void remove()}>
              Delete
            </Button>
          </div>
        </>
      )}

      {mode === 'view' && (
        <>
          <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
            {error && <ErrorState message={error} onRetry={load} />}
            {!detail && !error && <Skeleton className="h-32" />}

            {detail && (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge tone={STATUS_TONE[detail.status] ?? 'neutral'}>
                    {STATUS_LABEL[detail.status]}
                  </Badge>
                  <Badge tone={SEVERITY_TONE[detail.priority] ?? 'neutral'}>
                    {detail.priority} priority
                  </Badge>
                  {detail.request_type && <Badge>{humanize(detail.request_type)}</Badge>}
                  {detail.deadline && (
                    <Badge tone="warn">Due {formatDateTime(detail.deadline)}</Badge>
                  )}
                </div>

                {detail.description && (
                  <section>
                    <h3 className="mb-1 text-[13px] font-semibold text-ink-700">Description</h3>
                    <p className="whitespace-pre-wrap text-sm text-ink-600">{detail.description}</p>
                  </section>
                )}

                {detail.administrator_response && (
                  <section className="rounded-lg bg-brand-50 px-4 py-3">
                    <h3 className="mb-1 text-[13px] font-semibold text-brand-700">
                      Administrator response
                    </h3>
                    <p className="whitespace-pre-wrap text-sm text-ink-700">
                      {detail.administrator_response}
                    </p>
                  </section>
                )}

                <StatusLine request={detail} />

                {/* Reçus : masqués tant que rien n'a été déposé. */}
                {detail.attachments.length > 0 && (
                  <section>
                    <h3 className="mb-2 text-[13px] font-semibold text-ink-700">
                      Attachments ({detail.attachments.length})
                    </h3>
                    <AttachmentList
                      requestId={detail.id}
                      attachments={detail.attachments}
                      currentUserId={currentUserId}
                      onRemove={(attachment) => void detach(attachment)}
                      busy={busy}
                    />
                  </section>
                )}

                {/* Dépôt : toujours accessible, au-dessus des actions. */}
                <section>
                  <h3 className="mb-2 text-[13px] font-semibold text-ink-700">Add a file</h3>
                  {staged.length > 0 && (
                    <div className="mb-2">
                      <StagedFileList
                        files={staged}
                        busy={busy}
                        onRemove={(index) =>
                          setStaged((current) => current.filter((_, i) => i !== index))
                        }
                      />
                    </div>
                  )}
                  <DropZone
                    label="Drop a file here"
                    onFiles={(files) =>
                      files && setStaged((current) => [...current, ...Array.from(files)])
                    }
                  />
                  {staged.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
                      <p className="mr-auto text-[12px] text-ink-500">
                        {canAct
                          ? 'Sent with the action below, or attach them now.'
                          : `${staged.length} file${staged.length > 1 ? 's' : ''} ready to send.`}
                      </p>
                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        loading={busy}
                        onClick={() => void attachNow()}
                      >
                        Attach
                      </Button>
                    </div>
                  )}
                </section>

                {/* Actions : réservées au destinataire, et limitées aux transitions
                    que le backend acceptera. */}
                {canAct && (
                  <section className="rounded-lg border border-line px-4 py-3">
                    <h3 className="mb-2 text-[13px] font-semibold text-ink-700">Actions</h3>
                    {isAdmin && (
                      <TextAreaField
                        label="Response (optional)"
                        rows={2}
                        className="mb-3"
                        value={response}
                        onChange={(event) => setResponse(event.target.value)}
                        placeholder="Explain your decision to the engineer."
                      />
                    )}
                    <div className="flex flex-wrap gap-2">
                      {nextStatuses.map((target) => (
                        <Button
                          key={target}
                          variant={target === 'rejected' ? 'danger' : 'primary'}
                          loading={busy}
                          onClick={() => void applyStatus(target)}
                        >
                          {ACTION_LABEL[target]}
                        </Button>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>

          {canManage && (
            <div className="flex justify-end gap-2 border-t border-line px-6 py-3">
              <Button onClick={() => setMode('edit')}>
                <Pencil className="h-4 w-4" />
                Edit
              </Button>
              <Button variant="ghost" onClick={() => setMode('delete')}>
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}

function NewRequestModal({
  open,
  isAdmin,
  onClose,
  onCreated,
}: {
  open: boolean;
  isAdmin: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const notify = useToast();
  const [draft, setDraft] = useState<RequestDraft>(emptyDraft);
  // Les fichiers attendent la création : ils n'ont pas de demande à laquelle
  // se rattacher tant qu'elle n'existe pas.
  const [pending, setPending] = useState<File[]>([]);
  const [recipients, setRecipients] = useState<UserBrief[]>([]);
  const [assignedTo, setAssignedTo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    api
      .get<UserBrief[]>('/requests/recipients')
      .then((found) => {
        setRecipients(found);
        if (found.length > 0) setAssignedTo(String(found[0].id));
      })
      .catch(() => setRecipients([]));
  }, [open]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await api.post<ServiceRequestDetail>('/requests', {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        // Le type qualifie une demande d'ingénieur ; une consigne envoyée par
        // l'administrateur n'en a pas.
        request_type: isAdmin ? null : draft.requestType,
        priority: draft.priority,
        deadline: isAdmin && draft.deadline ? new Date(draft.deadline).toISOString() : null,
        assigned_to: assignedTo ? Number(assignedTo) : null,
      });
      // La demande est partie : un dépôt qui échoue ne doit pas la faire
      // passer pour un échec, mais doit se dire clairement.
      const failed: string[] = [];
      for (const file of pending) {
        try {
          await api.upload<ServiceRequestDetail>(`/requests/${created.id}/attachments`, file);
        } catch {
          failed.push(file.name);
        }
      }

      if (failed.length > 0) {
        notify({
          tone: 'error',
          title: `Request sent, but ${failed.join(', ')} couldn't be attached`,
          detail: 'Open the request to try again.',
        });
      } else {
        notify({
          title: 'Request sent',
          detail: isAdmin
            ? 'The Storage Engineer will see it in their inbox.'
            : 'The Administrator will review it.',
        });
      }

      setDraft(emptyDraft());
      setPending([]);
      onCreated();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Your request couldn't be sent",
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
      subtitle={isAdmin ? 'Send a request to a Storage Engineer.' : 'Send a request to the Administrator.'}
    >
      <form onSubmit={handleSubmit}>
        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-6 py-5">
          <RequestFields value={draft} onChange={setDraft} fromAdmin={isAdmin} />

          <div>
            <p className="mb-1.5 text-[13px] font-medium text-ink-800">
              Attachments <span className="font-normal text-ink-500">(optional)</span>
            </p>
            {pending.length > 0 && (
              <div className="mb-2">
                <StagedFileList
                  files={pending}
                  onRemove={(index) =>
                    setPending((current) => current.filter((_, i) => i !== index))
                  }
                />
              </div>
            )}
            <DropZone
              label="Drop a file here"
              onFiles={(files) =>
                files && setPending((current) => [...current, ...Array.from(files)])
              }
            />
            <p className="mt-1.5 text-[12px] text-ink-500">
              Files are uploaded once the request is sent.
            </p>
          </div>

          {/* Un seul destinataire possible : inutile de faire choisir. */}
          {recipients.length > 1 && (
            <SelectField
              label="Recipient"
              value={assignedTo}
              onChange={(event) => setAssignedTo(event.target.value)}
            >
              {recipients.map((person) => (
                <option key={person.id} value={person.id}>
                  {displayName(person)}
                </option>
              ))}
            </SelectField>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-line px-6 py-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={submitting} disabled={!draft.title.trim()}>
            Send request
          </Button>
        </div>
      </form>
    </Modal>
  );
}
