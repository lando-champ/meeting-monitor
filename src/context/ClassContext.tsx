import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  listProjects,
  createProject,
  joinProject,
  leaveProject,
  type ApiProject,
  type ProjectMember,
} from "@/lib/api";

export type ClassRole = "teacher" | "student";

export interface ClassItem {
  id: string;
  name: string;
  description: string;
  inviteCode: string;
  ownerId: string;
  ownerEmail: string;
  students: string[];
  studentCount: number;
  memberDetails: ProjectMember[];
}

interface ClassContextValue {
  role: ClassRole | null;
  classes: ClassItem[];
  currentClassId: string | null;
  currentClass: ClassItem | null;
  currentUserEmail: string;
  setRole: (role: ClassRole) => void;
  setCurrentClassId: (id: string) => void;
  ensureClass: (id: string) => void;
  createClass: (name: string, description: string, inviteCode: string) => Promise<ClassItem>;
  joinClass: (code: string) => Promise<ClassItem>;
  deleteClass: (classId: string) => Promise<boolean>;
  leaveClass: (classId: string) => Promise<boolean>;
  deleteAllClasses: () => Promise<number>;
  addStudentToClass: (classId: string, studentEmail: string) => void;
  hasAccessToClass: (classId: string) => boolean;
  getClassByInviteCode: (code: string) => ClassItem | null;
}

const ClassContext = createContext<ClassContextValue | undefined>(undefined);

function mapApiProjectToClass(p: ApiProject): ClassItem {
  const owner = p.member_details?.find((m) => m.id === p.owner_id);
  const studentEmails = (p.member_details ?? []).map((m) => m.email);
  return {
    id: p.id,
    name: p.name,
    description: p.description ?? "",
    inviteCode: p.invite_code,
    ownerId: p.owner_id,
    ownerEmail: owner?.email ?? "",
    students: studentEmails,
    studentCount: (p.member_details ?? []).length,
    memberDetails: p.member_details ?? [],
  };
}

export const ClassProvider = ({ children }: { children: React.ReactNode }) => {
  const { user, token } = useAuth();
  const [role, setRole] = useState<ClassRole | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [currentClassId, setCurrentClassId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const currentUserEmail = user?.email ?? "";

  const fetchClasses = useCallback(async () => {
    if (!token) {
      setClasses([]);
      setLoading(false);
      return;
    }
    try {
      const list = await listProjects(token, "class");
      setClasses(list.map(mapApiProjectToClass));
      setCurrentClassId((id) => (id && list.some((p) => p.id === id)) ? id : (list[0]?.id ?? null));
    } catch {
      setClasses([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    setLoading(true);
    fetchClasses();
  }, [fetchClasses]);

  useEffect(() => {
    if (!currentClassId && classes.length) {
      setCurrentClassId(classes[0].id);
    }
  }, [currentClassId, classes]);

  const currentClass = useMemo(
    () => classes.find((cls) => cls.id === currentClassId) ?? null,
    [currentClassId, classes],
  );

  const ensureClass = useCallback(
    (id: string) => {
      if (classes.some((cls) => cls.id === id)) {
        setCurrentClassId(id);
      }
    },
    [classes],
  );

  const createClass = useCallback(
    async (name: string, description: string, inviteCode: string) => {
      if (!token) throw new Error("Not authenticated");
      const created = await createProject(token, {
        name: name.trim(),
        description: description.trim(),
        invite_code: inviteCode.trim(),
        project_type: "class",
      });
      const cls = mapApiProjectToClass(created);
      setClasses((prev) => [...prev, cls]);
      setCurrentClassId(cls.id);
      return cls;
    },
    [token],
  );

  const joinClass = useCallback(
    async (code: string) => {
      if (!token) throw new Error("Not authenticated");
      const joined = await joinProject(token, code);
      const cls = mapApiProjectToClass(joined);
      setClasses((prev) => {
        if (prev.some((c) => c.id === cls.id)) {
          return prev.map((c) => (c.id === cls.id ? cls : c));
        }
        return [...prev, cls];
      });
      setCurrentClassId(cls.id);
      return cls;
    },
    [token],
  );

  const deleteClass = useCallback(
    async (classId: string) => {
      if (!token) return false;
      try {
        await leaveProject(token, classId);
        setClasses((prev) => prev.filter((c) => c.id !== classId));
        setCurrentClassId((id) => (id === classId ? null : id));
        return true;
      } catch {
        return false;
      }
    },
    [token],
  );

  const leaveClass = useCallback(
    (classId: string) => deleteClass(classId),
    [deleteClass],
  );

  const deleteAllClasses = useCallback(async () => {
    if (!token) return 0;
    const count = classes.length;
    if (count === 0) return 0;
    for (const c of classes) {
      try {
        await leaveProject(token, c.id);
      } catch {
        /* skip */
      }
    }
    setClasses([]);
    setCurrentClassId(null);
    return count;
  }, [classes, token]);

  const addStudentToClass = useCallback(
    (classId: string, student: string) => {
      setClasses((prev) =>
        prev.map((cls) => {
          if (cls.id !== classId) {
            return cls;
          }
          if (cls.students.includes(student)) {
            return cls;
          }
          const updatedStudents = [...cls.students, student];
          return { ...cls, students: updatedStudents, studentCount: updatedStudents.length };
        }),
      );
    },
    [setClasses],
  );

  const hasAccessToClass = useCallback(
    (classId: string) => {
      const cls = classes.find((item) => item.id === classId);
      if (!cls) return false;
      return cls.students.includes(currentUserEmail);
    },
    [classes, currentUserEmail],
  );

  const getClassByInviteCode = useCallback(
    (code: string) =>
      classes.find((item) => item.inviteCode.toLowerCase() === code.toLowerCase()) ?? null,
    [classes],
  );

  const value = useMemo<ClassContextValue>(
    () => ({
      role,
      classes,
      currentClassId,
      currentClass,
      currentUserEmail,
      setRole,
      setCurrentClassId,
      ensureClass,
      createClass,
      joinClass,
      deleteClass,
      leaveClass,
      deleteAllClasses,
      addStudentToClass,
      hasAccessToClass,
      getClassByInviteCode,
    }),
    [
      role,
      classes,
      currentClassId,
      currentClass,
      currentUserEmail,
      setRole,
      ensureClass,
      createClass,
      joinClass,
      deleteClass,
      leaveClass,
      deleteAllClasses,
      addStudentToClass,
      hasAccessToClass,
      getClassByInviteCode,
    ],
  );

  return <ClassContext.Provider value={value}>{children}</ClassContext.Provider>;
};

export const useClass = () => {
  const context = useContext(ClassContext);
  if (!context) {
    throw new Error("useClass must be used within a ClassProvider");
  }
  return context;
};
