/**
 * API client for Meeting Monitor backend
 */

const getBaseUrl = () => import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const apiBaseUrl = getBaseUrl();

export interface ApiUser {
  id: string;
  name: string;
  email: string;
  role: "manager" | "member" | "teacher" | "student";
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
    const msg = Array.isArray(err.detail) ? err.detail.map((e: { msg?: string }) => e.msg).join(", ") : (err.detail ?? "Login failed");
    throw new Error(msg);
  }
  const token: TokenResponse = await res.json();
  if (!token?.access_token) throw new Error("Invalid login response");

  const meRes = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token.access_token}` },
  });
  if (!meRes.ok) {
    const err = await meRes.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Failed to load user");
  }
  const user: ApiUser = await meRes.json();
  return { token, user };
}

export async function register(data: {
  name: string;
  email: string;
  password: string;
  role: "manager" | "member" | "teacher" | "student";
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
  const u = apiBaseUrl.replace(/^http/, "ws");
  return u.endsWith("/") ? u.slice(0, -1) : u;
}

// --- Meeting bot: create, start, stop, get detail, live transcript ---

export interface MeetingBotDetail {
  meeting: { id: string; project_id?: string; title?: string; status: string; meeting_url?: string; started_at?: string; ended_at?: string };
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
  summary: { summary_text?: string; key_points?: string[] } | null;
  action_items: { text: string; status: string }[];
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

export async function getMeetingDetail(token: string, meetingId: string): Promise<MeetingBotDetail> {
  const res = await fetch(`${apiBaseUrl}/api/v1/meetings/${meetingId}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load meeting");
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

export async function listProjects(
  token: string,
  projectType?: "workspace" | "class"
): Promise<ApiProject[]> {
  const url = projectType
    ? `${apiBaseUrl}/api/v1/projects?project_type=${projectType}`
    : `${apiBaseUrl}/api/v1/projects`;
  const res = await fetch(url, { headers: getAuthHeaders(token) });
  if (!res.ok) throw new Error("Failed to load projects");
  return res.json();
}

export interface ApiTask {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "in_review" | "done" | "blockers";
  priority: "low" | "medium" | "high" | "urgent";
  assignee_id: string | null;
  due_date: string | null;
  subtasks: string[] | null;
  source_meeting_id: string | null;
  is_auto_generated: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
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
