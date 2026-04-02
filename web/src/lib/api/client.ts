import {
  activityResponseSchema,
  alertsResponseSchema,
  anomaliesResponseSchema,
  aiHistoryResponseSchema,
  aiRecommendationsResponseSchema,
  auditResponseSchema,
  currentUserSchema,
  districtNotesResponseSchema,
  districtTargetsResponseSchema,
  districtsResponseSchema,
  leaderboardResponseSchema,
  notificationsResponseSchema,
  presetsResponseSchema,
  reportSnapshotSchema,
  runResultSchema,
  runsResponseSchema,
  teamPerformanceResponseSchema,
  templatesResponseSchema,
} from "@/lib/api/schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function withApiBase(url: string) {
  if (!url) {
    return url;
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPut<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getDistricts() {
  const data = await apiGet("/api/districts");
  return districtsResponseSchema.parse(data);
}

export async function getRuns(params?: { district_id?: string; limit?: number; status?: string }) {
  const search = new URLSearchParams();
  if (params?.district_id) {
    search.set("district_id", params.district_id);
  }
  if (params?.limit) {
    search.set("limit", String(params.limit));
  }
  if (params?.status) {
    search.set("status", params.status);
  }
  const query = search.toString();
  const data = await apiGet(`/api/runs${query ? `?${query}` : ""}`);
  return runsResponseSchema.parse(data);
}

export async function getRun(runId: string) {
  const data = await apiGet(`/api/runs/${runId}`);
  return runResultSchema.parse(data);
}

export async function getAlerts() {
  const data = await apiGet("/api/alerts");
  return alertsResponseSchema.parse(data);
}

export async function getNotifications() {
  const data = await apiGet("/api/notifications");
  return notificationsResponseSchema.parse(data);
}

export async function getTemplates() {
  const data = await apiGet("/api/templates");
  return templatesResponseSchema.parse(data);
}

export async function getPresets() {
  const data = await apiGet("/api/presets");
  return presetsResponseSchema.parse(data);
}

export async function createPreset(payload: unknown) {
  return apiPost("/api/presets", payload);
}

export async function deletePreset(presetId: string) {
  return apiDelete(`/api/presets/${presetId}`);
}

export async function runSimulation(payload: unknown) {
  const data = await apiPost("/api/run", payload);
  return runResultSchema.parse(data);
}

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!response.ok) {
    return null;
  }
  const data = await response.json();
  return currentUserSchema.parse(data);
}

export async function updateDistrictSettings(districtId: string, payload: unknown) {
  return apiPatch(`/api/districts/${districtId}/settings`, payload);
}

export async function getDistrictNotes(districtId: string) {
  const data = await apiGet(`/api/districts/${districtId}/notes`);
  return districtNotesResponseSchema.parse(data);
}

export async function addDistrictNote(districtId: string, payload: { note: string }) {
  return apiPost(`/api/districts/${districtId}/notes`, payload);
}

export async function getDistrictTargets(districtId: string) {
  const data = await apiGet(`/api/districts/${districtId}/targets`);
  return districtTargetsResponseSchema.parse(data);
}

export async function updateDistrictTargets(districtId: string, payload: { targets: any }) {
  return apiPut(`/api/districts/${districtId}/targets`, payload);
}

export async function approveRun(runId: string) {
  return apiPost(`/api/runs/${runId}/approve`, {});
}

export async function rejectRun(runId: string) {
  return apiPost(`/api/runs/${runId}/reject`, {});
}

export async function getActivity() {
  const data = await apiGet(`/api/activity`);
  return activityResponseSchema.parse(data);
}

export async function getAudit() {
  const data = await apiGet(`/api/audit`);
  return auditResponseSchema.parse(data);
}

export async function getLeaderboard() {
  const data = await apiGet(`/api/leaderboard`);
  return leaderboardResponseSchema.parse(data);
}

export async function getTeamPerformance() {
  const data = await apiGet(`/api/teams/performance`);
  return teamPerformanceResponseSchema.parse(data);
}

export async function getWeeklyReport() {
  const data = await apiGet(`/api/reports/weekly`);
  return reportSnapshotSchema.parse(data);
}

export async function getMonthlyReport() {
  const data = await apiGet(`/api/reports/monthly`);
  return reportSnapshotSchema.parse(data);
}

export async function getAnomalies() {
  const data = await apiGet(`/api/anomalies`);
  return anomaliesResponseSchema.parse(data);
}

export async function getAIRecommendations(districtId: string) {
  const data = await apiPost(`/api/ai/recommend`, { district_id: districtId });
  return aiRecommendationsResponseSchema.parse(data);
}

export async function getAIHistory(districtId: string) {
  const data = await apiGet(`/api/districts/${districtId}/ai/history`);
  return aiHistoryResponseSchema.parse(data);
}

export async function getSumoStatus() {
  return apiGet(`/api/sumo/status`);
}
