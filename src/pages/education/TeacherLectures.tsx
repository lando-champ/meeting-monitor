import { useState } from "react";
import {
  LayoutDashboard,
  BookOpen,
  Video,
  FileText,
  Users,
  Settings,
  Plus,
  Clock,
  CheckCircle2,
  Play,
  ExternalLink,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import UploadMeeting from "@/components/meetings/UploadMeeting";
import { useParams, useNavigate } from "react-router-dom";
import { useEducation } from "@/context/EducationContext";
import type { MeetingPlatform } from "@/context/EducationContext";

const PLATFORMS: { value: MeetingPlatform; label: string }[] = [
  { value: "jitsi", label: "Jitsi Meet" },
  { value: "gmeet", label: "Google Meet" },
  { value: "zoom", label: "Zoom" },
  { value: "teams", label: "Microsoft Teams" },
];

const TeacherLectures = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/teacher/classes/${classId}`;
  const { getLecturesByClass, addLecture, addLiveSession } = useEducation();
  const classLectures = getLecturesByClass(classId);

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [liveSessionOpen, setLiveSessionOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    title: "",
    date: "",
    time: "",
    platform: "jitsi" as MeetingPlatform,
    meetingLink: "",
    description: "",
  });
  const [liveForm, setLiveForm] = useState({
    title: "",
    meetingLink: "",
    description: "",
  });

  const teacherSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "Class", href: `${basePath}/class`, icon: BookOpen },
    { title: "Lecture", href: `${basePath}/lecture`, icon: Video, badge: 2 },
    { title: "Assignments", href: `${basePath}/assignments`, icon: FileText, badge: 5 },
    { title: "Students", href: `${basePath}/students`, icon: Users },
    { title: "Settings", href: `${basePath}/settings`, icon: Settings },
  ];

  const handleScheduleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addLecture({
      title: scheduleForm.title,
      classId,
      className: "Class",
      date: scheduleForm.date,
      time: scheduleForm.time,
      meetingLink: scheduleForm.meetingLink,
      platform: scheduleForm.platform,
      description: scheduleForm.description,
      status: "scheduled",
    });
    setScheduleForm({ title: "", date: "", time: "", platform: "jitsi", meetingLink: "", description: "" });
    setScheduleOpen(false);
  };

  const handleLiveSessionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addLiveSession({
      title: liveForm.title,
      classId,
      className: "Class",
      date: new Date().toISOString().slice(0, 10),
      time: new Date().toTimeString().slice(0, 5),
      meetingLink: liveForm.meetingLink,
      platform: "jitsi",
      description: liveForm.description,
    });
    setLiveForm({ title: "", meetingLink: "", description: "" });
    setLiveSessionOpen(false);
  };

  const upcomingLectures = classLectures.filter((l) => l.status === "scheduled");
  const completedLectures = classLectures.filter((l) => l.status === "completed");

  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
      userName="Prof. James Wilson"
      userRole="Computer Science"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Lectures</h1>
            <p className="text-muted-foreground">
              Schedule live sessions or upload lecture recordings
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setLiveSessionOpen(true)}>
              <Video className="h-4 w-4 mr-2" />
              Start Live Session
            </Button>
            <Button onClick={() => setScheduleOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Schedule Class
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <UploadMeeting variant="education" title="Upload Lecture Recording" />

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="h-5 w-5 text-secondary" />
                Upcoming Sessions
              </CardTitle>
              <CardDescription>Your scheduled lectures</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {upcomingLectures.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">
                  No upcoming sessions. Schedule a class to get started.
                </p>
              ) : (
                upcomingLectures.map((lecture) => (
                  <div
                    key={lecture.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-secondary/10 flex items-center justify-center">
                        <Video className="h-5 w-5 text-secondary" />
                      </div>
                      <div>
                        <p className="font-medium">{lecture.title}</p>
                        <p className="text-sm text-muted-foreground flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {lecture.className}
                          </Badge>
                          <Clock className="h-3 w-3" />
                          {lecture.date} at {lecture.time}
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        navigate(`${basePath}/lecture/${lecture.id}/meeting`)
                      }
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Start Meeting
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Past Lectures</CardTitle>
            <CardDescription>Lectures with AI-generated summaries and assignments</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {completedLectures.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">
                  No past lectures yet.
                </p>
              ) : (
                completedLectures.map((lecture) => (
                  <div
                    key={lecture.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
                        <CheckCircle2 className="h-5 w-5 text-success" />
                      </div>
                      <div>
                        <p className="font-medium">{lecture.title}</p>
                        <p className="text-sm text-muted-foreground">
                          {lecture.className} • {lecture.date}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          navigate(
                            `/education/teacher/classes/${classId}/lecture/${lecture.id}/summary`
                          )
                        }
                      >
                        View Summary
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Schedule Class Dialog */}
      <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Class</DialogTitle>
            <DialogDescription>Create a new scheduled meeting for your class.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleScheduleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="title">Class Name</Label>
              <Input
                id="title"
                value={scheduleForm.title}
                onChange={(e) =>
                  setScheduleForm((p) => ({ ...p, title: e.target.value }))
                }
                placeholder="e.g. Introduction to Data Structures"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="date">Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={scheduleForm.date}
                  onChange={(e) =>
                    setScheduleForm((p) => ({ ...p, date: e.target.value }))
                  }
                  required
                />
              </div>
              <div>
                <Label htmlFor="time">Time</Label>
                <Input
                  id="time"
                  type="time"
                  value={scheduleForm.time}
                  onChange={(e) =>
                    setScheduleForm((p) => ({ ...p, time: e.target.value }))
                  }
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="platform">Meeting Platform</Label>
              <Select
                value={scheduleForm.platform}
                onValueChange={(v: MeetingPlatform) =>
                  setScheduleForm((p) => ({ ...p, platform: v }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORMS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="meetingLink">Meeting Link</Label>
              <Input
                id="meetingLink"
                value={scheduleForm.meetingLink}
                onChange={(e) =>
                  setScheduleForm((p) => ({ ...p, meetingLink: e.target.value }))
                }
                placeholder="https://meet.jit.si/your-room-name"
                required
              />
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={scheduleForm.description}
                onChange={(e) =>
                  setScheduleForm((p) => ({ ...p, description: e.target.value }))
                }
                placeholder="Brief description of the class/meeting"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setScheduleOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Schedule Class</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Start Live Session Dialog */}
      <Dialog open={liveSessionOpen} onOpenChange={setLiveSessionOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Start Live Session</DialogTitle>
            <DialogDescription>Begin an instant live meeting for your class.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleLiveSessionSubmit} className="space-y-4">
            <div>
              <Label htmlFor="live-title">Session Name</Label>
              <Input
                id="live-title"
                value={liveForm.title}
                onChange={(e) =>
                  setLiveForm((p) => ({ ...p, title: e.target.value }))
                }
                placeholder="e.g. Live Q&A - Data Structures"
                required
              />
            </div>
            <div>
              <Label htmlFor="live-link">Meeting Link</Label>
              <Input
                id="live-link"
                value={liveForm.meetingLink}
                onChange={(e) =>
                  setLiveForm((p) => ({ ...p, meetingLink: e.target.value }))
                }
                placeholder="https://meet.jit.si/your-room-name"
                required
              />
            </div>
            <div>
              <Label htmlFor="live-desc">Description</Label>
              <Textarea
                id="live-desc"
                value={liveForm.description}
                onChange={(e) =>
                  setLiveForm((p) => ({ ...p, description: e.target.value }))
                }
                placeholder="Brief description of the live session"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setLiveSessionOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Start Live Session</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default TeacherLectures;
