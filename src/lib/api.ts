/**
 * API client for Meeting Monitor backend
 */

/**
 * In dev, default to same-origin so Vite can proxy `/api` (see vite.config.ts).
 * Set VITE_API_URL when your API runs elsewhere (e.g. http://localhost:8001).
 */
const getBaseUrl = () => {
  const env = import.meta.env.VITE_API_URL as string | undefined;
  if (env && env.length > 0) return env.replace(/\/$/, "");
  if (import.meta.env.DEV) return "http://localhost:8001";
  return "http://localhost:8001";
};

export const apiBaseUrl = getBaseUrl();

export interface ApiUser {
  id: string;
  name: string;
  email: string;
  role: string;
  skills?: string[];
  avatar?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<{ token: TokenResponse; user: ApiUser }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/auth/login/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = Array.isArray(err.detail)
      ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
      : (err.detail ?? "Login failed");
    throw new Error(msg);
  }
  const data = (await res.json()) as {
    access_token?: string;
    token_type?: string;
    user?: ApiUser;
  };
  if (!data?.access_token) throw new Error("Invalid login response");

  const token: TokenResponse = {
    access_token: data.access_token,
    token_type: data.token_type ?? "bearer",
  };

  // Use inline user payload when the backend returns it (meeting-monitor /api/v1/auth/login/json);
  // otherwise fetch the profile separately (works against backends that only return the token).
  const user = data.user ?? (await fetchMe(token.access_token));
  return { token, user };
}

export async function forgotPassword(
  email: string,
): Promise<{ message: string; reset_token?: string; reset_url?: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = Array.isArray(err.detail)
      ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
      : (err.detail ?? "Request failed");
    throw new Error(msg);
  }
  return res.json();
}

export async function resetPassword(token: string, new_password: string): Promise<{ message: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = Array.isArray(err.detail)
      ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
      : (err.detail ?? "Reset failed");
    throw new Error(msg);
  }
  return res.json();
}

export async function register(data: {
  name: string;
  email: string;
  password: string;
  role: string;
  skills?: string[];
  avatar?: string | null;
}): Promise<ApiUser> {
  const res = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Registration failed");
  }
  return res.json();
}

export async function fetchMe(token: string): Promise<ApiUser> {
  const res = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Session expired");
  return res.json();
}

export function getAuthHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

/** WebSocket base URL for live meeting transcript (ws or wss from API host). */
export function getWsBaseUrl(): string {
  if (!apiBaseUrl) {
    const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
    const host = typeof window !== "undefined" ? window.location.host : "localhost:8080";
    return `${proto}://${host}`;
  }
  const u = apiBaseUrl.replace(/^http/, "ws");
  return u.endsWith("/") ? u.slice(0, -1) : u;
}

// --- Meeting bot: create, start, stop, get detail, live transcript ---

export interface MeetingBotDetail {
  meeting: { id: string; project_id?: string; title?: string; status: string; meeting_url?: string; started_at?: string; ended_at?: string };
  /** True when this API process has a bot process for the meeting (in-memory). */
  bot_running?: boolean;
  /** True when PCM is actively streaming from the bot to the STT pipeline. */
  bot_audio_streaming?: boolean;
  transcript_segments: { text: string; timestamp: string }[];
  transcripts: { text: string; timestamp: string }[];
  attendance: {
    participant_id: string;
    participant_name: string;
    join_time?: string;
    leave_time?: string;
    duration_seconds?: number;
    meeting_role?: string;
  }[];
  summary: {
    summary_text?: string;
    key_points?: string[];
    decisions?: string[];
    meeting_signals?: {
      confidence_score?: number;
      toxicity_score?: number;
      dominant_emotion?: string;
      emotion_scores?: {
        positive?: number;
        neutral?: number;
        negative?: number;
      };
    };
  } | null;
  action_items: { text: string }[];
  total_participants?: number;
  total_duration?: number | null;
}

export async function createMeeting(
  token: string,
  data: { project_id?: string; title?: string; meeting_url?: string }
): Promise<{ id: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create meeting");
  return res.json();
}

export async function startMeeting(
  token: string,
  meetingId: string,
  body: { meeting_url: string; project_id?: string; title?: string }
): Promise<{ message: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to start meeting");
  return res.json();
}

