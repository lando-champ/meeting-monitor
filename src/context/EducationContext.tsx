import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type MeetingPlatform = "jitsi" | "gmeet" | "zoom" | "teams";

export interface EducationLecture {
  id: string;
  title: string;
  classId: string;
  className: string;
  date: string;
  time: string;
  meetingLink: string;
  platform: MeetingPlatform;
  description: string;
  status: "scheduled" | "live" | "completed";
  summary?: {
    overview: string;
    keyPoints: string[];
    decisions: string[];
    actionItems: string[];
    sentiment: string;
  };
  notes?: string;
  transcript?: { speaker: string; text: string; timestamp: string }[];
  attendance?: { id: string; name: string; email: string; joinedAt?: string }[];
  tasks?: { id: string; title: string; assignee: string; status: string }[];
}

export interface EducationAssignment {
  id: string;
  title: string;
  description: string;
  dueDate: string;
  classId: string;
  lectureId?: string;
  createdAt: string;
}

export interface AssignmentSubmission {
  id: string;
  assignmentId: string;
  studentId: string;
  studentName: string;
  content: string;
  submittedAt: string;
}

const STORAGE_KEY = "meetingSenseEducation";

const loadStored = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    return {
      lectures: (data.lectures ?? []) as EducationLecture[],
      assignments: (data.assignments ?? []) as EducationAssignment[],
      submissions: (data.submissions ?? []) as AssignmentSubmission[],
    };
  } catch {
    return null;
  }
};

interface EducationContextValue {
  lectures: EducationLecture[];
  assignments: EducationAssignment[];
  submissions: AssignmentSubmission[];
  addLecture: (lecture: Omit<EducationLecture, "id">) => EducationLecture;
  addLiveSession: (lecture: Omit<EducationLecture, "id" | "status">) => EducationLecture;
  getLecturesByClass: (classId: string) => EducationLecture[];
  addAssignment: (assignment: Omit<EducationAssignment, "id">) => EducationAssignment;
  getAssignmentsByClass: (classId: string) => EducationAssignment[];
  submitAssignment: (submission: Omit<AssignmentSubmission, "id">) => AssignmentSubmission;
  getSubmissionsByAssignment: (assignmentId: string) => AssignmentSubmission[];
  getLectureById: (id: string) => EducationLecture | undefined;
  getAssignmentsForStudent: (classId: string) => EducationAssignment[];
}

const EducationContext = createContext<EducationContextValue | undefined>(undefined);

export const EducationProvider = ({ children }: { children: React.ReactNode }) => {
  const stored = loadStored();
  const [lectures, setLectures] = useState<EducationLecture[]>(
    stored?.lectures ?? []
  );
  const [assignments, setAssignments] = useState<EducationAssignment[]>(
    stored?.assignments ?? []
  );
  const [submissions, setSubmissions] = useState<AssignmentSubmission[]>(
    stored?.submissions ?? []
  );

  const persist = useCallback(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ lectures, assignments, submissions })
    );
  }, [lectures, assignments, submissions]);

  const addLecture = useCallback(
    (lecture: Omit<EducationLecture, "id">) => {
      const id = `lec-${Date.now()}`;
      const newLecture: EducationLecture = { ...lecture, id, status: "scheduled" };
      setLectures((prev) => {
        const next = [...prev, newLecture];
        setTimeout(() => {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ lectures: next, assignments, submissions })
          );
        }, 0);
        return next;
      });
      return newLecture;
    },
    [assignments, submissions]
  );

  const addLiveSession = useCallback(
    (lecture: Omit<EducationLecture, "id" | "status">) => {
      const id = `lec-${Date.now()}`;
      const newLecture: EducationLecture = {
        ...lecture,
        id,
        status: "live",
      };
      setLectures((prev) => {
        const next = [...prev, newLecture];
        setTimeout(() => {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ lectures: next, assignments, submissions })
          );
        }, 0);
        return next;
      });
      return newLecture;
    },
    [assignments, submissions]
  );

  const getLecturesByClass = useCallback(
    (classId: string) =>
      lectures.filter((l) => l.classId === classId),
    [lectures]
  );

  const addAssignment = useCallback(
    (assignment: Omit<EducationAssignment, "id">) => {
      const id = `a-${Date.now()}`;
      const newAssignment: EducationAssignment = { ...assignment, id };
      setAssignments((prev) => {
        const next = [...prev, newAssignment];
        setTimeout(() => {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ lectures, assignments: next, submissions })
          );
        }, 0);
        return next;
      });
      return newAssignment;
    },
    [lectures, submissions]
  );

  const getAssignmentsByClass = useCallback(
    (classId: string) =>
      assignments.filter((a) => a.classId === classId),
    [assignments]
  );

  const submitAssignment = useCallback(
    (submission: Omit<AssignmentSubmission, "id">) => {
      const id = `sub-${Date.now()}`;
      const newSubmission: AssignmentSubmission = { ...submission, id };
      setSubmissions((prev) => {
        const next = [...prev, newSubmission];
        setTimeout(() => {
          localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ lectures, assignments, submissions: next })
          );
        }, 0);
        return next;
      });
      return newSubmission;
    },
    [lectures, assignments]
  );

  const getSubmissionsByAssignment = useCallback(
    (assignmentId: string) =>
      submissions.filter((s) => s.assignmentId === assignmentId),
    [submissions]
  );

  const getLectureById = useCallback(
    (id: string) => lectures.find((l) => l.id === id),
    [lectures]
  );

  const getAssignmentsForStudent = useCallback(
    (classId: string) =>
      assignments.filter((a) => a.classId === classId),
    [assignments]
  );

  const value = useMemo<EducationContextValue>(
    () => ({
      lectures,
      assignments,
      submissions,
      addLecture,
      addLiveSession,
      getLecturesByClass,
      addAssignment,
      getAssignmentsByClass,
      submitAssignment,
      getSubmissionsByAssignment,
      getLectureById,
      getAssignmentsForStudent,
    }),
    [
      lectures,
      assignments,
      submissions,
      addLecture,
      addLiveSession,
      getLecturesByClass,
      addAssignment,
      getAssignmentsByClass,
      submitAssignment,
      getSubmissionsByAssignment,
      getLectureById,
      getAssignmentsForStudent,
    ]
  );

  return (
    <EducationContext.Provider value={value}>{children}</EducationContext.Provider>
  );
};

export const useEducation = () => {
  const ctx = useContext(EducationContext);
  if (!ctx) {
    throw new Error("useEducation must be used within EducationProvider");
  }
  return ctx;
};
