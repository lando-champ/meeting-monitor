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

const defaultLectures: EducationLecture[] = [
  {
    id: "lec-1",
    title: "Introduction to Variables and Data Types",
    classId: "cs101",
    className: "Intro to Computer Science",
    date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    time: "10:00",
    meetingLink: "https://meet.jit.si/intro-cs-variables",
    platform: "jitsi",
    description: "Fundamental concepts of variables and data types in Python.",
    status: "completed",
    summary: {
      overview: "Covered fundamental concepts of variables, data types, and basic operations in Python.",
      keyPoints: [
        "Variables as containers for storing data",
        "Primitive data types: int, float, string, boolean",
        "Type conversion and casting",
        "Basic arithmetic operators",
      ],
      decisions: [],
      actionItems: ["Complete Chapter 2 exercises", "Practice variable declarations"],
      sentiment: "positive",
    },
    notes: "Focus on type casting and operator precedence. Students struggled with float division.",
    transcript: [
      { speaker: "Prof. Wilson", text: "Today we'll cover variables and data types in Python.", timestamp: "00:00" },
      { speaker: "Prof. Wilson", text: "Variables are containers for storing data values.", timestamp: "02:15" },
      { speaker: "Prof. Wilson", text: "We have int, float, string, and boolean as primitive types.", timestamp: "05:30" },
    ],
    attendance: [
      { id: "s1", name: "Alex Johnson", email: "alex@uni.edu", joinedAt: "09:58" },
      { id: "s2", name: "Emma Thompson", email: "emma@uni.edu", joinedAt: "10:02" },
      { id: "s3", name: "John Doe", email: "john@uni.edu", joinedAt: "10:05" },
    ],
    tasks: [
      { id: "t1", title: "Chapter 2 exercises", assignee: "All", status: "assigned" },
      { id: "t2", title: "Practice variable declarations", assignee: "Alex Johnson", status: "in-progress" },
    ],
  },
  {
    id: "lec-2",
    title: "Control Flow: Conditionals",
    classId: "cs101",
    className: "Intro to Computer Science",
    date: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    time: "10:00",
    meetingLink: "https://meet.jit.si/control-flow-cs101",
    platform: "jitsi",
    description: "if/else, switch, and conditional logic.",
    status: "scheduled",
  },
  {
    id: "lec-3",
    title: "Binary Search Trees",
    classId: "cs202",
    className: "Data Structures",
    date: new Date().toISOString().slice(0, 10),
    time: "14:00",
    meetingLink: "https://meet.jit.si/bst-data-structures",
    platform: "jitsi",
    description: "BST implementation and traversal.",
    status: "live",
  },
];

const defaultAssignments: EducationAssignment[] = [
  {
    id: "a1",
    title: "Chapter 2 Exercises - Variables",
    description: "Complete all exercises from Chapter 2 focusing on variable declarations and data types.",
    dueDate: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    classId: "cs101",
    lectureId: "lec-1",
    createdAt: new Date().toISOString(),
  },
  {
    id: "a2",
    title: "Build a Calculator App",
    description: "Create a simple calculator using Python that can perform basic arithmetic operations.",
    dueDate: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    classId: "cs101",
    createdAt: new Date().toISOString(),
  },
];

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
    stored?.lectures?.length ? stored.lectures : defaultLectures
  );
  const [assignments, setAssignments] = useState<EducationAssignment[]>(
    stored?.assignments?.length ? stored.assignments : defaultAssignments
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
