import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ClassRole = "teacher" | "student";

export interface ClassItem {
  id: string;
  name: string;
  description: string;
  inviteCode: string;
  ownerEmail: string;
  students: string[];
  studentCount: number;
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
  createClass: (name: string, description: string, inviteCode: string) => ClassItem;
  joinClass: (code: string) => ClassItem | null;
  addStudentToClass: (classId: string, studentEmail: string) => void;
  hasAccessToClass: (classId: string) => boolean;
  getClassByInviteCode: (code: string) => ClassItem | null;
}

const ClassContext = createContext<ClassContextValue | undefined>(undefined);

const STORAGE_KEY = "meetingSenseClasses";

const teacherEmail = "prof.wilson@university.edu";
const studentEmail = "emma.thompson@university.edu";

const initialClasses: ClassItem[] = [
  {
    id: "cs101",
    name: "Intro to Computer Science",
    description: "Foundations of computing",
    inviteCode: "CS101",
    ownerEmail: teacherEmail,
    students: [teacherEmail, studentEmail],
    studentCount: 2,
  },
  {
    id: "cs202",
    name: "Data Structures",
    description: "Core data structures and algorithms",
    inviteCode: "CS202",
    ownerEmail: teacherEmail,
    students: [teacherEmail, studentEmail],
    studentCount: 2,
  },
  {
    id: "webdev",
    name: "Web Development",
    description: "Frontend and backend fundamentals",
    inviteCode: "WEBDEV",
    ownerEmail: teacherEmail,
    students: [teacherEmail],
    studentCount: 1,
  },
];

export const ClassProvider = ({ children }: { children: React.ReactNode }) => {
  const [role, setRole] = useState<ClassRole | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as ClassItem[];
        return parsed.map((cls) => ({
          ...cls,
          students: cls.students ?? [],
          studentCount: cls.students?.length ?? cls.studentCount ?? 0,
        }));
      } catch {
        return initialClasses;
      }
    }
    return initialClasses;
  });
  const [currentClassId, setCurrentClassId] = useState<string | null>(null);

  const currentUserEmail = useMemo(() => {
    if (role === "student") {
      return studentEmail;
    }
    return teacherEmail;
  }, [role]);

  useEffect(() => {
    if (!currentClassId && classes.length) {
      setCurrentClassId(classes[0].id);
    }
  }, [currentClassId, classes]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(classes));
  }, [classes]);

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
    (name: string, description: string, inviteCode: string) => {
      const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)+/g, "");
      const cls: ClassItem = {
        id: id || `class-${Date.now()}`,
        name,
        description,
        inviteCode,
        ownerEmail: teacherEmail,
        students: [teacherEmail],
        studentCount: 1,
      };
      setClasses((prev) => [...prev, cls]);
      setCurrentClassId(cls.id);
      return cls;
    },
    [setClasses],
  );

  const joinClass = useCallback(
    (code: string) => {
      const cls = classes.find((item) => item.inviteCode.toLowerCase() === code.toLowerCase());
      if (!cls) {
        return null;
      }
      setClasses((prev) =>
        prev.map((item) =>
          item.id === cls.id && !item.students.includes(studentEmail)
            ? {
                ...item,
                students: [...item.students, studentEmail],
                studentCount: item.students.length + 1,
              }
            : item,
        ),
      );
      setCurrentClassId(cls.id);
      return cls;
    },
    [classes],
  );

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
      if (!cls) {
        return false;
      }
      if (role === "student") {
        return cls.students.includes(currentUserEmail);
      }
      return true;
    },
    [classes, role, currentUserEmail],
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
