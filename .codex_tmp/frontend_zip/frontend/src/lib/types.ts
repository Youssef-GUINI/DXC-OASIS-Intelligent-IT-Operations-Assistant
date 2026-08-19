export type Role = 'storage_engineer' | 'linux_engineer' | 'administrator';

export type CurrentUser = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
};

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown';

export type Volume = {
  volume_id: string | null;
  mountpoint: string | null;
  device: string | null;
  filesystem: string | null;
  total_gb: number;
  used_gb: number;
  available_gb: number;
  percent_used: number;
  status: HealthStatus;
};

export type Capacity = {
  total_gb: number;
  used_gb: number;
  available_gb: number;
  reserved_gb: number;
  percent_used: number;
  volumes: Volume[];
  volumes_near_limit: number;
  unavailable: boolean;
  error: string | null;
};

export type BackupJob = {
  job_id: string | null;
  target: string | null;
  status: string;
  last_run: string | null;
  hours_since_last_success: number;
};

export type Backups = {
  successful: number;
  failed: number;
  running: number;
  scheduled: number;
  total: number;
  jobs: BackupJob[];
  /** false : aucun timer de sauvegarde n'existe encore sur la VM. */
  configured: boolean;
  /** Renseigné seulement si la VM n'a pas pu être interrogée. */
  error: string | null;
};

export type IncidentCounts = {
  open: number;
  by_severity: Record<Severity, number>;
  needs_attention: number;
  resolved_last_7d: number;
};

export type Alert = {
  type: string;
  severity: string;
  message: string;
  target: string | null;
};

export type Overview = {
  overall_status: HealthStatus;
  headline: string;
  /** null quand la VM est injoignable : rien n'a pu être mesuré. */
  health_score: number | null;
  capacity: Capacity;
  backups: Backups;
  incidents: IncidentCounts;
  alerts: Alert[];
  generated_at: string;
};

export type PerformanceRange = '24h' | '7d' | '30d';

export type PerformancePoint = {
  timestamp: string;
  iops: number;
  throughput_mbps: number;
  latency_ms: number;
};

export type Performance = {
  range: PerformanceRange;
  points: PerformancePoint[];
  iops_avg: number;
  throughput_avg_mbps: number;
  latency_avg_ms: number;
  iops_trend_percent: number;
  /** true : le collecteur n'a pas encore de mesure sur cette plage. */
  collecting: boolean;
};

export type ActivityItem = {
  id: string;
  kind: 'incident' | 'action';
  title: string;
  resource: string | null;
  status: string;
  severity: Severity | null;
  timestamp: string;
};

export type Insight = {
  id: string;
  priority: Severity | 'info';
  title: string;
  detail: string;
  action_label: string | null;
  action_target: string | null;
};

export type Incident = {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  affected_system: string;
  root_cause: string | null;
  impact_summary: string | null;
  recommendations: { order?: number; description?: string; [key: string]: unknown }[];
  created_at: string;
  resolved_at: string | null;
};

export type RequestStatus = 'pending' | 'confirmed' | 'completed' | 'failed' | 'rejected';

export type StorageRequest = {
  id: string;
  action_type: string;
  target: string;
  parameters: {
    priority?: string;
    description?: string;
    justification?: string;
    [key: string]: unknown;
  };
  status: RequestStatus;
  incident_ticket_id: string | null;
  created_at: string;
  completed_at: string | null;
  result: Record<string, unknown> | null;
};

export type DocumentStatus = 'pending' | 'indexed' | 'failed';

export type KnowledgeDocument = {
  id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  collection: string;
  chunk_count: number;
  status: DocumentStatus;
  error: string | null;
  created_at: string;
  indexed_at: string | null;
};
