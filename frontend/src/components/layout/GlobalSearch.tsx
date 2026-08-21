import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ClipboardList,
  Database,
  FileText,
  LayoutGrid,
  Loader2,
  MessageSquare,
  Search,
  Settings,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';

type HitType = 'incident' | 'request' | 'conversation' | 'document';

type SearchHit = {
  type: HitType;
  id: string;
  title: string;
  subtitle: string | null;
  timestamp: string | null;
};

/** Le backend renvoie un type et un identifiant ; la route se décide ici. */
const DESTINATION: Record<HitType, (id: string) => string> = {
  incident: (id) => `/storage/incidents?incident=${encodeURIComponent(id)}`,
  request: (id) => `/storage/requests?request=${encodeURIComponent(id)}`,
  conversation: (id) => `/storage/chat?conversation=${encodeURIComponent(id)}`,
  document: (id) => `/storage/data-hub?document=${encodeURIComponent(id)}`,
};

const GROUP_LABEL: Record<HitType, string> = {
  incident: 'Incidents',
  request: 'Requests',
  conversation: 'Conversations',
  document: 'Documents',
};

const GROUP_ICON: Record<HitType, LucideIcon> = {
  incident: ShieldAlert,
  request: ClipboardList,
  conversation: MessageSquare,
  document: FileText,
};

type Page = {
  label: string;
  description: string;
  to: string;
  icon: LucideIcon;
  /** Les mots par lesquels on cherche la page sans en connaître le nom. */
  keywords: string[];
};

/**
 * On cherche aussi bien une page qu'une donnée : « documents » doit mener au
 * Data Hub même si aucun fichier ne porte ce mot dans son nom. Ces entrées
 * sont résolues côté client -- elles ne dépendent d'aucune donnée, une requête
 * réseau pour les retrouver serait du gaspillage.
 */
const PAGES: Page[] = [
  {
    label: 'Dashboard',
    description: 'Capacity, performance and backup health',
    to: '/storage/dashboard',
    icon: LayoutGrid,
    keywords: ['overview', 'home', 'kpi', 'capacity', 'performance', 'volumes', 'disk', 'charts'],
  },
  {
    label: 'Chat',
    description: 'Ask OASIS about your storage',
    to: '/storage/chat',
    icon: MessageSquare,
    keywords: ['assistant', 'oasis', 'ask', 'conversations', 'ai', 'llm'],
  },
  {
    label: 'Incidents',
    description: 'Open and resolved incident tickets',
    to: '/storage/incidents',
    icon: ShieldAlert,
    keywords: ['tickets', 'alerts', 'issues', 'outage', 'severity', 'critical'],
  },
  {
    label: 'Requests',
    description: 'Requests submitted to the administrator',
    to: '/storage/requests',
    icon: ClipboardList,
    keywords: ['actions', 'approval', 'restore', 'snapshot', 'pending'],
  },
  {
    label: 'Data Hub',
    description: 'Runbooks and documents OASIS reads',
    to: '/storage/data-hub',
    icon: Database,
    keywords: ['documents', 'docs', 'files', 'knowledge', 'runbooks', 'upload', 'pdf', 'rag'],
  },
  {
    label: 'Reports',
    description: 'Storage reports you can export',
    to: '/storage/reports',
    icon: FileText,
    keywords: ['report', 'export', 'pdf', 'summary'],
  },
  {
    label: 'Settings',
    description: 'Your account and preferences',
    to: '/storage/settings',
    icon: Settings,
    keywords: ['account', 'profile', 'preferences', 'password'],
  },
];

/** Une ligne du panneau, qu'elle vienne du backend ou de la liste des pages. */
type Row = {
  key: string;
  group: string;
  icon: LucideIcon;
  title: string;
  subtitle: string | null;
  timestamp: string | null;
  to: string;
};

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 250;

function matchingPages(query: string): Row[] {
  const needle = query.toLowerCase();
  return PAGES.filter(
    (page) =>
      page.label.toLowerCase().includes(needle) ||
      page.keywords.some((keyword) => keyword.includes(needle)),
  ).map((page) => ({
    key: `page:${page.to}`,
    group: 'Pages',
    icon: page.icon,
    title: page.label,
    subtitle: page.description,
    timestamp: null,
    to: page.to,
  }));
}

