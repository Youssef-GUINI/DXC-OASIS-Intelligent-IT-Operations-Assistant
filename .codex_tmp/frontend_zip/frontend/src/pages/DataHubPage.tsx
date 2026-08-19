import { useRef, useState, type DragEvent } from 'react';
import { Eye, FileText, Trash2, Upload } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/Card';
import { Badge, STATUS_TONE } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Overlay';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatBytes, formatRelativeTime } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { KnowledgeDocument } from '@/lib/types';

const ACCEPTED = '.md,.txt,.log,.json,.yaml,.yml,.csv,.pdf';

export default function DataHubPage() {
  const notify = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<{ filename: string; text: string } | null>(null);
  const [pendingDelete, setPendingDelete] = useState<KnowledgeDocument | null>(null);

  const { data, error, loading, reload } = useResource<KnowledgeDocument[]>(
    () => api.get<KnowledgeDocument[]>('/storage/documents'),
    [],
  );

  async function uploadFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        const document = await api.upload<KnowledgeDocument>('/storage/documents', file);
        if (document.status === 'failed') {
          notify({
            tone: 'error',
            title: `${file.name} was saved but not indexed`,
            detail: document.error ?? 'OASIS could not read this document.',
          });
        } else {
          notify({
            title: `${file.name} is now part of your knowledge base`,
            detail: `OASIS indexed ${document.chunk_count} passages from it.`,
          });
        }
      } catch (caught) {
        notify({
          tone: 'error',
          title: `${file.name} could not be uploaded`,
          detail: caught instanceof Error ? caught.message : undefined,
        });
      }
    }
    setUploading(false);
    reload();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    void uploadFiles(event.dataTransfer.files);
  }

  async function openPreview(document: KnowledgeDocument) {
    try {
      const result = await api.get<{ filename: string; text: string }>(
        `/storage/documents/${document.id}/content`,
      );
      setPreview(result);
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't open this document",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    try {
      await api.delete(`/storage/documents/${pendingDelete.id}`);
      notify({
        title: `${pendingDelete.filename} removed`,
        detail: 'OASIS will no longer use it when answering you.',
      });
      setPendingDelete(null);
      reload();
    } catch (caught) {
      notify({
        tone: 'error',
        title: "Couldn't remove this document",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    }
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="Data Hub"
        subtitle="Add your own runbooks and notes so OASIS can use them when it answers you."
      />

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'card flex flex-col items-center justify-center gap-3 border-dashed px-6 py-10 text-center transition-colors',
          dragging ? 'border-brand-400 bg-brand-50' : 'border-line',
        )}
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-500">
          <Upload className="h-5 w-5" />
        </span>
        <div>
          <p className="text-[15px] font-medium text-ink-900">Drop a document here</p>
          <p className="mt-1 text-[13px] text-ink-500">
            Markdown, text, YAML, JSON, CSV or PDF — up to 10 MB each.
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={(event) => {
            void uploadFiles(event.target.files);
            event.target.value = '';
          }}
        />
        <Button variant="primary" loading={uploading} onClick={() => inputRef.current?.click()}>
          Choose a file
        </Button>
      </div>

      <Card className="mt-4">
        {loading && (
          <div className="space-y-3 p-5">
            {[0, 1].map((row) => (
              <Skeleton key={row} className="h-14" />
            ))}
          </div>
        )}

        {error && !loading && <ErrorState message={error} onRetry={reload} />}

        {data && !loading && data.length === 0 && (
          <EmptyState
            icon={<FileText className="h-7 w-7" />}
            title="Your knowledge base is empty"
            description="Upload the runbooks and procedures your team actually uses, and OASIS will draw on them."
          />
        )}

        {data && data.length > 0 && (
          <ul className="divide-y divide-line">
            {data.map((document) => (
              <li key={document.id} className="flex items-center gap-4 px-5 py-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-ink-500">
                  <FileText className="h-4 w-4" />
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium text-ink-900">{document.filename}</p>
                  <p className="mt-0.5 truncate text-[12px] text-ink-500">
                    {formatBytes(document.size_bytes)} · added {formatRelativeTime(document.created_at)}
                    {document.status === 'indexed' && ` · ${document.chunk_count} passages indexed`}
                    {document.status === 'failed' && document.error && ` · ${document.error}`}
                  </p>
                </div>

                <Badge tone={STATUS_TONE[document.status] ?? 'neutral'}>{document.status}</Badge>

                <div className="flex shrink-0 gap-0.5">
                  <button
                    onClick={() => void openPreview(document)}
                    aria-label={`View ${document.filename}`}
                    className="focus-ring rounded-lg p-2 text-ink-400 transition-colors hover:bg-slate-100 hover:text-ink-700"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPendingDelete(document)}
                    aria-label={`Delete ${document.filename}`}
                    className="focus-ring rounded-lg p-2 text-ink-400 transition-colors hover:bg-danger-50 hover:text-danger-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Modal
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={preview?.filename ?? ''}
        subtitle="This is the text OASIS reads from your document."
        className="max-w-3xl"
      >
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap px-6 py-5 text-[13px] leading-relaxed text-ink-700">
          {preview?.text}
        </pre>
      </Modal>

      <Modal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title="Remove this document?"
        subtitle={`${pendingDelete?.filename} will be deleted and OASIS will stop using it.`}
        className="max-w-md"
      >
        <div className="flex justify-end gap-2 px-6 py-5">
          <Button onClick={() => setPendingDelete(null)}>Keep it</Button>
          <Button variant="danger" onClick={() => void confirmDelete()}>
            Remove
          </Button>
        </div>
      </Modal>
    </div>
  );
}
