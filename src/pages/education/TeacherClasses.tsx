import {
  LayoutDashboard,
  BookOpen,
  Video,
  FileText,
  Users,
  Settings,
  Calendar,
  Plus,
  MoreHorizontal,
  Clock,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SidebarItem } from "@/components/layout/Sidebar";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useParams, useNavigate } from "react-router-dom";
import { useClass } from "@/context/ClassContext";
import { useEducation } from "@/context/EducationContext";

const TeacherClasses = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/teacher/classes/${classId}`;
  const { classes } = useClass();
  const { getLecturesByClass } = useEducation();

  const teacherSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "Class", href: `${basePath}/class`, icon: BookOpen },
    { title: "Lecture", href: `${basePath}/lecture`, icon: Video, badge: 2 },
    { title: "Assignments", href: `${basePath}/assignments`, icon: FileText, badge: 5 },
    { title: "Students", href: `${basePath}/students`, icon: Users },
    { title: "Calendar", href: `${basePath}/calendar`, icon: Calendar },
    { title: "Settings", href: `${basePath}/settings`, icon: Settings },
  ];

  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Classes</h1>
            <p className="text-muted-foreground">
              Manage your classes and schedules
            </p>
          </div>
          <Button onClick={() => navigate("/education/teacher/classes")}>
            <Plus className="h-4 w-4 mr-2" />
            Create Class
          </Button>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {classes.map((cls) => {
            const classLectures = getLecturesByClass(cls.id);
            const nextLecture =
              classLectures.find((l) => l.status === "live") ||
              classLectures.find((l) => l.status === "scheduled");
            const completedCount = classLectures.filter(
              (l) => l.status === "completed"
            ).length;
            const progress = classLectures.length
              ? Math.min(100, (completedCount / classLectures.length) * 100)
              : 0;

            return (
              <Card
                key={cls.id}
                className="shadow-card hover:shadow-hover transition-shadow"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <Badge variant="secondary" className="mb-2">
                        {cls.inviteCode}
                      </Badge>
                      <CardTitle className="text-lg">{cls.name}</CardTitle>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => navigate(`/education/teacher/classes/${cls.id}`)}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground flex items-center gap-2">
                      <Users className="h-4 w-4" />
                      {cls.studentCount} students
                    </span>
                    <span className="text-muted-foreground flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      {nextLecture
                        ? `${nextLecture.date} ${nextLecture.time}`
                        : "No session"}
                    </span>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Course Progress</span>
                      <span className="font-medium">{Math.round(progress)}%</span>
                    </div>
                    <Progress value={progress} className="h-2" />
                  </div>

                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() =>
                        navigate(`/education/teacher/classes/${cls.id}/dashboard`)
                      }
                    >
                      View Class
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex-1"
                      onClick={() => {
                        if (nextLecture) {
                          navigate(
                            `/education/teacher/classes/${cls.id}/lecture/${nextLecture.id}/meeting`
                          );
                        } else {
                          navigate(
                            `/education/teacher/classes/${cls.id}/lecture`
                          );
                        }
                      }}
                    >
                      Start Session
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default TeacherClasses;
