import { useEffect, useRef, useState, type FormEvent } from 'react';
import { AlertCircle, ArrowUp, Sparkles } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { MarkdownMessage } from '@/components/ui/MarkdownMessage';
import { api, ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAuth } from '@/auth/AuthContext';

type Message = {
  id: number;
  author: 'user' | 'oasis';
  text: string;
  at: Date;
  failed?: boolean;
};

const SUGGESTIONS = [
  'Mon CPU est bloque a 100%, que faire ?',
  'Comment verifier la RAM sur Linux ?',
  'Quel diagnostic faire si /var est plein ?',
  'Comment analyser un service systemd qui tombe ?',
  'Quels checks reseau lancer en premier ?',
];

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

export default function ChatPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [thinking, setThinking] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const initials = (user?.full_name || 'Linux Engineer')
    .split(' ')
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || thinking) return;

    setMessages((current) => [
      ...current,
      { id: Date.now(), author: 'user', text: trimmed, at: new Date() },
    ]);
    setDraft('');
    setThinking(true);

    try {
      const { response } = await api.post<{ response: string }>('/linux/chat', {
        message: trimmed,
      });
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, author: 'oasis', text: response, at: new Date() },
      ]);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return;
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          author: 'oasis',
          at: new Date(),
          failed: true,
          text:
            caught instanceof Error
              ? `I could not reach the Linux persona just now: ${caught.message}`
              : 'I could not reach the Linux persona just now.',
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col">
      <header className="mb-4 flex items-center gap-3">
        <Logo size={34} />
        <div className="min-w-0">
          <h1 className="text-[18px] font-semibold tracking-tight text-ink-900">OASIS Linux Assistant</h1>
          <p className="text-[13px] text-ink-500">
            Your Linux troubleshooting persona powered by Groq and RAG
          </p>
        </div>
      </header>

      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto px-5 py-6">
          {messages.length === 0 && !thinking && (
            <div className="mx-auto max-w-lg py-8 text-center">
              <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-500">
                <Sparkles className="h-5 w-5" />
              </span>
              <h2 className="mt-4 text-[15px] font-semibold text-ink-900">
                Ask me anything about Linux incidents
              </h2>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-500">
                I can help with CPU, RAM, disk, services and network diagnostics, and use the Linux knowledge base when it has a relevant procedure.
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
                    {initials || 'LE'}
                  </span>
                </div>
              ) : (
                <div key={message.id} className="flex items-start gap-3">
                  <Logo size={32} />
                  <div className="max-w-[80%] min-w-0">
                    <div
                      className={cn(
                        'rounded-2xl rounded-tl-md border px-4 py-2.5',
                        message.failed ? 'border-warn-200 bg-warn-50' : 'border-line bg-canvas',
                      )}
                    >
                      {message.failed && <AlertCircle className="mb-1.5 h-4 w-4 text-warn-600" />}
                      <MarkdownMessage content={message.text} className="text-[14px] text-ink-900" />
                    </div>
                    <div className="mt-1">
                      <Timestamp at={message.at} />
                    </div>
                  </div>
                </div>
              ),
            )}

            {thinking && (
              <div className="flex items-start gap-3">
                <Logo size={32} />
                <div className="rounded-2xl rounded-tl-md border border-line bg-canvas px-4 py-2.5">
                  <TypingIndicator />
                </div>
              </div>
            )}
          </div>

          <div ref={endRef} />
        </div>

        <div className="border-t border-line bg-white px-5 py-4">
          {messages.length === 0 && (
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
              placeholder="Ask OASIS about Linux troubleshooting..."
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
  );
}
