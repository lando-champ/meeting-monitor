import { useEffect } from "react";
import { Navigate, Outlet, Route, useNavigate, useParams } from "react-router-dom";
import EducationRoleSelect from "@/pages/education/RoleSelect";
import TeacherDashboard from "@/pages/education/TeacherDashboard";
import TeacherClasses from "@/pages/education/TeacherClasses";
import TeacherLectures from "@/pages/education/TeacherLectures";
import TeacherAssignments from "@/pages/education/TeacherAssignments";
import TeacherStudents from "@/pages/education/TeacherStudents";
import TeacherSettings from "@/pages/education/TeacherSettings";
import TeacherCalendar from "@/pages/education/TeacherCalendar";
import LectureSummary from "@/pages/education/LectureSummary";
import MeetingDetails from "@/pages/education/MeetingDetails";
import StudentDashboard from "@/pages/education/StudentDashboard";
import StudentClasses from "@/pages/education/StudentClasses";
import StudentTodo from "@/pages/education/StudentTodo";
import StudentNotes from "@/pages/education/StudentNotes";
import StudentCalendar from "@/pages/education/StudentCalendar";
import ClassList from "@/features/classes/ClassList";
import { useClass, ClassRole } from "@/context/ClassContext";

const ClassGate = ({ role }: { role: ClassRole }) => {
  const { classId } = useParams();
  const { setRole, ensureClass, hasAccessToClass } = useClass();
  const navigate = useNavigate();
  const basePath = role === "teacher" ? "/education/teacher/classes" : "/education/student/classes";

  useEffect(() => {
    setRole(role);
    if (classId) {
      ensureClass(classId);
    }
    if (classId && !hasAccessToClass(classId)) {
      navigate(basePath, { replace: true });
    }
  }, [role, setRole, ensureClass, classId, hasAccessToClass, navigate, basePath]);

  return <Outlet />;
};

const JoinClassRoute = () => {
  const { code } = useParams();
  const navigate = useNavigate();
  const { joinClass, getClassByInviteCode, setRole } = useClass();

  useEffect(() => {
    setRole("student");
    if (!code) {
      navigate("/education/student/classes", { replace: true });
      return;
    }
    const cls = getClassByInviteCode(code);
    if (!cls) {
      navigate("/education/student/classes", { replace: true });
      return;
    }
    joinClass(code);
    navigate(`/education/student/classes/${cls.id}/dashboard`, { replace: true });
  }, [code, joinClass, getClassByInviteCode, navigate, setRole]);

  return null;
};

export const educationRoutes = (
  <>
    <Route path="/education" element={<EducationRoleSelect />} />
    <Route path="/join/class/:code" element={<JoinClassRoute />} />

    <Route path="/education/teacher/classes" element={<ClassList role="teacher" />} />
    <Route path="/education/teacher/classes/:classId" element={<ClassGate role="teacher" />}>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<TeacherDashboard />} />
      <Route path="class" element={<TeacherClasses />} />
      <Route path="lecture" element={<TeacherLectures />} />
      <Route path="assignments" element={<TeacherAssignments />} />
      <Route path="lecture/:lectureId/summary" element={<LectureSummary />} />
      <Route path="lecture/:lectureId/meeting" element={<MeetingDetails role="teacher" />} />
      <Route path="students" element={<TeacherStudents />} />
      <Route path="calendar" element={<TeacherCalendar />} />
      <Route path="settings" element={<TeacherSettings />} />
    </Route>

    <Route path="/education/student/classes" element={<ClassList role="student" />} />
    <Route path="/education/student/classes/:classId" element={<ClassGate role="student" />}>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<StudentDashboard />} />
      <Route path="my-class" element={<StudentClasses />} />
      <Route path="todo-list" element={<StudentTodo />} />
      <Route path="lecture-notes" element={<StudentNotes />} />
      <Route path="lecture/:lectureId/meeting" element={<MeetingDetails role="student" />} />
      <Route path="calendar" element={<StudentCalendar />} />
    </Route>
  </>
);
