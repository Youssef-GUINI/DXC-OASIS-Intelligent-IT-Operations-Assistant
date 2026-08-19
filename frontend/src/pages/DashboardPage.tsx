import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowUp,
  Bot,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  MemoryStick,
  Network,
  Settings2,
  Sparkles,
  TerminalSquare,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '@/lib/api';
import { Badge, StatusDot } from '@/components/ui/Badge';
import { MarkdownMessage } from '@/components/ui/MarkdownMessage';
import { cn } from '@/lib/cn';
import { formatRelativeTime, greeting } from '@/lib/format';
import { useResource } from '@/lib/useResource';
import type { LinuxIncidentApi, LinuxKPIs } from '@/lib/types';

type TrendRange = 'Daily' | 'Weekly' | 'Monthly';
type TrendMetric = 'checks' | 'success';

const trendByRange: Record<TrendRange, { day: string; checks: number; success: number }[]> = {
  Daily: [
    { day: '08:00', checks: 120, success: 82 },
    { day: '10:00', checks: 180, success: 86 },
    { day: '12:00', checks: 340, success: 89 },
    { day: '14:00', checks: 280, success: 87 },
    { day: '16:00', checks: 410, success: 92 },
    { day: '18:00', checks: 360, success: 90 },
  ],
  Weekly: [
  { day: 'Mon', checks: 420, success: 84 },
  { day: 'Tue', checks: 520, success: 89 },
  { day: 'Wed', checks: 760, success: 86 },
  { day: 'Thu', checks: 1180, success: 93 },
  { day: 'Fri', checks: 920, success: 90 },
  { day: 'Sat', checks: 820, success: 87 },
  { day: 'Sun', checks: 1120, success: 94 },
  ],
  Monthly: [
    { day: 'W1', checks: 2100, success: 87 },
    { day: 'W2', checks: 2650, success: 91 },
    { day: 'W3', checks: 2480, success: 88 },
    { day: 'W4', checks: 3120, success: 95 },
  ],
};

const ranges: TrendRange[] = ['Daily', 'Weekly', 'Monthly'];

const fallbackChecksByArea = [
  { name: 'CPU', value: 35, color: '#3b66ef' },
  { name: 'Memory', value: 25, color: '#10b981' },
  { name: 'Disk', value: 20, color: '#8b5cf6' },
  { name: 'Network', value: 12, color: '#f59e0b' },
  { name: 'Services', value: 8, color: '#94a3b8' },
];

const fallbackActivities = [
  { icon: Cpu, title: 'CPU Analysis Persona', detail: 'Detected app-server-01 high load', status: 'Completed', time: '2 min ago', tone: 'brand' },
  { icon: MemoryStick, title: 'Memory Check', detail: 'Validated RAM pressure on db-node-02', status: 'Completed', time: '10 min ago', tone: 'ok' },
  { icon: HardDrive, title: 'Disk Troubleshooting', detail: 'Analyzing /var/log growth', status: 'In Progress', time: '18 min ago', tone: 'warn' },
  { icon: Network, title: 'Network Diagnostic', detail: 'SSH latency returned to normal', status: 'Completed', time: '35 min ago', tone: 'ok' },
] as const;

type KpiItem = {
  label: string;
  value: string;
  delta: string;
  caption: string;
  icon: typeof TerminalSquare;
  tone: 'brand' | 'ok' | 'warn';
  spark: number[];
};

type ActivityItem = {
  icon: typeof Cpu;
  title: string;
  detail: string;
  status: string;
  time: string;
  tone: 'brand' | 'ok' | 'warn';
};

const fallbackKpis: KpiItem[] = [
  { label: 'Linux Checks', value: '24', delta: '+12.5%', caption: 'vs last 7 days', icon: TerminalSquare, tone: 'brand', spark: [12, 13, 12, 15, 18, 16, 19] },
  { label: 'Tasks Completed', value: '1,429', delta: '+18.3%', caption: 'vs last 7 days', icon: CheckCircle2, tone: 'ok', spark: [40, 45, 42, 52, 57, 61, 59] },
  { label: 'Success Rate', value: '96.7%', delta: '+2.4%', caption: 'vs last 7 days', icon: Sparkles, tone: 'brand', spark: [91, 93, 92, 95, 96, 94, 97] },
  { label: 'Time Saved', value: '320h', delta: '+22.1%', caption: 'vs last 7 days', icon: Activity, tone: 'warn', spark: [18, 21, 24, 22, 28, 31, 34] },
] as KpiItem[];

