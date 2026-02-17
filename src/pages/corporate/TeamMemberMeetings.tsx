import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  FileText,
  Video,
  Clock,
  CheckCircle2,
  Play
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import UploadMeeting from '@/components/meetings/UploadMeeting';
import { mockMeetings } from '@/data/mockData';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { useParams, useNavigate } from 'react-router-dom';

const TeamMemberMeetings = () => {
  const { workspaceId = "alpha" } = useParams();
  const navigate = useNavigate();
  const basePath = `/business/member/workspaces/${workspaceId}`;
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
      userName="Alex Kim"
      userRole="Software Engineer"
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
