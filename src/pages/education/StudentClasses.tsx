import {
  LayoutDashboard,
  BookOpen,
  ListTodo,
  FileText,
  Calendar,
  Video,
  Clock,
  Play,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SidebarItem } from "@/components/layout/Sidebar";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import UploadMeeting from "@/components/meetings/UploadMeeting";
import { format } from "date-fns";
import { useParams, useNavigate } from "react-router-dom";
import { useClass } from "@/context/ClassContext";
import { useEducation } from "@/context/EducationContext";

const StudentClasses = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/student/classes/${classId}`;
  const { classes } = useClass();
  const { getLecturesByClass } = useEducation();
  const enrolledClasses = classes.filter((cls) => cls.students.includes("emma.thompson@university.edu"));

  const getMeetingLinkForClass = (clsId: string) => {
    const lectures = getLecturesByClass(clsId);
    const live = lectures.find((l) => l.status === "live");
    const next = lectures.find((l) => l.status === "scheduled");
    return (live || next)?.meetingLink;
  };

  const getNextLectureForClass = (clsId: string) => {
    const lectures = getLecturesByClass(clsId);
    const live = lectures.find((l) => l.status === "live");
    const next = lectures.find((l) => l.status === "scheduled");
    return live || next;
  };

  const studentSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "My Class", href: `${basePath}/my-class`, icon: BookOpen },
    { title: "To-Do List", href: `${basePath}/todo-list`, icon: ListTodo, badge: 4 },
    { title: "Lecture Notes", href: `${basePath}/lecture-notes`, icon: FileText },
    { title: "Calendar", href: `${basePath}/calendar`, icon: Calendar },
  ];

  return (
    <DashboardLayout
      sidebarItems={studentSidebarItems}
      sidebarTitle="Student"
      sidebarSubtitle="Learning Dashboard"
      userName="Emma Thompson"
      userRole="Computer Science"
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">My Classes</h1>
          <p className="text-muted-foreground">
            View and join your enrolled classes
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <UploadMeeting variant="education" title="Upload Lecture Recording" />

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-secondary" />
                Enrolled Classes
              </CardTitle>
              <CardDescription>Your current courses</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(enrolledClasses.length > 0 ? enrolledClasses : classes).map((cls) => {
                const meetingLink = getMeetingLinkForClass(cls.id);
                const nextLecture = getNextLectureForClass(cls.id);
                return (
                  <div
                    key={cls.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary">{cls.inviteCode}</Badge>
                        <p className="font-medium">{cls.name}</p>
                      </div>
                      <p className="text-sm text-muted-foreground">{cls.description}</p>
                      {nextLecture && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                          <Clock className="h-3 w-3" />
                          {nextLecture.status === "live"
                            ? "Live now"
                            : `Next: ${nextLecture.date} at ${nextLecture.time}`}
                        </p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        nextLecture &&
                        navigate(
                          `/education/student/classes/${cls.id}/lecture/${nextLecture.id}/meeting`
                        )
                      }
                      disabled={!nextLecture}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Join
                    </Button>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default StudentClasses;