function MiniSparkline({ values, tone }: { values: number[]; tone: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 90;
      const y = 28 - ((value - min) / span) * 22;
      return `${x},${y}`;
    })
    .join(' ');
  const stroke = tone === 'ok' ? '#10b981' : tone === 'warn' ? '#f59e0b' : '#3b66ef';

  return (
    <svg viewBox="0 0 92 32" className="h-8 w-24" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function KpiTile({ item }: { item: KpiItem }) {
  const Icon = item.icon;
  const toneClass = {
    brand: 'bg-brand-50 text-brand-500',
    ok: 'bg-ok-50 text-ok-600',
    warn: 'bg-warn-50 text-warn-600',
  }[item.tone];

  return (
    <article className="rounded-xl border border-line bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className={cn('inline-flex h-8 w-8 items-center justify-center rounded-lg', toneClass)}>
            <Icon className="h-4 w-4" />
          </span>
          <p className="mt-3 text-[13px] font-medium text-ink-500">{item.label}</p>
          <p className="mt-2 text-[28px] font-semibold leading-none tracking-tight text-ink-900">{item.value}</p>
          <p className="mt-3 text-[12px] text-ink-500">
            <span className="font-semibold text-ok-600">{item.delta}</span> {item.caption}
          </p>
        </div>
        <MiniSparkline values={item.spark} tone={item.tone} />
      </div>
    </article>
  );
}

function AssistantPanel() {
  const [draft, setDraft] = useState('');
  const [answer, setAnswer] = useState('Hi Linux Engineer. How can I help you troubleshoot today?');
  const [loading, setLoading] = useState(false);

  async function askAssistant(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;
    setDraft('');
    setLoading(true);
    try {
      const response = await api.post<{ response: string }>('/linux/chat', { message: trimmed });
      setAnswer(response.response);
    } catch (error) {
      setAnswer(error instanceof Error ? error.message : 'Unable to reach the Linux persona.');
    } finally {
      setLoading(false);
    }
  }

  function ask(event: FormEvent) {
    event.preventDefault();
    void askAssistant(draft);
  }

  const quickActions = [
    ['Performance Insights', 'Get CPU/RAM guidance', 'Analyse les performances Linux actuelles et donne les actions recommandees.'],
    ['Optimize Workflows', 'Improve incident response', 'Propose un workflow simple pour traiter les incidents Linux ouverts.'],
    ['Create Linux Check', 'Ask the Linux persona', 'Quels checks Linux dois-je lancer maintenant pour CPU, RAM, disque et services ?'],
    ['View Recommendations', 'See smart suggestions', 'Donne-moi les recommandations prioritaires pour stabiliser le serveur Linux.'],
  ];

  return (
    <aside className="flex max-h-none flex-col rounded-2xl border border-line bg-white p-5 shadow-card xl:sticky xl:top-20 xl:max-h-[calc(100vh-6rem)]">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-[15px] font-semibold text-ink-900">
          <Sparkles className="h-4 w-4 text-brand-500" />
          AI Agent Assistant
        </h2>
        <button
          onClick={() => void askAssistant('Donne-moi un resume rapide des actions prioritaires du dashboard Linux.')}
          disabled={loading}
          aria-label="Ask dashboard summary"
          className="rounded-lg p-1.5 text-ink-400 hover:bg-slate-100 disabled:opacity-50"
        >
          <Settings2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 rounded-xl bg-brand-50 p-4">
        <p className="text-[13px] font-medium text-ink-900">Hi Linux Engineer. I am your AI assistant.</p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-500">
          Ask here directly from the dashboard.
        </p>
      </div>

      <div className="mt-4 min-h-[260px] overflow-y-auto rounded-xl border border-brand-100 bg-canvas p-4 xl:flex-1">
        {loading ? (
          <p className="text-[12px] leading-relaxed text-ink-600">OASIS is thinking...</p>
        ) : (
          <MarkdownMessage content={answer} className="text-[12px]" />
        )}
      </div>

      <form onSubmit={ask} className="flex items-center gap-2 pt-3">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask me anything..."
          className="h-10 min-w-0 flex-1 rounded-lg border border-line bg-canvas px-3 text-[13px] text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
        <button
          type="submit"
          disabled={!draft.trim() || loading}
          aria-label="Send"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-500 text-white transition-colors hover:bg-brand-600 disabled:bg-slate-200"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-4 space-y-2.5">
        {quickActions.map(([title, detail, prompt], index) => (
          <button
            key={title}
            onClick={() => void askAssistant(prompt)}
            disabled={loading}
            className="flex w-full items-center gap-3 rounded-xl border border-line bg-white px-3 py-3 text-left transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-canvas text-brand-500">
              {index === 0 ? <Activity className="h-4 w-4" /> : index === 1 ? <GitIcon /> : index === 2 ? <Bot className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            </span>
            <span>
              <span className="block text-[13px] font-semibold text-ink-900">{title}</span>
              <span className="block text-[12px] text-ink-500">{detail}</span>
            </span>
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-xl bg-ok-50 p-4">
        <p className="text-[13px] font-semibold text-ink-900">Smart Insight</p>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-600">
          The dashboard uses backend incidents, KPIs and AI chat routes.
        </p>
      </div>
    </aside>
  );
}

function GitIcon() {
  return <Database className="h-4 w-4" />;
}

const palette = ['#3b66ef', '#10b981', '#8b5cf6', '#f59e0b', '#94a3b8'];

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

function percent(part: number, total: number) {
  if (total <= 0) return 0;
  return Math.round((part / total) * 100);
}

function buildKpis(kpis?: LinuxKPIs): KpiItem[] {
  if (!kpis) return fallbackKpis;
  const successRate = percent(kpis.resolved_incidents, kpis.total_incidents);
  const avg = kpis.avg_resolution_minutes;

  return [
    {
      label: 'Total Incidents',
      value: formatNumber(kpis.total_incidents),
      delta: `${formatNumber(kpis.open_incidents)}`,
      caption: 'open now',
      icon: TerminalSquare,
      tone: 'brand',
      spark: [12, 13, 12, 15, 18, 16, Math.max(1, kpis.total_incidents)],
    },
    {
      label: 'Resolved Incidents',
      value: formatNumber(kpis.resolved_incidents),
      delta: `${successRate}%`,
      caption: 'resolution rate',
      icon: CheckCircle2,
      tone: 'ok',
      spark: [40, 45, 42, 52, 57, 61, Math.max(1, kpis.resolved_incidents)],
    },
    {
      label: 'Success Rate',
      value: `${successRate}%`,
      delta: '+2.4%',
      caption: 'from Linux history',
      icon: Sparkles,
      tone: 'brand',
      spark: [80, 83, 86, 88, 90, 92, Math.max(1, successRate)],
    },
    {
      label: 'Avg Resolution',
      value: avg === null ? 'N/A' : `${Math.round(avg)}m`,
      delta: avg === null ? '0m' : `${Math.round(avg)}m`,
      caption: 'mean time',
      icon: Activity,
      tone: 'warn',
      spark: [18, 21, 24, 22, 28, 31, Math.max(1, Math.round(avg ?? 0))],
    },
  ];
}

function buildChecksByArea(kpis?: LinuxKPIs) {
  const entries = Object.entries(kpis?.incidents_by_category ?? {});
  if (entries.length === 0) return fallbackChecksByArea;
  const total = entries.reduce((sum, [, value]) => sum + value, 0);
  return entries.map(([name, value], index) => ({
    name,
    value: percent(value, total),
    color: palette[index % palette.length],
  }));
}

function iconForIncident(incident: LinuxIncidentApi) {
  const category = (incident.category ?? '').toLowerCase();
  if (category.includes('memory') || category.includes('ram')) return MemoryStick;
  if (category.includes('disk') || category.includes('filesystem')) return HardDrive;
  if (category.includes('network') || category.includes('ssh')) return Network;
  return Cpu;
}

function buildActivities(incidents?: LinuxIncidentApi[]): ActivityItem[] {
  if (!incidents || incidents.length === 0) return [...fallbackActivities];
  return incidents.slice(0, 4).map((incident) => ({
    icon: iconForIncident(incident),
    title: incident.category ? `${incident.category} incident` : `Incident INC-${incident.id}`,
    detail: incident.user_message || incident.response,
    status: incident.status === 'resolved' ? 'Completed' : incident.status.replace('_', ' '),
    time: formatRelativeTime(incident.created_at),
    tone: incident.status === 'resolved' ? 'ok' : incident.severity === 'high' || incident.severity === 'critical' ? 'warn' : 'brand',
  }));
}

export default function DashboardPage() {
  const [range, setRange] = useState<TrendRange>('Weekly');
  const [visibleMetrics, setVisibleMetrics] = useState<Record<TrendMetric, boolean>>({
    checks: true,
    success: true,
  });
  const [selectedArea, setSelectedArea] = useState<string | null>(null);
  const { data: kpiData } = useResource<LinuxKPIs>(() => api.get<LinuxKPIs>('/linux/dashboard/kpis'), []);
  const { data: incidentData } = useResource<LinuxIncidentApi[]>(() => api.get<LinuxIncidentApi[]>('/linux/incidents'), []);
  const kpiItems = buildKpis(kpiData);
  const checksByArea = buildChecksByArea(kpiData);
  const activities = buildActivities(incidentData);
  const totalForDonut = kpiData ? kpiData.total_incidents : 1429;
  const trend = trendByRange[range];
  const activeArea = selectedArea
    ? checksByArea.find((area) => area.name === selectedArea)
    : null;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="min-w-0">
        <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold tracking-tight text-ink-900">
              {greeting()}, Linux Engineer
            </h1>
            <p className="mt-1 text-sm text-ink-500">
              Here is what is happening with your Linux persona today.
            </p>
          </div>
          <Link to="/linux/reports" className="rounded-lg border border-line bg-white px-3 py-2 text-[12px] font-semibold text-ink-600 shadow-sm hover:bg-slate-50">
            Aug 19 - Aug 25, 2026
          </Link>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          {kpiItems.map((item) => (
            <KpiTile key={item.label} item={item} />
          ))}
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.8fr)]">
          <section className="rounded-xl border border-line bg-white p-5 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-[15px] font-semibold text-ink-900">Performance Overview</h2>
                <div className="mt-3 flex flex-wrap gap-4 text-[12px] text-ink-500">
                  <span className="flex items-center gap-1.5"><StatusDot tone="brand" /> Checks Completed</span>
                  <span className="flex items-center gap-1.5"><StatusDot tone="ok" /> Success Rate (%)</span>
                </div>
              </div>
              <div className="inline-flex rounded-lg border border-line bg-canvas p-0.5">
                {ranges.map((option) => (
                  <button
                    key={option}
                    onClick={() => setRange(option)}
                    className={cn(
                      'rounded-[6px] px-2.5 py-1 text-[12px] font-medium transition-colors',
                      range === option ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-900',
                    )}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {(['checks', 'success'] as TrendMetric[]).map((metric) => (
                <button
                  key={metric}
                  onClick={() =>
                    setVisibleMetrics((current) => ({
                      ...current,
                      [metric]: !current[metric],
                    }))
                  }
                  className={cn(
                    'rounded-full border px-3 py-1 text-[12px] font-medium capitalize transition-colors',
                    visibleMetrics[metric]
                      ? 'border-brand-200 bg-brand-50 text-brand-700'
                      : 'border-line bg-white text-ink-400',
                  )}
                >
                  {metric === 'checks' ? 'Checks Completed' : 'Success Rate'}
                </button>
              ))}
            </div>
            <div className="mt-5">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={trend} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="checksFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b66ef" stopOpacity={0.16} />
                      <stop offset="100%" stopColor="#3b66ef" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="successFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.12} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f8" vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={42} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: '1px solid #e6ebf4',
                      boxShadow: '0 12px 32px rgba(15,23,42,0.08)',
                      fontSize: 12,
                    }}
                  />
                  {visibleMetrics.checks && (
                    <Area type="monotone" dataKey="checks" stroke="#3b66ef" strokeWidth={2.5} fill="url(#checksFill)" activeDot={{ r: 4 }} />
                  )}
                  {visibleMetrics.success && (
                    <Area type="monotone" dataKey="success" stroke="#10b981" strokeWidth={2.5} fill="url(#successFill)" activeDot={{ r: 4 }} />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="rounded-xl border border-line bg-white p-5 shadow-card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-[15px] font-semibold text-ink-900">Checks by Area</h2>
                <p className="mt-1 text-[12px] text-ink-500">
                  {activeArea ? `${activeArea.name}: ${activeArea.value}% selected` : 'Click an area to focus it'}
                </p>
              </div>
              {activeArea && (
                <button
                  onClick={() => setSelectedArea(null)}
                  className="text-[12px] font-medium text-brand-600 hover:text-brand-700"
                >
                  Reset
                </button>
              )}
            </div>
            <div className="mt-4 grid items-center gap-4 sm:grid-cols-[180px_1fr] xl:grid-cols-1 2xl:grid-cols-[180px_1fr]">
              <div className="relative h-[190px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={checksByArea}
                      dataKey="value"
                      innerRadius={56}
                      outerRadius={82}
                      paddingAngle={3}
                      onClick={(entry) => setSelectedArea(entry.name)}
                    >
                      {checksByArea.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={entry.color}
                          opacity={!activeArea || activeArea.name === entry.name ? 1 : 0.32}
                          stroke={activeArea?.name === entry.name ? '#0f172a' : '#ffffff'}
                          strokeWidth={activeArea?.name === entry.name ? 2 : 1}
                          className="cursor-pointer"
                        />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-[24px] font-semibold leading-none text-ink-900">{formatNumber(totalForDonut)}</span>
                  <span className="mt-1 text-[11px] text-ink-400">Total</span>
                </div>
              </div>
              <ul className="space-y-3">
                {checksByArea.map((item) => (
                  <li key={item.name}>
                    <button
                      onClick={() => setSelectedArea(item.name)}
                      className={cn(
                        'flex w-full items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-[13px] transition-colors',
                        activeArea?.name === item.name ? 'bg-brand-50 text-brand-700' : 'text-ink-600 hover:bg-slate-50',
                      )}
                    >
                    <span className="flex items-center gap-2 text-ink-600">
                      <span className="h-2 w-2 rounded-full" style={{ background: item.color }} />
                      {item.name}
                    </span>
                    <span className="font-semibold text-ink-900">{item.value}%</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>

        <section className="mt-5 rounded-xl border border-line bg-white p-5 shadow-card">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-semibold text-ink-900">Recent Agent Activity</h2>
            <Link to="/linux/incidents" className="text-[13px] font-medium text-brand-600 hover:text-brand-700">View all</Link>
          </div>
          <ul className="mt-4 divide-y divide-line">
            {activities.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title} className="flex items-center gap-4 py-3">
                  <span
                    className={cn(
                      'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                      item.tone === 'ok' && 'bg-ok-50 text-ok-600',
                      item.tone === 'warn' && 'bg-warn-50 text-warn-600',
                      item.tone === 'brand' && 'bg-brand-50 text-brand-600',
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-semibold text-ink-900">{item.title}</span>
                    <span className="block truncate text-[12px] text-ink-500">{item.detail}</span>
                  </span>
                  <Badge tone={item.status === 'Completed' ? 'ok' : 'brand'}>{item.status}</Badge>
                  <span className="hidden w-20 text-right text-[12px] text-ink-400 sm:block">{item.time}</span>
                </li>
              );
            })}
          </ul>
        </section>
      </section>

      <AssistantPanel />
    </div>
  );
}