export async function stopMeeting(
  token: string,
  meetingId: string
): Promise<{ message: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}/stop`, {
    method: "POST",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to stop meeting");
  return res.json();
}

/** Persist Web Speech lines (call before end meeting so summary/intelligence sees them). */
export async function appendBrowserTranscriptSegments(
  token: string,
  meetingId: string,
  texts: string[]
): Promise<{ inserted: number; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}/transcript-segments/browser`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify({ texts }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const d = err.detail;
    throw new Error(typeof d === "string" ? d : "Failed to save transcript");
  }
  return res.json();
}

export async function getMeetingDetail(token: string, meetingId: string): Promise<MeetingBotDetail> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load meeting");
  return res.json();
}

export interface MeetingBotStatus {
  meeting_id: string;
  bot_available: boolean;
  bot_running: boolean;
  bot_audio_streaming: boolean;
}

export async function getMeetingBotStatus(token: string, meetingId: string): Promise<MeetingBotStatus> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}/bot-status`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load bot status");
  return res.json();
}

export async function deleteMeeting(
  token: string,
  meetingId: string
): Promise<{ message: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}`, {
    method: "DELETE",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to delete meeting");
  }
  return res.json();
}

export async function generateMeetingSummary(
  token: string,
  meetingId: string,
  language?: string
): Promise<{ message: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}/generate-summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify({ language: language ?? "en" }),
  });
  if (!res.ok) throw new Error("Failed to generate summary");
  return res.json();
}

/** Ask the meeting assistant (Groq) about transcript + summary context. */
export async function askMeetingQuestion(
  token: string,
  meetingId: string,
  question: string
): Promise<{ answer: string; meeting_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${encodeURIComponent(meetingId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify({ question: question.trim() }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg =
      typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
          : "Assistant unavailable";
    throw new Error(msg);
  }
  return res.json();
}

export interface MeetingBotListItem {
  id: string;
  project_id?: string;
  title?: string;
  status: string;
  meeting_url?: string;
  started_at?: string;
  ended_at?: string;
}

export async function listMeetings(
  token: string,
  projectId?: string
): Promise<{ meetings: MeetingBotListItem[] }> {
  const url = projectId
    ? `${apiBaseUrl}/api/v1/meetings?project_id=${encodeURIComponent(projectId)}`
    : `${apiBaseUrl}/api/v1/meetings`;
  const res = await fetch(url, { headers: getAuthHeaders(token) });
  if (!res.ok) throw new Error("Failed to load meetings");
  return res.json();
}

// --- Projects (workspaces & classes) - stored in database ---

export interface ProjectMember {
  id: string;
  name: string;
  email: string;
  /** Account/job role from user profile (not workspace Owner vs Member). */
  role?: string;
}

export interface ApiProject {
  id: string;
  name: string;
  description: string | null;
  invite_code: string;
  project_type: "workspace" | "class";
  owner_id: string;
  members: string[];
  member_details: ProjectMember[];
  created_at: string;
  updated_at: string;
  /** GitHub `owner/repo` when linked (Kanban webhook). */
  github_full_name?: string | null;
  github_webhook_enabled?: boolean;
  /** Last handled webhook for this repo mapping (manager diagnostics). */
  github_webhook_last_at?: string | null;
  github_webhook_last_event?: string | null;
  github_webhook_last_delivery?: string | null;
  github_webhook_last_result?: Record<string, unknown> | null;
}

export async function createProject(
  token: string,
  data: { name: string; description: string; invite_code: string; project_type: "workspace" | "class" }
): Promise<ApiProject> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create project");
  }
  return res.json();
}

/** Use in catch blocks to detect 401 and clear session (e.g. call logout). */
export function isUnauthorized(error: unknown): boolean {
  return (error as { status?: number })?.status === 401;
}

