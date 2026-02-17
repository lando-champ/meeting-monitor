import { Meeting, Task, TeamMember } from "@/lib/types";

const meetingKey = (workspaceId: string) => `meetingSense:workspace:${workspaceId}:meetings`;
const taskKey = (workspaceId: string) => `meetingSense:workspace:${workspaceId}:tasks`;
const memberKey = (workspaceId: string) => `meetingSense:workspace:${workspaceId}:members`;

const parseMeetings = (data: string): Meeting[] =>
  (JSON.parse(data) as Meeting[]).map((meeting) => ({
    ...meeting,
    startTime: new Date(meeting.startTime),
    endTime: new Date(meeting.endTime),
  }));

const parseTasks = (data: string): Task[] =>
  (JSON.parse(data) as Task[]).map((task) => ({
    ...task,
    dueDate: task.dueDate ? new Date(task.dueDate) : undefined,
    createdAt: new Date(task.createdAt),
    updatedAt: new Date(task.updatedAt),
    completedAt: task.completedAt ? new Date(task.completedAt) : undefined,
  }));

export const loadWorkspaceMeetings = (workspaceId: string, fallback: Meeting[]) => {
  const stored = localStorage.getItem(meetingKey(workspaceId));
  if (!stored) {
    localStorage.setItem(meetingKey(workspaceId), JSON.stringify(fallback));
    return fallback;
  }
  try {
    return parseMeetings(stored);
  } catch {
    return fallback;
  }
};

export const saveWorkspaceMeetings = (workspaceId: string, meetings: Meeting[]) => {
  localStorage.setItem(meetingKey(workspaceId), JSON.stringify(meetings));
};

export const loadWorkspaceTasks = (workspaceId: string, fallback: Task[]) => {
  const stored = localStorage.getItem(taskKey(workspaceId));
  if (!stored) {
    localStorage.setItem(taskKey(workspaceId), JSON.stringify(fallback));
    return fallback;
  }
  try {
    return parseTasks(stored);
  } catch {
    return fallback;
  }
};

export const saveWorkspaceTasks = (workspaceId: string, tasks: Task[]) => {
  localStorage.setItem(taskKey(workspaceId), JSON.stringify(tasks));
};

export const loadWorkspaceMembers = (workspaceId: string, fallback: TeamMember[]) => {
  const stored = localStorage.getItem(memberKey(workspaceId));
  if (!stored) {
    localStorage.setItem(memberKey(workspaceId), JSON.stringify(fallback));
    return fallback;
  }
  try {
    return JSON.parse(stored) as TeamMember[];
  } catch {
    return fallback;
  }
};

export const saveWorkspaceMembers = (workspaceId: string, members: TeamMember[]) => {
  localStorage.setItem(memberKey(workspaceId), JSON.stringify(members));
};

export interface WorkspaceDocument {
  id: string;
  name: string;
  type: string;
  size: string;
  modified: string;
  url?: string;
  content?: string;
}

const docKey = (workspaceId: string) => `meetingSense:workspace:${workspaceId}:documents`;

const defaultDocs: WorkspaceDocument[] = [
  { id: "1", name: "Sprint Planning Notes", type: "doc", size: "245 KB", modified: "2 hours ago" },
  { id: "2", name: "Q4 Goals Presentation", type: "ppt", size: "1.2 MB", modified: "Yesterday" },
  { id: "3", name: "Meeting Recording - Dec 15", type: "video", size: "156 MB", modified: "3 days ago" },
  { id: "4", name: "Project Requirements", type: "doc", size: "89 KB", modified: "1 week ago" },
  { id: "5", name: "Design Assets", type: "folder", size: "23 files", modified: "2 weeks ago" },
];

export const loadWorkspaceDocuments = (workspaceId: string): WorkspaceDocument[] => {
  const stored = localStorage.getItem(docKey(workspaceId));
  if (!stored) {
    localStorage.setItem(docKey(workspaceId), JSON.stringify(defaultDocs));
    return defaultDocs;
  }
  try {
    return JSON.parse(stored);
  } catch {
    return defaultDocs;
  }
};

export const saveWorkspaceDocuments = (workspaceId: string, docs: WorkspaceDocument[]) => {
  localStorage.setItem(docKey(workspaceId), JSON.stringify(docs));
};
