import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type WorkspaceRole = "manager" | "member";

export interface Workspace {
  id: string;
  name: string;
  description: string;
  inviteCode: string;
  ownerEmail: string;
  members: string[];
  membersCount: number;
}

interface WorkspaceContextValue {
  role: WorkspaceRole | null;
  workspaces: Workspace[];
  currentWorkspaceId: string | null;
  currentWorkspace: Workspace | null;
  currentUserEmail: string;
  setRole: (role: WorkspaceRole) => void;
  setCurrentWorkspaceId: (id: string) => void;
  ensureWorkspace: (id: string) => void;
  createWorkspace: (name: string, description: string, inviteCode: string) => Workspace;
  joinWorkspace: (code: string) => Workspace | null;
  addMemberToWorkspace: (workspaceId: string, memberEmail: string) => void;
  hasAccessToWorkspace: (workspaceId: string) => boolean;
  getWorkspaceByInviteCode: (code: string) => Workspace | null;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

const STORAGE_KEY = "meetingSenseWorkspaces";

const managerEmail = "sarah.chen@company.com";
const memberEmail = "alex.kim@company.com";

const initialWorkspaces: Workspace[] = [
  {
    id: "alpha",
    name: "Alpha Project",
    description: "Core product development",
    inviteCode: "ALPHA2025",
    ownerEmail: managerEmail,
    members: [managerEmail],
    membersCount: 1,
  },
  {
    id: "growth",
    name: "Growth Team",
    description: "Acquisition and retention initiatives",
    inviteCode: "GROWTH2025",
    ownerEmail: managerEmail,
    members: [managerEmail],
    membersCount: 1,
  },
  {
    id: "platform",
    name: "Platform Initiative",
    description: "Infrastructure and enablement",
    inviteCode: "PLATFORM25",
    ownerEmail: managerEmail,
    members: [managerEmail],
    membersCount: 1,
  },
];

export const WorkspaceProvider = ({ children }: { children: React.ReactNode }) => {
  const [role, setRole] = useState<WorkspaceRole | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Workspace[];
        return parsed.map((workspace) => ({
          ...workspace,
          members: workspace.members ?? [],
          membersCount: workspace.members?.length ?? workspace.membersCount ?? 0,
        }));
      } catch {
        return initialWorkspaces;
      }
    }
    return initialWorkspaces;
  });
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);

  const currentUserEmail = useMemo(() => {
    if (role === "member") {
      return memberEmail;
    }
    return managerEmail;
  }, [role]);

  useEffect(() => {
    if (!currentWorkspaceId && workspaces.length) {
      setCurrentWorkspaceId(workspaces[0].id);
    }
  }, [currentWorkspaceId, workspaces]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(workspaces));
  }, [workspaces]);

  const currentWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === currentWorkspaceId) ?? null,
    [currentWorkspaceId, workspaces],
  );

  const ensureWorkspace = useCallback(
    (id: string) => {
      if (workspaces.some((workspace) => workspace.id === id)) {
        setCurrentWorkspaceId(id);
      }
    },
    [workspaces],
  );

  const createWorkspace = useCallback(
    (name: string, description: string, inviteCode: string) => {
      const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)+/g, "");
      const workspace: Workspace = {
        id: id || `workspace-${Date.now()}`,
        name,
        description,
        inviteCode,
        ownerEmail: managerEmail,
        members: [managerEmail],
        membersCount: 1,
      };
      setWorkspaces((prev) => [...prev, workspace]);
      setCurrentWorkspaceId(workspace.id);
      return workspace;
    },
    [setWorkspaces],
  );

  const joinWorkspace = useCallback(
    (code: string) => {
      const workspace = workspaces.find(
        (item) => item.inviteCode.toLowerCase() === code.toLowerCase(),
      );
      if (!workspace) {
        return null;
      }
      setWorkspaces((prev) =>
        prev.map((item) =>
          item.id === workspace.id && !item.members.includes(memberEmail)
            ? {
                ...item,
                members: [...item.members, memberEmail],
                membersCount: item.members.length + 1,
              }
            : item,
        ),
      );
      setCurrentWorkspaceId(workspace.id);
      return workspace;
    },
    [workspaces],
  );

  const addMemberToWorkspace = useCallback(
    (workspaceId: string, member: string) => {
      setWorkspaces((prev) =>
        prev.map((workspace) => {
          if (workspace.id !== workspaceId) {
            return workspace;
          }
          if (workspace.members.includes(member)) {
            return workspace;
          }
          const updatedMembers = [...workspace.members, member];
          return {
            ...workspace,
            members: updatedMembers,
            membersCount: updatedMembers.length,
          };
        }),
      );
    },
    [setWorkspaces],
  );

  const hasAccessToWorkspace = useCallback(
    (workspaceId: string) => {
      const workspace = workspaces.find((item) => item.id === workspaceId);
      if (!workspace) {
        return false;
      }
      if (role === "member") {
        return workspace.members.includes(currentUserEmail);
      }
      return true;
    },
    [workspaces, role, currentUserEmail],
  );

  const getWorkspaceByInviteCode = useCallback(
    (code: string) =>
      workspaces.find((workspace) => workspace.inviteCode.toLowerCase() === code.toLowerCase()) ??
      null,
    [workspaces],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      role,
      workspaces,
      currentWorkspaceId,
      currentWorkspace,
      currentUserEmail,
      setRole,
      setCurrentWorkspaceId,
      ensureWorkspace,
      createWorkspace,
      joinWorkspace,
      addMemberToWorkspace,
      hasAccessToWorkspace,
      getWorkspaceByInviteCode,
    }),
    [
      role,
      workspaces,
      currentWorkspaceId,
      currentWorkspace,
      currentUserEmail,
      setRole,
      ensureWorkspace,
      createWorkspace,
      joinWorkspace,
      addMemberToWorkspace,
      hasAccessToWorkspace,
      getWorkspaceByInviteCode,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
};
