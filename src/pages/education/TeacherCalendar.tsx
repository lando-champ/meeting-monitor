import {
  LayoutDashboard,
  BookOpen,
  Video,
  FileText,
  Users,
  Settings,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SidebarItem } from "@/components/layout/Sidebar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameDay,
  isToday,
  addMonths,
  subMonths,
} from "date-fns";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useParams, useNavigate } from "react-router-dom";
import { useEducation } from "@/context/EducationContext";
import { useClass } from "@/context/ClassContext";

const TeacherCalendar = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/teacher/classes/${classId}`;
  const { classes } = useClass();
  const { getLecturesByClass, getAssignmentsByClass } = useEducation();

  const allLectures = classes.flatMap((cls) =>
    getLecturesByClass(cls.id).map((l) => ({
      ...l,
      type: "class" as const,
      classCode: cls.inviteCode,
      date: new Date(`${l.date}T${l.time || "00:00"}`),
    }))
  );

  const allAssignments = classes.flatMap((cls) =>
    getAssignmentsByClass(cls.id).map((a) => ({
      ...a,
      type: "deadline" as const,
      classCode: cls.inviteCode,
      date: new Date(a.dueDate + "T23:59:00"),
    }))
  );

  const events = [
    ...allLectures.map((l) => ({
      id: l.id,
      title: l.title,
      date: l.date,
      type: "class" as const,
      class: l.classCode,
      lecture: l,
    })),
    ...allAssignments.map((a) => ({
      id: a.id,
      title: a.title,
      date: a.date,
      type: "deadline" as const,
      class: a.classCode,
    })),
  ].sort((a, b) => a.date.getTime() - b.date.getTime());

  const teacherSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "Class", href: `${basePath}/class`, icon: BookOpen },
    { title: "Lecture", href: `${basePath}/lecture`, icon: Video, badge: 2 },
    { title: "Assignments", href: `${basePath}/assignments`, icon: FileText, badge: 5 },
    { title: "Students", href: `${basePath}/students`, icon: Users },
    { title: "Calendar", href: `${basePath}/calendar`, icon: Calendar },
    { title: "Settings", href: `${basePath}/settings`, icon: Settings },
  ];

  const [currentMonth, setCurrentMonth] = useState(new Date());

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

  const getEventsForDay = (day: Date) => {
    return events.filter((event) => isSameDay(event.date, day));
  };

  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
      userName="Prof. James Wilson"
      userRole="Computer Science"
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Calendar</h1>
          <p className="text-muted-foreground">
            View your scheduled meets and assignment deadlines
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          <Card className="shadow-card lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{format(currentMonth, "MMMM yyyy")}</CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-1 mb-2">
                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
                  (day) => (
                    <div
                      key={day}
                      className="text-center text-sm font-medium text-muted-foreground p-2"
                    >
                      {day}
                    </div>
                  )
                )}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: monthStart.getDay() }).map((_, i) => (
                  <div key={`empty-${i}`} className="aspect-square p-2" />
                ))}

                {days.map((day) => {
                  const dayEvents = getEventsForDay(day);
                  const hasClass = dayEvents.some((e) => e.type === "class");
                  const hasDeadline = dayEvents.some((e) => e.type === "deadline");

                  return (
                    <div
                      key={day.toISOString()}
                      className={cn(
                        "aspect-square p-1 border rounded-lg hover:bg-muted/50",
                        isToday(day) && "border-primary bg-primary/5"
                      )}
                    >
                      <div className="h-full flex flex-col">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            isToday(day) && "text-primary"
                          )}
                        >
                          {format(day, "d")}
                        </span>
                        <div className="flex-1 flex flex-col gap-0.5 mt-1 overflow-hidden">
                          {hasClass && (
                            <div className="h-1.5 w-full rounded bg-secondary" />
                          )}
                          {hasDeadline && (
                            <div className="h-1.5 w-full rounded bg-destructive" />
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center gap-6 mt-4 pt-4 border-t text-sm">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-secondary" />
                  <span className="text-muted-foreground">Class / Meet</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-destructive" />
                  <span className="text-muted-foreground">Deadline</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Upcoming Meets
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {events
                .filter((e) => e.type === "class" && e.date >= new Date())
                .slice(0, 8)
                .map((event) =>
                  event.type === "class" && "lecture" in event ? (
                    <div
                      key={event.id}
                      className="p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                      onClick={() =>
                        navigate(
                          `/education/teacher/classes/${event.lecture.classId}/lecture/${event.lecture.id}/meeting`
                        )
                      }
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-[10px]">
                          {event.lecture.status}
                        </Badge>
                        <Badge variant="outline" className="text-[10px]">
                          {event.class}
                        </Badge>
                      </div>
                      <p className="font-medium text-sm">{event.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {format(event.date, "EEE, MMM d • h:mm a")}
                      </p>
                    </div>
                  ) : null
                )}
              {events.filter(
                (e) => e.type === "class" && e.date >= new Date()
              ).length === 0 && (
                <p className="text-sm text-muted-foreground py-4">
                  No upcoming meets.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default TeacherCalendar;
