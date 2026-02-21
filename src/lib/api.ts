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

export async function getProject(token: string, projectId: string): Promise<ApiProject> {
  const res = await fetch(`${apiBaseUrl}/api/v1/projects/${projectId}`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load project");
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