export async function listProjects(
  token: string,
  projectType?: "workspace" | "class"
): Promise<ApiProject[]> {
  const url = projectType
    ? `${apiBaseUrl}/api/v1/projects?project_type=${projectType}`
    : `${apiBaseUrl}/api/v1/projects`;
  const res = await fetch(url, { headers: getAuthHeaders(token) });
  if (!res.ok) {
    const err = new Error(res.status === 401 ? "Session expired" : "Failed to load projects") as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

/** Single entry from GitHub webhook completion (append-only on task). */
export interface ApiGitEvidenceEntry {
  source?: string;
  event?: string;
  sha?: string;
  url?: string;
  actor?: string;
  at?: string;
  message?: string;
}

export interface ApiTask {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "in_review" | "done" | "blockers";
  priority: "low" | "medium" | "high" | "urgent";
  assignee_id: string | null;
  assignee_name?: string | null;
  assigned_at?: string | null;
  due_date: string | null;
  subtasks: string[] | null;
  source_meeting_id: string | null;
  is_auto_generated: boolean;
  planner_generated?: boolean;
  /** When true, description was set by user/copilot/seed and is shown for AI tasks. */
  description_user_set?: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  /** Reference in PR/commit messages (e.g. MM-AB12CD34). */
  task_key?: string | null;
  git_evidence?: ApiGitEvidenceEntry[] | null;
  github_ci_head_sha?: string | null;
  github_ci_conclusion?: string | null;
  github_ci_updated_at?: string | null;
  github_ci_workflow_run_id?: number | null;
  github_ci_workflow_url?: string | null;
}

export interface ApiProjectWithTasks extends ApiProject {
  tasks: ApiTask[];
}

export async function getProject(token: string, projectId: string): Promise<ApiProjectWithTasks> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load project");
  return res.json();
}

export interface AnalyticsWeekBucket {
  week_start: string;
  week_end: string;
  created: number;
  completed: number;
  open_at_week_end: number;
}

export interface ProjectAnalyticsTimeseries {
  project_id: string;
  weeks: AnalyticsWeekBucket[];
  velocity_completed_per_week_avg: number;
}

export async function getProjectAnalyticsTimeseries(
  token: string,
  projectId: string,
  weeks: number = 8,
): Promise<ProjectAnalyticsTimeseries> {
  const q = new URLSearchParams({ weeks: String(weeks) });
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}/analytics/timeseries?${q}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
}

/** Public URL to paste in GitHub → Webhooks (depends on `VITE_API_URL` or current origin). */
export function getGithubWebhookCallbackUrl(): string {
  const base = (apiBaseUrl || "").replace(/\/$/, "");
  if (base) return `${base}/api/v1/webhooks/github`;
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api/v1/webhooks/github`;
  }
  return "/api/v1/webhooks/github";
}

export interface ConsiliumGithubRepo {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  private?: boolean;
}

export interface ConsiliumGithubRepoSummary {
  full_name: string;
  stars: number;
  forks: number;
  html_url: string;
}

export interface ConsiliumGithubActivity {
  repo: ConsiliumGithubRepoSummary | null;
  commits: Array<Record<string, unknown>>;
  pulls: Array<Record<string, unknown>>;
  pull_requests?: Array<Record<string, unknown>>;
}

export interface ConsiliumResolveWorkspaceResponse {
  workspace_id: string;
}

export async function resolveConsiliumWorkspaceId(
  token: string,
  projectId: string,
): Promise<string> {
  const res = await fetch(
    `${apiBaseUrl}/api/workspaces/resolve-project/${encodeURIComponent(projectId)}`,
    {
      method: "POST",
      headers: getAuthHeaders(token),
    },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to resolve workspace");
  }
  const data: ConsiliumResolveWorkspaceResponse = await res.json();
  return data.workspace_id;
}

export function getConsiliumGithubConnectUrl(workspaceId: string): string {
  const base = apiBaseUrl ? apiBaseUrl : window.location.origin;
  return `${base.replace(/\/$/, "")}/api/github/connect?workspace_id=${encodeURIComponent(workspaceId)}`;
}

export async function listConsiliumGithubRepos(
  token: string,
  workspaceId: string,
): Promise<ConsiliumGithubRepo[]> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/github/repos`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load GitHub repositories");
  }
  return res.json();
}

export async function selectConsiliumGithubRepo(
  token: string,
  workspaceId: string,
  payload: { owner: string; name: string },
): Promise<void> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/github/repo`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to save GitHub repository");
  }
}

export async function getConsiliumGithubActivity(
  token: string,
  workspaceId: string,
): Promise<ConsiliumGithubActivity> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/github/activity`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load GitHub activity");
  }
  return res.json();
}

