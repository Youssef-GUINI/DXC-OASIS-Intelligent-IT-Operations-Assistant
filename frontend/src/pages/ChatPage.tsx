import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowUp,
  MessageSquare,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { ActionProposal } from '@/components/ActionProposal';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { Drawer, Modal } from '@/components/ui/Overlay';
import { Skeleton } from '@/components/ui/States';
import { useToast } from '@/components/ui/Toast';
import { api, ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';
import { useAuth } from '@/auth/AuthContext';
import type { ActionRequest } from '@/lib/types';

/** Un fil de discussion, tel que le backend le conserve. */
type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  /** Renseigné pour un fil ouvert depuis un incident. */
  incident_ticket_id: string | null;
};

type ChatMessageDto = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  action_requests: ActionRequest[];
};

type ChatTurn = {
  response: string;
  conversation: Conversation;
  user_message: ChatMessageDto;
  assistant_message: ChatMessageDto;
};

type Message = {
  /** Identifiant serveur, ou clé locale `local-…` tant que le tour n'est pas enregistré. */
  id: string;
  author: 'user' | 'oasis';
  text: string;
  at: Date;
  failed?: boolean;
  /**
   * Remédiations que ce message propose. Elles s'affichent en boutons sous la
   * bulle : annoncées en texte seul, elles se liraient comme des actions déjà
   * lancées, alors qu'aucune ne part sans le clic de l'ingénieur.
   */
  actions?: ActionRequest[];
};

const SUGGESTIONS = [
  'Show storage health',
  'Check failed backups',
  'Show critical incidents',
  'Which volumes are near capacity?',
  'Show recent snapshots',
];

function toMessage(dto: ChatMessageDto): Message {
  return {
    id: String(dto.id),
    author: dto.role === 'user' ? 'user' : 'oasis',
    text: dto.content,
    at: new Date(dto.created_at),
    actions: dto.action_requests ?? [],
  };
}

function errorMessage(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback;
}

