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
  expected_interval_hours: number | null;
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
  /** Date du dernier relevé sur la VM — la réponse peut servir un relevé récent en cache. */
  checked_at: string;
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

/**
 * Une remédiation proposée par l'agent et pas encore exécutée.
 *
 * L'agent n'exécute jamais un outil qui modifie la VM : il enregistre cette
 * intention, que l'ingénieur confirme ou rejette d'un clic. C'est le seul
 * chemin d'exécution du système.
 */
export type ActionRequest = {
  id: string;
  action_type: string;
  target: string;
  parameters: Record<string, unknown>;
  status: RequestStatus;
  incident_ticket_id: string | null;
  created_at: string;
  completed_at: string | null;
  result: Record<string, unknown> | null;
};

/** Une entrée de la piste d'audit d'un incident. */
export type IncidentNote = {
  id: string;
  content: string;
  created_at: string;
  author_name: string | null;
};

/**
 * Le ticket et tout son cycle de vie : détection, diagnostic, actions
 * proposées, confirmation, résolution. Chargé à l'ouverture du panneau ; la
 * liste des incidents, elle, se contente d'`Incident`.
 */
export type IncidentDetail = Incident & {
  mcp_data: Record<string, unknown>;
  actions: ActionRequest[];
  notes: IncidentNote[];
  investigation_conversation_id: number | null;
};

export type Investigation = {
  conversation_id: number;
  created: boolean;
  ticket: IncidentDetail;
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

// --- Demandes entre l'ingénieur Storage et l'administrateur -----------------
// À ne pas confondre avec ActionRequest ci-dessus, qui porte la confirmation
// d'une remédiation MCP et vit sur la page Incidents et dans le chat.

export type RequestDirection = 'engineer_to_admin' | 'admin_to_engineer';
export type RequestPriority = 'low' | 'medium' | 'high' | 'critical';

export type ServiceRequestStatus =
  | 'pending'
  | 'in_review'
  | 'approved'
  | 'rejected'
  | 'acknowledged'
  | 'in_progress'
  | 'completed';

export type UserBrief = {
  id: number;
  email: string;
  full_name: string | null;
  role: Role | null;
};

export type RequestAttachment = {
  id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  uploader: UserBrief | null;
  created_at: string;
};

export type ServiceRequest = {
  id: string;
  direction: RequestDirection;
  title: string;
  description: string | null;
  request_type: string | null;
  priority: RequestPriority;
  status: ServiceRequestStatus;
  creator: UserBrief | null;
  assignee: UserBrief | null;
  deadline: string | null;
  administrator_response: string | null;
  created_at: string;
  updated_at: string;
  /** Date de la décision (approuvée ou refusée) ; null tant qu'elle n'est pas prise. */
  decided_at: string | null;
  acknowledged_at: string | null;
  completed_at: string | null;
  attachment_count: number;
};

/** Une demande vue seule : elle seule détaille les fichiers joints. */
export type ServiceRequestDetail = ServiceRequest & {
  attachments: RequestAttachment[];
};