export interface ConsiliumPrd {
  executive_summary?: string;
  overview: string;
  problem_statement: string;
  target_users: string[];
  market_analysis: string[];
  features: string[];
  user_stories: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  tech_stack: string[];
  system_architecture: string[];
  database_design: string[];
  api_design: string[];
  security: string[];
  performance: string[];
  deployment: string[];
  folder_structure: string[];
  milestones: string[];
  mvp_scope: string[];
  future_enhancements: string[];
  risks_and_mitigations?: string[];
  assumptions_and_out_of_scope?: string[];
  implementation_notes?: string[];
  observability_and_reason_codes?: string[];
  doc_sections?: Array<{
    id: string;
    title: string;
    type: string;
    content: string[];
  }>;
  [key: string]: unknown;
}

export interface ConsiliumRoadmapPhase {
  phase?: string;
  title?: string;
  goal?: string;
  date_range?: string;
  owners?: string[];
  streams?: Array<{
    stream: string;
    owner: string;
    actions: string[];
  }>;
  deliverables?: string[];
  execution_notes?: string;
  items?: string[];
}

export interface ConsiliumRoadmapTask {
  id?: string;
  title?: string;
  description?: string;
  status?: string;
  assigned_to?: string;
  assigned_to_name?: string;
}

export interface ConsiliumRoadmap {
  phases: ConsiliumRoadmapPhase[];
  tasks?: ConsiliumRoadmapTask[];
  milestone_tracker?: Array<{
    milestone: string;
    deliverable: string;
    primary_owner: string;
  }>;
}

export interface ConsiliumKanbanTask {
  id?: string;
  title?: string;
  description?: string | null;
  status?: string;
  priority?: string;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  assigned_user_id?: string | null;
  assigned_name?: string | null;
  created_at?: string;
  updated_at?: string;
  deadline?: string | null;
  source_meeting_id?: string | null;
  is_auto_generated?: boolean;
  planner_generated?: boolean;
}

export async function generateConsiliumPrd(
  token: string,
  workspaceId: string,
  payload: {
    product_name: string;
    product_description: string;
    target_users: string;
    key_features: string;
    competitors?: string;
    constraints?: string;
    meeting_id?: string;
  },
): Promise<ConsiliumPrd> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/generate-prd`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to generate PRD");
  }
  const data = (await res.json()) as { prd: ConsiliumPrd };
  return data.prd;
}

export async function getConsiliumPrd(
  token: string,
  workspaceId: string,
): Promise<{ prd: ConsiliumPrd | null; prd_status: string }> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/prd`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load PRD");
  }
  return res.json();
}

export async function saveConsiliumPrd(
  token: string,
  workspaceId: string,
  prd: ConsiliumPrd,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/prd`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify({ prd }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to save PRD");
  }
}

export async function finalizeConsiliumPrd(
  token: string,
  workspaceId: string,
): Promise<{ prd_status: string; roadmap: Record<string, unknown> | null }> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/finalize-prd`, {
    method: "POST",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to finalize PRD");
  }
  return res.json();
}

export async function getConsiliumRoadmap(
  token: string,
  workspaceId: string,
): Promise<ConsiliumRoadmap | null> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/roadmap`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load roadmap");
  }
  const data = (await res.json()) as { roadmap: ConsiliumRoadmap | null };
  return data.roadmap;
}

export async function getConsiliumKanbanTasks(
  token: string,
  workspaceId: string,
): Promise<ConsiliumKanbanTask[]> {
  const res = await fetch(`${apiBaseUrl}/api/workspaces/${encodeURIComponent(workspaceId)}/kanban`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load workspace kanban");
  }
  const data = (await res.json()) as { tasks?: ConsiliumKanbanTask[] };
  return Array.isArray(data.tasks) ? data.tasks : [];
}

/** Project owner only: link `owner/repo` and toggle webhook deliveries. */
export async function patchProjectGitHub(
  token: string,
  projectId: string,
  body: { github_full_name?: string | null; github_webhook_enabled?: boolean }
): Promise<ApiProject> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/github`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg =
      typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
          : "Failed to update GitHub settings";
    throw new Error(msg);
  }
  return res.json();
}

