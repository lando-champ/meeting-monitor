import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  Users, 
  BarChart3, 
  Settings,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  AlertCircle,
  Radio,
  ArrowUpRight,
  Sparkles,
  Upload,
  Video
} from 'lucide-react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import UploadMeeting from '@/components/meetings/UploadMeeting';
import { mockTeamMembers, mockMeetings, mockTasks, getTaskStats, mockTeamAnalytics } from '@/data/mockData';
import { format } from 'date-fns';

const ManagerDashboard = () => {
  const { workspaceId = "alpha" } = useParams();
  const navigate = useNavigate();
  const basePath = `/business/manager/workspaces/${workspaceId}`;
  const managerSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar, badge: 3 },
    { title: 'Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 5 },
    { title: 'Kanban Board', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Team', href: `${basePath}/team`, icon: Users },
    { title: 'Analytics', href: `${basePath}/analytics`, icon: BarChart3, isPremium: true },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  const taskStats = getTaskStats();
  const liveMeeting = mockMeetings.find(m => m.status === 'live');
  const upcomingMeetings = mockMeetings.filter(m => m.status === 'scheduled').slice(0, 3);

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
            <h1 className="text-2xl font-bold">Welcome back, Sarah</h1>
            <p className="text-muted-foreground">Here's what's happening with your team today.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link to={`${basePath}/meetings`}>
              <Button variant="outline">
                <Upload className="h-4 w-4 mr-2" />
                Upload Recording
              </Button>
            </Link>
            <Link to={`${basePath}/meetings`}>
              <Button className="gradient-primary">
                <Calendar className="h-4 w-4 mr-2" />
                Schedule Meeting
              </Button>
            </Link>
          </div>
        </div>

        {/* Live Meeting Banner */}
        {liveMeeting && (
          <Card className="border-success/30 bg-success/5">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-success/20 flex items-center justify-center">
                    <Radio className="h-5 w-5 text-success animate-pulse" />
                  </div>
                  <div>
                    <p className="font-medium">{liveMeeting.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {liveMeeting.participants.length} participants • Live now
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="border-success text-success hover:bg-success/10"
                  onClick={() => navigate(`${basePath}/meeting/${liveMeeting.id}`)}
                >
                  Join Meeting
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-4">
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Team Score</p>
                  <p className="text-3xl font-bold">{mockTeamAnalytics.teamScore}%</p>
                </div>
                <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                  mockTeamAnalytics.trend === 'up' ? 'bg-success/10' : 'bg-destructive/10'
                }`}>
                  {mockTeamAnalytics.trend === 'up' ? (
                    <TrendingUp className="h-5 w-5 text-success" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-destructive" />
                  )}
                </div>
              </div>
              <p className="text-xs text-success mt-2 flex items-center gap-1">
                <ArrowUpRight className="h-3 w-3" />
                +12% from last week
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Tasks In Progress</p>
                  <p className="text-3xl font-bold">{taskStats.inProgress}</p>
                </div>
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-primary" />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {taskStats.todo} pending • {taskStats.review} in review
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-3xl font-bold">{taskStats.done}</p>
                </div>
                <div className="h-10 w-10 rounded-full bg-success/10 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5 text-success" />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">This week</p>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Overdue</p>
                  <p className="text-3xl font-bold">{taskStats.overdue}</p>
                </div>
                <div className="h-10 w-10 rounded-full bg-destructive/10 flex items-center justify-center">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                </div>
              </div>
              <p className="text-xs text-destructive mt-2">Needs attention</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Team Overview */}
          <Card className="shadow-card lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Team Overview</CardTitle>
                <CardDescription>Your team's current status and performance</CardDescription>
              </div>
              <Link to={`${basePath}/team`}>
                <Button variant="ghost" size="sm">View All</Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockTeamMembers.map((member) => (
                  <div key={member.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={member.avatar} alt={member.name} />
                      <AvatarFallback>{member.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{member.name}</p>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${
                            member.status === 'active' ? 'border-success text-success' :
                            member.status === 'busy' ? 'border-warning text-warning' :
                            member.status === 'away' ? 'border-muted-foreground' : 'border-muted'
                          }`}
                        >
                          {member.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{member.role}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{member.productivityScore}%</p>
                      <p className="text-xs text-muted-foreground">
                        {member.tasksCompleted}/{member.totalTasks} tasks
                      </p>
                    </div>
                    <Progress 
                      value={(member.tasksCompleted / member.totalTasks) * 100} 
                      className="w-20 h-2"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Upcoming Meetings */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Upcoming Meetings</CardTitle>
              <CardDescription>Scheduled for today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {upcomingMeetings.map((meeting) => (
                  <div key={meeting.id} className="p-3 rounded-lg border bg-card hover:shadow-sm transition-shadow">
                    <p className="font-medium text-sm mb-1">{meeting.title}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                      <Clock className="h-3 w-3" />
                      {format(meeting.startTime, 'h:mm a')}
                    </div>
                    <div className="flex -space-x-2">
                      {meeting.participants.slice(0, 4).map((p) => (
                        <Avatar key={p.id} className="h-6 w-6 border-2 border-background">
                          <AvatarImage src={p.avatar} alt={p.name} />
                          <AvatarFallback className="text-[10px]">
                            {p.name.split(' ').map(n => n[0]).join('')}
                          </AvatarFallback>
                        </Avatar>
                      ))}
                      {meeting.participants.length > 4 && (
                        <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center text-[10px] font-medium border-2 border-background">
                          +{meeting.participants.length - 4}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <Button variant="outline" className="w-full" size="sm">
                  <Calendar className="h-4 w-4 mr-2" />
                  View Calendar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent AI Summaries */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-secondary" />
                Recent AI Summaries
              </CardTitle>
              <CardDescription>Auto-generated from your meetings</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate(`${basePath}/meetings`)}>
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              {mockMeetings.filter(m => m.summary).slice(0, 2).map((meeting) => (
                <div key={meeting.id} className="p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-medium">{meeting.title}</p>
                    <Badge variant="outline" className="text-xs">
                      {format(meeting.startTime, 'MMM d')}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {meeting.summary?.overview}
                  </p>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {meeting.summary?.keyPoints.slice(0, 2).map((point, i) => (
                      <Badge key={i} variant="secondary" className="text-xs font-normal">
                        {point.slice(0, 30)}...
                      </Badge>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{meeting.summary?.actionItems.length} action items</span>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 text-primary"
                      onClick={() => navigate(`${basePath}/meeting/${meeting.id}`)}
                    >
                      View full summary →
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

export default ManagerDashboard;