function toRow(hit: SearchHit): Row {
  return {
    key: `${hit.type}:${hit.id}`,
    group: GROUP_LABEL[hit.type],
    icon: GROUP_ICON[hit.type],
    title: hit.title,
    subtitle: hit.subtitle,
    timestamp: hit.timestamp,
    to: DESTINATION[hit.type](hit.id),
  };
}

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Numéro de la dernière requête envoyée : une réponse lente arrivée après
  // une frappe plus récente ne doit pas réafficher d'anciens résultats.
  const latestRequest = useRef(0);

  const trimmed = query.trim();

  useEffect(() => {
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setHits([]);
      setLoading(false);
      setError(null);
      return;
    }

    // On attend une pause dans la frappe : une requête par caractère
    // saturerait le backend pour des résultats aussitôt remplacés.
    setLoading(true);
    const ticket = ++latestRequest.current;
    const timer = setTimeout(() => {
      api
        .get<SearchHit[]>(`/storage/search?q=${encodeURIComponent(trimmed)}`)
        .then((results) => {
          if (latestRequest.current !== ticket) return;
          setHits(results);
          setError(null);
        })
        .catch((caught: unknown) => {
          if (latestRequest.current !== ticket) return;
          // Le 401 est déjà traité globalement (redirection vers la connexion).
          if (caught instanceof ApiError && caught.status === 401) return;
          setHits([]);
          setError(caught instanceof Error ? caught.message : 'Search failed.');
        })
        .finally(() => {
          if (latestRequest.current === ticket) setLoading(false);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [trimmed]);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setPanelOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Ctrl/⌘ + K amène le curseur ici depuis n'importe quelle page.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  // Les pages d'abord : elles répondent instantanément, pendant que la
  // requête réseau est encore en vol.
  const rows: Row[] = trimmed ? [...matchingPages(trimmed), ...hits.map(toRow)] : [];

  useEffect(() => {
    setActiveIndex(0);
  }, [trimmed, hits]);

  const openRow = useCallback(
    (row: Row) => {
      setPanelOpen(false);
      setQuery('');
      setHits([]);
      navigate(row.to);
    },
    [navigate],
  );

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setPanelOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!panelOpen || rows.length === 0) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % rows.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + rows.length) % rows.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const row = rows[activeIndex];
      if (row) openRow(row);
    }
  }

  const showPanel = panelOpen && trimmed.length > 0;
  // Rien trouvé, et plus rien en route : seul ce cas mérite de le dire.
  const nothingFound = rows.length === 0 && !loading && !error;

  // Les lignes arrivent déjà groupées : on n'insère un en-tête qu'au
  // changement de groupe, en gardant l'index global pour le clavier.
  let previousGroup: string | null = null;

  return (
    <div ref={containerRef} className="relative max-w-md flex-1">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
      <input
        ref={inputRef}
        type="search"
        role="combobox"
        aria-expanded={showPanel}
        aria-controls="global-search-results"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setPanelOpen(true);
        }}
        onFocus={() => setPanelOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="Search pages, incidents, requests, documents..."
        className="h-9 w-full rounded-lg border border-line bg-canvas pl-9 pr-9 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
      />
      {loading && (
        <Loader2 className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-ink-400" />
      )}

      {showPanel && (
        <div
          id="global-search-results"
          role="listbox"
          className="absolute left-0 top-full z-40 mt-1.5 w-full overflow-hidden rounded-xl border border-line bg-white shadow-lift animate-fade-up"
        >
          {error && (
            <p className="px-3 py-4 text-center text-[13px] text-warn-600">{error}</p>
          )}

          {nothingFound && (
            <p className="px-3 py-4 text-center text-[13px] text-ink-500">
              {trimmed.length < MIN_QUERY_LENGTH
                ? `Keep typing — at least ${MIN_QUERY_LENGTH} characters.`
                : `Nothing matches “${trimmed}”.`}
            </p>
          )}

          {rows.length > 0 && (
            <ul className="max-h-96 overflow-y-auto py-1">
              {rows.map((row, index) => {
                const Icon = row.icon;
                const newGroup = row.group !== previousGroup;
                previousGroup = row.group;

                return (
                  <li key={row.key}>
                    {newGroup && (
                      <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                        {row.group}
                      </p>
                    )}
                    <button
                      role="option"
                      aria-selected={index === activeIndex}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => openRow(row)}
                      className={cn(
                        'flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors',
                        index === activeIndex ? 'bg-brand-50' : 'hover:bg-slate-50',
                      )}
                    >
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-ink-400" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px] font-medium text-ink-900">
                          {row.title}
                        </span>
                        {row.subtitle && (
                          <span className="block truncate text-[11px] text-ink-500">
                            {row.subtitle}
                          </span>
                        )}
                      </span>
                      {row.timestamp && (
                        <span className="shrink-0 pt-0.5 text-[11px] text-ink-400">
                          {formatRelativeTime(row.timestamp)}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