function Timestamp({ at }: { at: Date }) {
  return (
    <time className="text-[11px] text-ink-400">
      {at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
    </time>
  );
}

function TypingIndicator() {
  return (
    <span className="flex items-center gap-1 py-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}

function HistorySkeleton() {
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Skeleton className="h-10 w-52" />
      </div>
      <div className="flex items-start gap-3">
        <Skeleton className="h-8 w-8 rounded-full" />
        <Skeleton className="h-20 w-2/3" />
      </div>
    </div>
  );
}

/** Liste des fils — réutilisée dans la colonne de gauche et dans le tiroir mobile. */
function ConversationList({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: {
  conversations: Conversation[];
  activeId: number | null;
  loading: boolean;
  onSelect: (conversation: Conversation) => void;
  onNew: () => void;
  onRename: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="px-3 pt-3">
        <Button
          className="w-full"
          size="sm"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={onNew}
        >
          New conversation
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        {loading && (
          <div className="space-y-2 px-1">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        )}

        {!loading && conversations.length === 0 && (
          <p className="px-3 py-6 text-center text-[12px] leading-relaxed text-ink-500">
            Your conversations will show up here, and stay available when you come back.
          </p>
        )}

        <ul className="space-y-0.5">
          {conversations.map((conversation) => (
            <li key={conversation.id} className="group relative">
              <button
                onClick={() => onSelect(conversation)}
                className={cn(
                  'focus-ring w-full rounded-lg px-3 py-2 pr-14 text-left transition-colors',
                  conversation.id === activeId
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-ink-700 hover:bg-slate-100',
                )}
              >
                <span className="flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 text-ink-400" />
                  <span className="truncate text-[13px] font-medium">{conversation.title}</span>
                </span>
                <span className="mt-0.5 block pl-[22px] text-[11px] text-ink-400">
                  {formatRelativeTime(conversation.updated_at)}
                </span>
              </button>

              {/* Visibles au survol : la liste reste lisible, les actions
                  destructrices ne sont pas à portée de clic distrait. */}
              <span className="absolute right-1.5 top-1.5 hidden gap-0.5 group-hover:flex group-focus-within:flex">
                <button
                  onClick={() => onRename(conversation)}
                  aria-label={`Rename ${conversation.title}`}
                  className="focus-ring rounded-md p-1.5 text-ink-400 transition-colors hover:bg-white hover:text-ink-700"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onDelete(conversation)}
                  aria-label={`Delete ${conversation.title}`}
                  className="focus-ring rounded-md p-1.5 text-ink-400 transition-colors hover:bg-white hover:text-danger-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { user } = useAuth();
  const notify = useToast();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [activeId, setActiveId] = useState<number | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const [draft, setDraft] = useState('');
  const [thinking, setThinking] = useState(false);

  const [listOpen, setListOpen] = useState(false);
  const [renaming, setRenaming] = useState<Conversation | null>(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null);
  const [busy, setBusy] = useState(false);

  const [searchParams, setSearchParams] = useSearchParams();
  // Lu une fois : le paramètre est retiré aussitôt, mais l'effet de montage
  // doit encore savoir quel fil ouvrir.
  const requestedConversation = useRef(searchParams.get('conversation'));

  const endRef = useRef<HTMLDivElement>(null);
  // Le fil demandé en dernier : une réponse arrivée après un changement de
  // conversation ne doit pas écraser celle qui est affichée.
  const requestedId = useRef<number | null>(null);

  const initials = (user?.full_name || 'Storage Engineer')
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  const openConversation = useCallback(async (conversationId: number) => {
    requestedId.current = conversationId;
    setActiveId(conversationId);
    setLoadingMessages(true);
    setHistoryError(null);
    try {
      const history = await api.get<ChatMessageDto[]>(
        `/storage/chat/conversations/${conversationId}/messages`,
      );
      if (requestedId.current !== conversationId) return;
      setMessages(history.map(toMessage));
    } catch (caught) {
      // Le 401 est déjà traité globalement (redirection vers la connexion).
      if (caught instanceof ApiError && caught.status === 401) return;
      if (requestedId.current !== conversationId) return;
      setMessages([]);
      setHistoryError(errorMessage(caught, 'Something went wrong.'));
    } finally {
      if (requestedId.current === conversationId) setLoadingMessages(false);
    }
  }, []);

  // Les fils vivent côté serveur : on les recharge à chaque montage, sinon
  // changer de page suffirait à les perdre. Le plus récent s'ouvre seul, sauf
  // si la recherche globale en désigne un autre.
  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const list = await api.get<Conversation[]>('/storage/chat/conversations');
        if (cancelled) return;
        setConversations(list);

        const requested = Number(requestedConversation.current);
        const target = list.find((item) => item.id === requested) ?? list[0];
        if (target) void openConversation(target.id);

        // Le paramètre a joué son rôle : le garder ferait rouvrir ce fil au
        // moindre rechargement, même après en avoir choisi un autre.
        if (requestedConversation.current) setSearchParams({}, { replace: true });
      } catch (caught) {
        if (cancelled || (caught instanceof ApiError && caught.status === 401)) return;
        setHistoryError(errorMessage(caught, 'Something went wrong.'));
      } finally {
        if (!cancelled) setLoadingConversations(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [openConversation, setSearchParams]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  function startNewConversation() {
    // Le fil n'est créé en base qu'au premier message : une conversation vide
    // encombrerait la liste si l'utilisateur repart sans rien demander.
    requestedId.current = null;
    setActiveId(null);
    setMessages([]);
    setHistoryError(null);
    setListOpen(false);
  }

  function selectConversation(conversation: Conversation) {
    setListOpen(false);
    if (conversation.id === activeId) return;
    void openConversation(conversation.id);
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || thinking) return;

    const target = activeId;
    // Bulle optimiste : remplacée par la version enregistrée dès la réponse.
    const localId = `local-${Date.now()}`;
    setMessages((current) => [
      ...current,
      { id: localId, author: 'user', text: trimmed, at: new Date() },
    ]);
    setDraft('');
    setThinking(true);

    try {
      const turn = await api.post<ChatTurn>('/storage/chat', {
        message: trimmed,
        conversation_id: target,
      });

      // L'utilisateur a pu changer de fil pendant que l'agent réfléchissait :
      // le tour est bien enregistré, mais il n'a plus sa place à l'écran.
      const stillHere = requestedId.current === target;
      if (stillHere) {
        requestedId.current = turn.conversation.id;
        setActiveId(turn.conversation.id);
        setMessages((current) => [
          ...current.map((message) =>
            message.id === localId ? toMessage(turn.user_message) : message,
          ),
          toMessage(turn.assistant_message),
        ]);
      }

      // Le fil qui vient de servir remonte en tête, avec son titre à jour.
      setConversations((current) => [
        turn.conversation,
        ...current.filter((item) => item.id !== turn.conversation.id),
      ]);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return;
      if (requestedId.current !== target) return;
      // Le backend n'enregistre un tour que s'il a abouti : cet échange-ci
      // n'est donc pas dans le fil, et le dire évite de le chercher au retour.
      setMessages((current) => [
        ...current,
        {
          id: `${localId}-error`,
          author: 'oasis',
          at: new Date(),
          failed: true,
          text: `I couldn't reach the storage tools just now — ${errorMessage(
            caught,
            'the request failed.',
          )}\n\nThis exchange wasn't saved to your conversation.`,
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  async function confirmRename() {
    if (!renaming) return;
    const title = renameDraft.trim();
    if (!title) return;

    setBusy(true);
    try {
      const updated = await api.patch<Conversation>(
        `/storage/chat/conversations/${renaming.id}`,
        { title },
      );
      setConversations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setRenaming(null);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return;
      notify({
        tone: 'error',
        title: "Couldn't rename this conversation",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const removed = pendingDelete;

    setBusy(true);
    try {
      await api.delete(`/storage/chat/conversations/${removed.id}`);
      const remaining = conversations.filter((item) => item.id !== removed.id);
      setConversations(remaining);
      setPendingDelete(null);
      notify({ title: `${removed.title} deleted` });

      // On enchaîne sur le fil suivant plutôt que de laisser un écran vide
      // avec, dans la liste, des conversations qu'il faudrait rouvrir.
      if (removed.id === activeId) {
        if (remaining.length > 0) void openConversation(remaining[0].id);
        else startNewConversation();
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return;
      notify({
        tone: 'error',
        title: "Couldn't delete this conversation",
        detail: caught instanceof Error ? caught.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  /**
   * Remplace une proposition par son état final après le clic.
   *
   * On réécrit l'action dans le message plutôt que de recharger le fil : le
   * reste de la conversation n'a pas bougé, et un rechargement complet ferait
   * sauter la position de lecture.
   */
  function settleAction(messageId: string, updated: ActionRequest) {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId
          ? {
              ...message,
              actions: message.actions?.map((action) =>
                action.id === updated.id ? updated : action,
              ),
            }
          : message,
      ),
    );
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  const activeConversation = conversations.find((item) => item.id === activeId) ?? null;
  const showWelcome = !loadingMessages && messages.length === 0 && !thinking;

  const list = (
    <ConversationList
      conversations={conversations}
      activeId={activeId}
      loading={loadingConversations}
      onSelect={selectConversation}
      onNew={startNewConversation}
      onRename={(conversation) => {
        setRenaming(conversation);
        setRenameDraft(conversation.title);
        setListOpen(false);
      }}
      onDelete={(conversation) => {
        setPendingDelete(conversation);
        setListOpen(false);
      }}
    />
  );

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-6xl gap-4">
      <aside className="card hidden w-64 shrink-0 flex-col overflow-hidden lg:flex">{list}</aside>

      <div className="flex min-h-0 flex-1 flex-col">
        <header className="mb-4 flex items-center gap-3">
          <Logo size={18} />
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[18px] font-semibold tracking-tight text-ink-900">
              {activeConversation?.title ?? 'OASIS Assistant'}
            </h1>
            <p className="text-[13px] text-ink-500">
              {activeConversation
                ? `Last activity ${formatRelativeTime(activeConversation.updated_at)}`
                : 'Your intelligent Storage Operations assistant'}
            </p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="lg:hidden"
            icon={<MessageSquare className="h-3.5 w-3.5" />}
            onClick={() => setListOpen(true)}
          >
            Conversations
          </Button>
          <Button
            size="sm"
            className="hidden lg:inline-flex"
            icon={<Plus className="h-3.5 w-3.5" />}
            onClick={startNewConversation}
            disabled={activeId === null && messages.length === 0}
          >
            New
          </Button>
        </header>

        <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-5 py-6">
            {loadingMessages && <HistorySkeleton />}

            {historyError && !loadingMessages && (
              <div className="mx-auto mb-5 flex max-w-lg items-start gap-2 rounded-xl border border-warn-200 bg-warn-50 px-4 py-3">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-warn-600" />
                <div className="min-w-0">
                  <p className="text-[13px] text-ink-700">
                    I couldn't load your earlier messages — {historyError}
                  </p>
                  {activeId !== null && (
                    <button
                      onClick={() => void openConversation(activeId)}
                      className="mt-1 text-[12px] font-medium text-brand-600 hover:text-brand-700"
                    >
                      Try again
                    </button>
                  )}
                </div>
              </div>
            )}

            {showWelcome && !historyError && (
              <div className="mx-auto max-w-lg py-8 text-center">
                <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-500">
                  <Sparkles className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-[15px] font-semibold text-ink-900">
                  Ask me anything about your storage
                </h2>
                <p className="mt-1.5 text-[13px] leading-relaxed text-ink-500">
                  I can read your capacity, backup jobs and replication status, cross-check them
                  against your runbooks, and tell you what actually needs doing.
                </p>
              </div>
            )}

            <div className="space-y-5">
              {messages.map((message) =>
                message.author === 'user' ? (
                  <div key={message.id} className="flex items-start justify-end gap-3">
                    <div className="max-w-[75%]">
                      <p className="rounded-2xl rounded-tr-md bg-brand-500 px-4 py-2.5 text-[14px] leading-relaxed text-white">
                        {message.text}
                      </p>
                      <div className="mt-1 text-right">
                        <Timestamp at={message.at} />
                      </div>
                    </div>
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-ink-700">
                      {initials || 'SE'}
                    </span>
                  </div>
                ) : (
                  <div key={message.id} className="flex items-start gap-3">
                    <Logo variant="mark" size={32} />
                    <div className="max-w-[80%] min-w-0">
                      <div
                        className={cn(
                          'rounded-2xl rounded-tl-md border px-4 py-2.5',
                          message.failed ? 'border-warn-200 bg-warn-50' : 'border-line bg-canvas',
                        )}
                      >
                        {message.failed && <AlertCircle className="mb-1.5 h-4 w-4 text-warn-600" />}
                        <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink-900">
                          {message.text}
                        </p>
                      </div>
                      {message.actions?.map((action) => (
                        <div key={action.id} className="mt-2">
                          <ActionProposal
                            action={action}
                            onSettled={(updated) => settleAction(message.id, updated)}
                          />
                        </div>
                      ))}

                      <div className="mt-1 flex items-center gap-2">
                        <Timestamp at={message.at} />
                        {!message.failed && (
                          <Link
                            to="/storage/requests"
                            className="text-[11px] font-medium text-brand-600 hover:text-brand-700"
                          >
                            Create a request from this
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                ),
              )}

              {thinking && (
                <div className="flex items-start gap-3">
                  <Logo variant="mark" size={32} />
                  <div className="rounded-2xl rounded-tl-md border border-line bg-canvas px-4 py-2.5">
                    <TypingIndicator />
                  </div>
                </div>
              )}
            </div>

            <div ref={endRef} />
          </div>

          <div className="border-t border-line bg-white px-5 py-4">
            {showWelcome && (
              <div className="mb-3 flex flex-wrap gap-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => void send(suggestion)}
                    className="focus-ring rounded-full border border-line bg-canvas px-3 py-1.5 text-[12px] font-medium text-ink-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex items-end gap-2">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    void send(draft);
                  }
                }}
                rows={1}
                placeholder="Ask OASIS about your storage environment..."
                className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-line bg-canvas px-4 py-3 text-[14px] text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
              />
              <button
                type="submit"
                disabled={!draft.trim() || thinking}
                aria-label="Send"
                className="focus-ring flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-500 text-white transition-colors hover:bg-brand-600 disabled:bg-slate-200 disabled:text-ink-400"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      <Drawer
        open={listOpen}
        onClose={() => setListOpen(false)}
        title="Conversations"
        subtitle="Everything you've asked OASIS, kept for you."
      >
        <div className="flex h-full flex-col">{list}</div>
      </Drawer>

      <Modal
        open={renaming !== null}
        onClose={() => setRenaming(null)}
        title="Rename this conversation"
        className="max-w-md"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void confirmRename();
          }}
        >
          <div className="px-6 py-5">
            <TextField
              label="Title"
              value={renameDraft}
              maxLength={120}
              autoFocus
              onChange={(event) => setRenameDraft(event.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 border-t border-line px-6 py-4">
            <Button type="button" onClick={() => setRenaming(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={busy} disabled={!renameDraft.trim()}>
              Save
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title="Delete this conversation?"
        subtitle={`${pendingDelete?.title} and all of its messages will be deleted.`}
        className="max-w-md"
      >
        <div className="flex justify-end gap-2 px-6 py-5">
          <Button onClick={() => setPendingDelete(null)}>Keep it</Button>
          <Button variant="danger" loading={busy} onClick={() => void confirmDelete()}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
