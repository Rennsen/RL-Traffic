export interface DistrictManager {
  owner: string;
  team: string;
  contact: string;
}

export interface District {
  district_id: string;
  name: string;
  description: string;
  manager: DistrictManager;
  traffic_pattern: string;
  default_params: {
    fixed_cycle: number;
    service_rate: number;
    emergency_rate: number;
  };
  actual_metrics: Record<string, number>;
  layout: {
    width: number;
    height: number;
    roads: Array<{ id: string; from: number[]; to: number[]; lanes: number }>;
    intersections: Array<{ id: string; x: number; y: number }>;
    [key: string]: unknown;
  };
  network?: Record<string, unknown>;
}

export interface RunSummary {
  run_id: string;
  district_id: string;
  district_name: string;
  created_at: string;
  avg_wait: number;
  avg_queue: number;
  throughput: number;
  clearance_ratio: number;
  improvements: Record<string, number>;
  status?: string;
}

export interface Preset {
  preset_id: string;
  name: string;
  description?: string | null;
  config: Record<string, unknown>;
  created_at: string;
}

export interface Alert {
  alert_id: string;
  district_id: string;
  title: string;
  message: string;
  severity: "low" | "medium" | "high";
  metric: string;
  value: number;
  threshold: number;
  created_at: string;
}

export interface Notification {
  notification_id: string;
  title: string;
  message: string;
  severity: "low" | "medium" | "high";
  category: string;
  district_id?: string | null;
  created_at: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  roles?: string[];
}

export interface DistrictNote {
  id: string;
  note: string;
  created_at: string;
  created_by?: string | null;
}

export interface DistrictTargets {
  district_id?: string;
  targets: Record<string, unknown>;
  updated_at?: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  actor_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface ActivityEvent {
  id: string;
  event_type: string;
  message: string;
  actor_id?: string | null;
  district_id?: string | null;
  created_at: string;
}

export interface LeaderboardRow {
  district_id: string;
  district_name: string;
  avg_wait_pct?: number | null;
  throughput_pct?: number | null;
}

export interface TeamPerformanceRow {
  team: string;
  district: string;
  owner: string;
  wait_gain?: number | null;
  throughput_gain?: number | null;
}

export interface ReportSnapshot {
  period_days: number;
  count: number;
  avg_wait: number;
  avg_queue: number;
  throughput: number;
  runs: RunSummary[];
}

export interface Anomaly {
  anomaly_id: string;
  district_id: string;
  title: string;
  message: string;
  severity: "low" | "medium" | "high";
  metric: string;
  value: number;
  threshold: number;
  created_at: string;
}

export interface AIRecommendations {
  district_id: string;
  recommendations: string[];
}

export interface AIHistoryEntry {
  id: string;
  district_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ScenarioTemplate {
  template_id: string;
  name: string;
  description: string;
  config: Record<string, unknown>;
}

export interface RunResult {
  run_id: string;
  created_at: string;
  config: {
    request: Record<string, unknown>;
    effective: Record<string, unknown>;
  };
  backend?: {
    requested_backend?: string;
    active_backend?: string;
    available?: boolean;
    message?: string;
    sumo_status?: Record<string, unknown>;
    preview?: {
      nodes_xml?: string;
      edges_xml?: string;
      routes_xml?: string;
      connections_xml?: string;
      [key: string]: unknown;
    };
    artifacts?: {
      node_count?: number;
      edge_count?: number;
      route_count?: number;
      traffic_light_count?: number;
      connection_count?: number;
      output_directory?: string;
      output_directory_relative?: string;
      generated_files?: Record<string, string>;
      public_files?: Record<string, string>;
      [key: string]: unknown;
    };
    visualization?: {
      nodes?: Array<{ id: string; x: number; y: number; type?: string }>;
      edges?: Array<{
        id: string;
        from: string;
        to: string;
        lanes?: number;
        speed?: number;
        length?: number;
        x1: number;
        y1: number;
        x2: number;
        y2: number;
      }>;
      flows?: Array<{ id: string; from: string; to: string; probability?: number }>;
    };
    runtime?: {
      executed?: boolean;
      reason?: string;
      missing_requirements?: string[];
      error?: string;
      metrics?: Record<string, number>;
      time_series?: { queue?: number[]; throughput?: number[] };
      trace?: {
        frames?: Array<{
          step?: number;
          sim_time?: number;
          vehicle_count?: number;
          truncated?: boolean;
          vehicles?: Array<{ id: string; x: number; y: number; speed?: number; angle?: number }>;
        }>;
        sample_period?: number;
        vehicle_limit?: number;
      };
    };
    gui?: {
      executed?: boolean;
      reason?: string;
      snapshot_dir?: string;
      frame_count?: number;
      stderr?: string;
      stdout?: string;
    };
    [key: string]: unknown;
  };
  district: District;
  training: Record<string, unknown>;
  comparison: {
    rl: Record<string, number>;
    fixed: Record<string, number>;
    improvements: Record<string, number>;
  };
  benchmark: Record<string, unknown>;
  time_series: {
    rl: Record<string, any>;
    fixed: Record<string, any>;
  };
}
