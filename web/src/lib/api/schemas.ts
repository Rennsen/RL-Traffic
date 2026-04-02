import { z } from "zod";

export const districtSchema = z.object({
  district_id: z.string(),
  name: z.string(),
  description: z.string(),
  manager: z.object({
    owner: z.string(),
    team: z.string(),
    contact: z.string(),
  }),
  traffic_pattern: z.string(),
  default_params: z.object({
    fixed_cycle: z.number(),
    service_rate: z.number(),
    emergency_rate: z.number(),
  }),
  actual_metrics: z.record(z.number()),
  layout: z.object({
    width: z.number(),
    height: z.number(),
    roads: z.array(
      z.object({
        id: z.string(),
        from: z.array(z.number()),
        to: z.array(z.number()),
        lanes: z.number(),
      }),
    ),
    intersections: z.array(
      z.object({
        id: z.string(),
        x: z.number(),
        y: z.number(),
      }),
    ),
  }).passthrough(),
  network: z.record(z.any()).optional(),
});

export const districtsResponseSchema = z.object({
  districts: z.array(districtSchema),
});

export const runSummarySchema = z.object({
  run_id: z.string(),
  district_id: z.string(),
  district_name: z.string(),
  created_at: z.string(),
  avg_wait: z.number(),
  avg_queue: z.number(),
  throughput: z.number(),
  clearance_ratio: z.number(),
  improvements: z.record(z.number()),
  status: z.string().optional(),
});

export const runsResponseSchema = z.object({
  runs: z.array(runSummarySchema),
});

export const alertSchema = z.object({
  alert_id: z.string(),
  district_id: z.string(),
  title: z.string(),
  message: z.string(),
  severity: z.enum(["low", "medium", "high"]),
  metric: z.string(),
  value: z.number(),
  threshold: z.number(),
  created_at: z.string(),
});

export const alertsResponseSchema = z.object({
  alerts: z.array(alertSchema),
});

export const presetSchema = z.object({
  preset_id: z.string(),
  name: z.string(),
  description: z.string().nullable().optional(),
  config: z.record(z.any()),
  created_at: z.string(),
});

export const presetsResponseSchema = z.object({
  presets: z.array(presetSchema),
});

export const templateSchema = z.object({
  template_id: z.string(),
  name: z.string(),
  description: z.string(),
  config: z.record(z.any()),
});

export const templatesResponseSchema = z.object({
  templates: z.array(templateSchema),
});

export const notificationSchema = z.object({
  notification_id: z.string(),
  title: z.string(),
  message: z.string(),
  severity: z.enum(["low", "medium", "high"]),
  category: z.string(),
  district_id: z.string().nullable().optional(),
  created_at: z.string(),
});

export const notificationsResponseSchema = z.object({
  notifications: z.array(notificationSchema),
});

export const currentUserSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string(),
  roles: z.array(z.string()).optional(),
});

export const districtNoteSchema = z.object({
  id: z.string(),
  note: z.string(),
  created_at: z.string(),
  created_by: z.string().nullable().optional(),
});

export const districtNotesResponseSchema = z.object({
  notes: z.array(districtNoteSchema),
});

export const districtTargetsResponseSchema = z.object({
  district_id: z.string().optional(),
  targets: z.record(z.any()),
  updated_at: z.string().optional(),
});

export const auditEntrySchema = z.object({
  id: z.string(),
  action: z.string(),
  actor_id: z.string().nullable().optional(),
  details: z.record(z.any()).nullable().optional(),
  created_at: z.string(),
});

export const auditResponseSchema = z.object({
  entries: z.array(auditEntrySchema),
});

export const activityEventSchema = z.object({
  id: z.string(),
  event_type: z.string(),
  message: z.string(),
  actor_id: z.string().nullable().optional(),
  district_id: z.string().nullable().optional(),
  created_at: z.string(),
});

export const activityResponseSchema = z.object({
  events: z.array(activityEventSchema),
});

export const leaderboardRowSchema = z.object({
  district_id: z.string(),
  district_name: z.string(),
  avg_wait_pct: z.number().nullable().optional(),
  throughput_pct: z.number().nullable().optional(),
});

export const leaderboardResponseSchema = z.object({
  leaderboard: z.array(leaderboardRowSchema),
});

export const teamPerformanceRowSchema = z.object({
  team: z.string(),
  district: z.string(),
  owner: z.string(),
  wait_gain: z.number().nullable().optional(),
  throughput_gain: z.number().nullable().optional(),
});

export const teamPerformanceResponseSchema = z.object({
  teams: z.array(teamPerformanceRowSchema),
});

export const reportSnapshotSchema = z.object({
  period_days: z.number(),
  count: z.number(),
  avg_wait: z.number(),
  avg_queue: z.number(),
  throughput: z.number(),
  runs: z.array(runSummarySchema),
});

export const anomalySchema = z.object({
  anomaly_id: z.string(),
  district_id: z.string(),
  title: z.string(),
  message: z.string(),
  severity: z.enum(["low", "medium", "high"]),
  metric: z.string(),
  value: z.number(),
  threshold: z.number(),
  created_at: z.string(),
});

export const anomaliesResponseSchema = z.object({
  anomalies: z.array(anomalySchema),
});

export const aiRecommendationsResponseSchema = z.object({
  district_id: z.string(),
  recommendations: z.array(z.string()),
});

export const aiHistoryEntrySchema = z.object({
  id: z.string(),
  district_id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  created_at: z.string(),
});

export const aiHistoryResponseSchema = z.object({
  history: z.array(aiHistoryEntrySchema),
});

export const runResultSchema = z.object({
  run_id: z.string(),
  created_at: z.string(),
  config: z.object({
    request: z.record(z.any()),
    effective: z.record(z.any()),
  }),
  backend: z.record(z.any()).optional(),
  district: districtSchema,
  training: z.record(z.any()),
  comparison: z.object({
    rl: z.record(z.number()),
    fixed: z.record(z.number()),
    improvements: z.record(z.number()),
  }),
  benchmark: z.record(z.any()),
  time_series: z.object({
    rl: z.record(z.any()),
    fixed: z.record(z.any()),
  }),
});
