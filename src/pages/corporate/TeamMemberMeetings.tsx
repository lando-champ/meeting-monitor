import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  FileText,
  Video,
  Clock,
  CheckCircle2,
  Play,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import UploadMeeting from '@/components/meetings/UploadMeeting';
import { mockMeetings } from '@/data/mockData';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { listMeetings, createMeeting, startMeeting, type MeetingBotListItem } from '@/lib/api';
import { useCallback, useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const TeamMemberMeetings = () => {
  const { workspaceId = "alpha" } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const basePath = `/business/member/workspaces/${workspaceId}`;
  const [botMeetings, setBotMeetings] = useState<MeetingBotListItem[]>([]);
  const [botMeetingsLoading, setBotMeetingsLoading] = useState(false);
  const [liveBotOpen, setLiveBotOpen] = useState(false);
  const [liveBotTitle, setLiveBotTitle] = useState('');
  const [liveBotUrl, setLiveBotUrl] = useState('');
  const [liveBotError, setLiveBotError] = useState('');
  const [liveBotStarting, setLiveBotStarting] = useState(false);

  const fetchBotMeetings = useCallback(async () => {
    if (!token || !workspaceId) return;
    setBotMeetingsLoading(true);
    try {
      const { meetings: list } = await listMeetings(token, workspaceId);
      setBotMeetings(list);
    } catch {
      setBotMeetings([]);
    } finally {
      setBotMeetingsLoading(false);
    }
  }, [token, workspaceId]);

  useEffect(() => {
    fetchBotMeetings();
  }, [fetchBotMeetings]);

  const handleStartLiveMeeting = async () => {
    if (!token || !liveBotUrl.trim()) {
      setLiveBotError('Meeting URL is required (e.g. Jitsi Meet link).');
      return;
    }
    const url = liveBotUrl.trim();
    if (!/^https?:\/\//i.test(url)) {
      setLiveBotError('URL must start with http:// or https://');
      return;
    }
    setLiveBotError('');
    setLiveBotStarting(true);
    try {
      const { id } = await createMeeting(token, {
        project_id: workspaceId,
        title: liveBotTitle.trim() || 'Live Meeting',
        meeting_url: url,
      });
      await startMeeting(token, id, { meeting_url: url, project_id: workspaceId, title: liveBotTitle.trim() || 'Live Meeting' });
      setLiveBotOpen(false);
      setLiveBotTitle('');
      setLiveBotUrl('');
      navigate(`${basePath}/meeting/${id}`);
    } catch (e) {
      setLiveBotError(e instanceof Error ? e.message : 'Failed to start meeting');
    } finally {
      setLiveBotStarting(false);
    }
  };
  const teamMemberSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar },
    { title: 'My Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 3 },
    { title: 'Kanban', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Documents', href: `${basePath}/documents`, icon: FileText },
  ];
  return (
    <DashboardLayout
      sidebarItems={teamMemberSidebarItems}
      sidebarTitle="Team Member"
      sidebarSubtitle="Personal Workspace"
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Meetings</h1>
            <p className="text-muted-foreground">
              Join meetings or upload recordings for AI analysis
            </p>
          </div>
          <Button onClick={() => navigate(`${basePath}/meetings`)}>
            <Video className="h-4 w-4 mr-2" />
            Join Meeting
          </Button>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Upload Section */}
          <UploadMeeting variant="corporate" title="Upload Meeting Recording" />

          {/* Upcoming Meetings */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-primary" />
                Upcoming Meetings
              </CardTitle>
              <CardDescription>Meetings you're invited to</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockMeetings.filter(m => m.status === 'scheduled').slice(0, 3).map((meeting) => (
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
              {mockMeetings.filter(m => m.status === 'completed').map((meeting) => (
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

export default TeamMemberMeetings;