/** Workspace copilot: Q&A + actions (create meeting/task, update task, sync Kanban). */
export async function postWorkspaceCopilotChat(
  token: string,
  projectId: string,
  message: string,
  meetingId?: string | null
): Promise<{ answer: string; actions_executed: unknown[]; project_id: string }> {
  const res = await fetch(
    `${apiBaseUrl}/api/v1/projects/${encodeURIComponent(projectId)}/copilot/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
      body: JSON.stringify({
        message: message.trim(),
        ...(meetingId ? { meeting_id: meetingId } : {}),
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg =
      typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? err.detail.map((e: { msg?: string }) => e.msg).join(", ")
          : "Copilot request failed";
    throw new Error(msg);
  }
  return res.json();
}

export async function createProjectTask(
  token: string,
  projectId: string,
  data: {
    title: string;
    description?: string;
    status?: ApiTask["status"];
    priority?: ApiTask["priority"];
    assignee_id?: string | null;
    due_date?: string | null;
    subtasks?: string[] | null;
  }
): Promise<ApiTask> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to create task");
  }
  return res.json();
}

export async function updateProjectTask(
  token: string,
  projectId: string,
  taskId: string,
  data: Partial<{
    title: string;
    description: string | null;
    status: ApiTask["status"];
    priority: ApiTask["priority"];
    assignee_id: string | null;
    assignee_name: string | null;
    assigned_at: string | null;
    due_date: string | null;
    subtasks: string[] | null;
  }>
): Promise<ApiTask> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}/tasks/${taskId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to update task");
  }
  return res.json();
}

export async function deleteTask(token: string, taskId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl}/api/v1/tasks/${taskId}`, {
    method: "DELETE",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to delete task");
  }
}

export async function extractProjectTasks(
  token: string,
  projectId: string
): Promise<{ message: string; project_id: string }> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}/extract-tasks`, {
    method: "POST",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to extract tasks");
  }
  return res.json();
}

export async function joinProject(token: string, inviteCode: string): Promise<ApiProject> {
  const code = encodeURIComponent(inviteCode.trim());
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/join/${code}`, {
    method: "POST",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Invalid invite code");
  }
  return res.json();
}

export async function leaveProject(token: string, projectId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}/leave`, {
    method: "POST",
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to leave project");
  }
}

// --- Meeting recordings (upload → transcribe, summarize, extract action items) ---

export interface RecordingSummaryApi {
  overview: string;
  key_points: string[];
  decisions: string[];
}

export interface MeetingRecordingApi {
  id: string;
  user_id: string;
  project_id: string;
  title: string;
  file_name: string;
  status: string;
  transcription: string | null;
  summary: RecordingSummaryApi | null;
  summary_dict?: RecordingSummaryApi | null;
  action_items: string[];
  created_at: string;
  updated_at: string;
}

export async function uploadMeetingRecording(
  token: string,
  projectId: string,
  file: File,
  title?: string
): Promise<MeetingRecordingApi> {
  if (!token) throw new Error("Not authenticated");
  const form = new FormData();
  form.append("file", file);
  form.append("project_id", projectId);
  form.append("access_token", token);
  if (title != null && title.trim() !== "") form.append("title", title.trim());
  const res = await fetch(`${apiBaseUrl}/api/v1/recordings/upload`, {
    method: "POST",
    headers: getAuthHeaders(token),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
  }
  return res.json();
}

export async function listMeetingRecordings(
  token: string,
  projectId?: string
): Promise<MeetingRecordingApi[]> {
  const url = projectId
    ? `${apiBaseUrl}/api/v1/recordings?project_id=${encodeURIComponent(projectId)}`
    : `${apiBaseUrl}/api/v1/recordings`;
  const res = await fetch(url, { headers: getAuthHeaders(token) });
  if (!res.ok) throw new Error("Failed to load recordings");
  return res.json();
}

export async function getMeetingRecording(
  token: string,
  recordingId: string
): Promise<MeetingRecordingApi> {
  const res = await fetch(`${apiBaseUrl}/api/v1/recordings/${recordingId}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load recording");
  return res.json();
}
