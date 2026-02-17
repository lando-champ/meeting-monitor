import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  Users, 
  BarChart3, 
  Settings,
  Plus,
  Video,
  Clock,
  CheckCircle2,
  Play,
  Upload
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import UploadMeeting from '@/components/meetings/UploadMeeting';
import { mockMeetings } from '@/data/mockData';
import { format, isSameDay } from 'date-fns';
import { cn } from '@/lib/utils';
import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { Calendar as CalendarPicker } from '@/components/ui/calendar';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Meeting } from '@/lib/types';
import { loadWorkspaceMeetings, saveWorkspaceMeetings } from '@/lib/workspaceStorage';

const ManagerMeetings = () => {
  const { workspaceId = "alpha" } = useParams();
  const navigate = useNavigate();
  const basePath = `/business/manager/workspaces/${workspaceId}`;
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [meetingTime, setMeetingTime] = useState("");
  const [meetingDescription, setMeetingDescription] = useState("");
  const [joinLink, setJoinLink] = useState("");
  const [joinId, setJoinId] = useState("");
  const [joinError, setJoinError] = useState("");
  const [scheduleError, setScheduleError] = useState("");

  useEffect(() => {
    const scheduled = mockMeetings.filter((meeting) => meeting.status === 'scheduled');
    setMeetings(loadWorkspaceMeetings(workspaceId, scheduled));
  }, [workspaceId]);

  useEffect(() => {
    if (meetings.length) {
      saveWorkspaceMeetings(workspaceId, meetings);
    }
  }, [meetings, workspaceId]);

  const scheduledMeetings = useMemo(
    () => meetings.filter((meeting) => meeting.status === 'scheduled'),
    [meetings],
  );
  const liveMeetings = useMemo(
    () => mockMeetings.filter((meeting) => meeting.status === 'live'),
    [],
  );
  const completedMeetings = useMemo(
    () => mockMeetings.filter((meeting) => meeting.status === 'completed'),
    [],
  );
  const allCalendarMeetings = useMemo(
    () => [...scheduledMeetings, ...liveMeetings],
    [scheduledMeetings, liveMeetings],
  );
  const meetingsForSelectedDate = useMemo(() => {
    if (!selectedDate) {
      return [];
    }
    return allCalendarMeetings.filter((meeting) => isSameDay(meeting.startTime, selectedDate));
  }, [allCalendarMeetings, selectedDate]);

  const handleSchedule = () => {
    if (!meetingTitle.trim() || !meetingDate || !meetingTime) {
      setScheduleError("Title, date, and time are required.");
      return;
    }
    const start = new Date(`${meetingDate}T${meetingTime}`);
    if (Number.isNaN(start.getTime())) {
      setScheduleError("Enter a valid date and time.");
      return;
    }
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const newMeeting: Meeting = {
      id: `mtg-${Date.now()}`,
      title: meetingTitle.trim(),
      description: meetingDescription.trim(),
      startTime: start,
      endTime: end,
      status: 'scheduled',
      participants: mockMeetings[0]?.participants ?? [],
    };
    setMeetings((prev) => [...prev, newMeeting]);
    setMeetingTitle("");
    setMeetingDate("");
    setMeetingTime("");
    setMeetingDescription("");
    setScheduleError("");
    setScheduleOpen(false);
  };

  const handleJoin = () => {
    if (!joinLink.trim() && !joinId.trim()) {
      setJoinError("Enter a meeting link or meeting ID.");
      return;
    }
    if (joinLink.trim() && !/^https?:\/\//i.test(joinLink.trim())) {
      setJoinError("Meeting link must start with http:// or https://");
      return;
    }
    setJoinError("");
    setJoinOpen(false);
    if (joinLink.trim()) {
      window.open(joinLink.trim(), "_blank", "noopener,noreferrer");
    }
  };
  const managerSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar, badge: 3 },
    { title: 'Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 5 },
    { title: 'Kanban Board', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Team', href: `${basePath}/team`, icon: Users },
    { title: 'Analytics', href: `${basePath}/analytics`, icon: BarChart3, isPremium: true },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  return (
    <DashboardLayout
      sidebarItems={managerSidebarItems}
      sidebarTitle="Manager"
      sidebarSubtitle="Business Dashboard"
      userName="Sarah Chen"
      userRole="Product Manager"
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Meetings</h1>
            <p className="text-muted-foreground">
              Schedule, join, or upload meeting recordings for AI analysis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <Video className="h-4 w-4 mr-2" />
                  Join Meeting
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Join a meeting</DialogTitle>
                  <DialogDescription>Enter a meeting link or ID.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <Label htmlFor="join-link">Meeting Link</Label>
                  <Input
                    id="join-link"
                    placeholder="https://meeting-link.com/room"
                    value={joinLink}
                    onChange={(event) => {
                      setJoinLink(event.target.value);
                      setJoinError("");
                    }}
                  />
                  <Label htmlFor="join-id">Meeting ID</Label>
                  <Input
                    id="join-id"
                    placeholder="Meeting ID"
                    value={joinId}
                    onChange={(event) => {
                      setJoinId(event.target.value);
                      setJoinError("");
                    }}
                  />
                  {joinError && <p className="text-sm text-destructive">{joinError}</p>}
                </div>
                <DialogFooter>
                  <Button variant="secondary" onClick={handleJoin}>
                    Join Meeting
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Schedule Meeting
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Schedule a meeting</DialogTitle>
                  <DialogDescription>
                    Provide a title, date, and time to schedule a meeting.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <Label htmlFor="meeting-title">Title</Label>
                  <Input
                    id="meeting-title"
                    placeholder="Weekly Standup"
                    value={meetingTitle}
                    onChange={(event) => {
                      setMeetingTitle(event.target.value);
                      setScheduleError("");
                    }}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-2">
                      <Label htmlFor="meeting-date">Date</Label>
                      <Input
                        id="meeting-date"
                        type="date"
                        value={meetingDate}
                        onChange={(event) => {
                          setMeetingDate(event.target.value);
                          setScheduleError("");
                        }}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="meeting-time">Time</Label>
                      <Input
                        id="meeting-time"
                        type="time"
                        value={meetingTime}
                        onChange={(event) => {
                          setMeetingTime(event.target.value);
                          setScheduleError("");
                        }}
                      />
                    </div>
                  </div>
                  <Label htmlFor="meeting-description">Description</Label>
                  <Textarea
                    id="meeting-description"
                    placeholder="Discuss goals and blockers..."
                    value={meetingDescription}
                    onChange={(event) => setMeetingDescription(event.target.value)}
                  />
                  {scheduleError && <p className="text-sm text-destructive">{scheduleError}</p>}
                </div>
                <DialogFooter>
                  <Button variant="secondary" onClick={handleSchedule}>
                    Schedule
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Upload Section */}
          <UploadMeeting variant="corporate" title="Upload Meeting Recording" />

          {/* Upcoming Meetings */}
          <Card className="shadow-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-primary" />
                  Upcoming Meetings
                </CardTitle>
                <Dialog open={calendarOpen} onOpenChange={setCalendarOpen}>
                  <DialogTrigger asChild>
                    <Button variant="ghost" size="sm">
                      View Calendar
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>Meeting Calendar</DialogTitle>
                      <DialogDescription>
                        View scheduled and live meetings.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid md:grid-cols-[300px_1fr] gap-4">
                      <CalendarPicker
                        mode="single"
                        selected={selectedDate}
                        onSelect={setSelectedDate}
                        modifiers={{
                          hasMeeting: allCalendarMeetings.map((meeting) => meeting.startTime),
                        }}
                        modifiersClassNames={{
                          hasMeeting: "bg-primary/15 text-primary font-semibold",
                        }}
                      />
                      <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                          {selectedDate ? format(selectedDate, 'MMMM d, yyyy') : 'Select a date'}
                        </p>
                        {meetingsForSelectedDate.length === 0 && (
                          <p className="text-sm text-muted-foreground">No meetings scheduled.</p>
                        )}
                        {meetingsForSelectedDate.map((meeting) => (
                          <div key={meeting.id} className="p-3 border rounded-lg">
                            <p className="font-medium">{meeting.title}</p>
                            <p className="text-sm text-muted-foreground">
                              {format(meeting.startTime, 'h:mm a')} • {meeting.status}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
              <CardDescription>Your scheduled meetings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {scheduledMeetings.slice(0, 3).map((meeting) => (
                <div key={meeting.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Video className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{meeting.title}</p>
                      <p className="text-sm text-muted-foreground flex items-center gap-2">
                        <Clock className="h-3 w-3" />
                        {format(meeting.startTime, 'MMM d, h:mm a')}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(`${basePath}/meeting/${meeting.id}`)}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Join
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Meeting History */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Meeting History</CardTitle>
            <CardDescription>Past meetings with AI-generated summaries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {completedMeetings.map((meeting) => (
                <div key={meeting.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer">
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "h-10 w-10 rounded-lg flex items-center justify-center",
                      "bg-success/10"
                    )}>
                      <CheckCircle2 className="h-5 w-5 text-success" />
                    </div>
                    <div>
                      <p className="font-medium">{meeting.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {format(meeting.startTime, 'MMMM d, yyyy • h:mm a')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex -space-x-2">
                      {meeting.participants.slice(0, 3).map((p) => (
                        <Avatar key={p.id} className="h-8 w-8 border-2 border-background">
                          <AvatarImage src={p.avatar} />
                          <AvatarFallback className="text-xs">
                            {p.name.split(' ').map(n => n[0]).join('')}
                          </AvatarFallback>
                        </Avatar>
                      ))}
                      {meeting.participants.length > 3 && (
                        <div className="h-8 w-8 rounded-full bg-muted border-2 border-background flex items-center justify-center text-xs font-medium">
                          +{meeting.participants.length - 3}
                        </div>
                      )}
                    </div>
                    <Badge variant="secondary">
                      {meeting.actionItems?.length || 0} tasks
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`${basePath}/meeting/${meeting.id}`)}
                    >
                      View Summary
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default ManagerMeetings;
