import {
  LayoutDashboard,
  BookOpen,
  ListTodo,
  FileText,
  Calendar,
  Search,
  Sparkles,
  Clock,
  CheckCircle2,
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
import { Input } from "@/components/ui/input";
import UploadMeeting from "@/components/meetings/UploadMeeting";
import { format } from "date-fns";
import { useParams, useNavigate } from "react-router-dom";
import { useEducation } from "@/context/EducationContext";
import { useClass } from "@/context/ClassContext";

const StudentNotes = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/student/classes/${classId}`;
  const { classes } = useClass();
  const { getLecturesByClass } = useEducation();

  const allLectures = classes.flatMap((cls) =>
    getLecturesByClass(cls.id)
      .filter((l) => l.status === "completed" && (l.summary || l.transcript))
      .map((l) => ({ ...l, classCode: cls.inviteCode }))
  );

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
          <h1 className="text-2xl font-bold">Lecture Notes</h1>
          <p className="text-muted-foreground">
            AI-generated notes and transcripts from your lectures
          </p>
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search notes..." className="pl-10" />
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <UploadMeeting variant="education" title="Upload Lecture Recording" />

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-secondary" />
                Recent Notes
              </CardTitle>
              <CardDescription>Latest lecture summaries</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {allLectures.slice(0, 3).map((note) => (
                <div
                  key={note.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                  onClick={() =>
                    navigate(
                      `/education/student/classes/${note.classId}/lecture/${note.id}/meeting`
                    )
                  }
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
                      <CheckCircle2 className="h-5 w-5 text-success" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{note.title}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          {note.classCode}
                        </Badge>
                        <Clock className="h-3 w-3" />
                        {format(new Date(note.date), "MMM d")}
                      </p>
                    </div>
                  </div>
                  {note.summary && (
                    <Badge variant="secondary" className="text-[10px]">
                      <Sparkles className="h-2 w-2 mr-1" />
                      AI Summary
                    </Badge>
                  )}
                </div>
              ))}
              {allLectures.length === 0 && (
                <p className="text-sm text-muted-foreground py-4">
                  No lecture notes yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>All Lecture Notes</CardTitle>
            <CardDescription>
              Complete archive of your lecture transcripts and summaries
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {allLectures.map((note) => (
                <div
                  key={note.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
                      <CheckCircle2 className="h-5 w-5 text-success" />
                    </div>
                    <div>
                      <p className="font-medium">{note.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {note.classCode} • {format(new Date(note.date), "MMMM d, yyyy")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {note.transcript && note.transcript.length > 0 && (
                      <Badge variant="outline" className="text-xs">
                        Transcript
                      </Badge>
                    )}
                    {note.summary && (
                      <Badge variant="secondary" className="text-xs">
                        <Sparkles className="h-2 w-2 mr-1" />
                        AI Summary
                      </Badge>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        navigate(
                          `/education/student/classes/${note.classId}/lecture/${note.id}/meeting`
                        )
                      }
                    >
                      View Notes
                    </Button>
                  </div>
                </div>
              ))}
              {allLectures.length === 0 && (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No lecture notes yet.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default StudentNotes;
