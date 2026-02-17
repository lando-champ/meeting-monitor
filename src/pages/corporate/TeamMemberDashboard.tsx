import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Radio,
  Upload
} from 'lucide-react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { mockMeetings, mockTasks, getTaskStats } from '@/data/mockData';
import { format, formatDistanceToNow } from 'date-fns';

const TeamMemberDashboard = () => {
  const { workspaceId = "alpha" } = useParams();
  const navigate = useNavigate();
  const basePath = `/business/member/workspaces/${workspaceId}`;
  const teamMemberSidebarItems: SidebarItem[] = [
    { title: 'My Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar, badge: 2 },
    { title: 'My Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 4 },
    { title: 'Kanban', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Documents', href: `${basePath}/documents`, icon: FileText },
  ];
  const taskStats = getTaskStats();
  const myTasks = mockTasks.slice(0, 5);
  const liveMeeting = mockMeetings.find(m => m.status === 'live');
  const upcomingMeetings = mockMeetings.filter(m => m.status === 'scheduled').slice(0, 3);
  const completedMeetings = mockMeetings.filter(m => m.status === 'completed' && m.summary).slice(0, 2);

  const completedTasks = myTasks.filter(t => t.status === 'done').length;
  const totalTasks = myTasks.length;
  const progressPercent = (completedTasks / totalTasks) * 100;

  return (
    <DashboardLayout
      sidebarItems={teamMemberSidebarItems}
      sidebarTitle="Team Member"
      sidebarSubtitle="Business Dashboard"
      userName="Michael Park"
      userRole="Senior Developer"
      userAvatar="https://api.dicebear.com/7.x/avataaars/svg?seed=Michael"
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Good morning, Michael</h1>
            <p className="text-muted-foreground">You have {taskStats.inProgress + taskStats.todo} tasks to work on today.</p>
          </div>
          <Link to={`${basePath}/meetings`}>
            <Button variant="outline">
              <Upload className="h-4 w-4 mr-2" />
              Upload Recording
            </Button>
          </Link>
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

        {/* Progress Card */}
        <Card className="shadow-card bg-gradient-to-r from-primary/5 to-secondary/5">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-muted-foreground">My Progress This Week</p>
                <p className="text-2xl font-bold">{completedTasks} of {totalTasks} tasks completed</p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-primary">{Math.round(progressPercent)}%</p>
                <p className="text-sm text-muted-foreground">completion rate</p>
              </div>
            </div>
            <Progress value={progressPercent} className="h-3" />
          </CardContent>
        </Card>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* My Tasks */}
          <Card className="shadow-card lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>My Tasks</CardTitle>
                <CardDescription>Tasks assigned to you from meetings</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`${basePath}/tasks`)}
              >
                View All
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {myTasks.map((task) => (
                  <div 
                    key={task.id} 
                    className="flex items-start gap-3 p-3 rounded-lg border hover:shadow-sm transition-shadow"
                  >
                    <Checkbox 
                      checked={task.status === 'done'} 
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className={`font-medium ${task.status === 'done' ? 'line-through text-muted-foreground' : ''}`}>
                          {task.title}
                        </p>
                        {task.isAutoGenerated && (
                          <Badge variant="outline" className="text-xs bg-secondary/10 border-secondary/30 text-secondary">
                            <Sparkles className="h-2.5 w-2.5 mr-1" />
                            AI
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {task.dueDate ? formatDistanceToNow(task.dueDate, { addSuffix: true }) : 'No deadline'}
                        </span>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${
                            task.priority === 'urgent' ? 'border-destructive text-destructive' :
                            task.priority === 'high' ? 'border-warning text-warning' :
                            'border-muted-foreground'
                          }`}
                        >
                          {task.priority}
                        </Badge>
                        <Badge 
                          variant="secondary" 
                          className={`text-xs ${
                            task.status === 'done' ? 'bg-success/10 text-success' :
                            task.status === 'in-progress' ? 'bg-primary/10 text-primary' :
                            task.status === 'blocked' ? 'bg-destructive/10 text-destructive' :
                            ''
                          }`}
                        >
                          {task.status.replace('-', ' ')}
                        </Badge>
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Upcoming Meetings */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Upcoming Meetings</CardTitle>
              <CardDescription>Your schedule for today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {upcomingMeetings.map((meeting) => (
                  <div key={meeting.id} className="p-3 rounded-lg border">
                    <p className="font-medium text-sm mb-1">{meeting.title}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                      <Clock className="h-3 w-3" />
                      {format(meeting.startTime, 'h:mm a')}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {meeting.participants.length} participants
                    </p>
                  </div>
                ))}
                <Button variant="outline" className="w-full" size="sm">
                  <Calendar className="h-4 w-4 mr-2" />
                  View Full Schedule
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Meeting Summaries */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-secondary" />
                Recent Meeting Summaries
              </CardTitle>
              <CardDescription>AI-generated notes from your meetings</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate(`${basePath}/meetings`)}>
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              {completedMeetings.map((meeting) => (
                <div key={meeting.id} className="p-4 rounded-lg border">
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-medium">{meeting.title}</p>
                    <Badge variant="outline" className="text-xs">
                      {format(meeting.startTime, 'MMM d')}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {meeting.summary?.overview}
                  </p>
                  
                  {/* My Action Items */}
                  <div className="mb-3">
                    <p className="text-xs font-medium text-muted-foreground mb-2">My Action Items:</p>
                    <div className="space-y-1">
                      {meeting.summary?.actionItems.slice(0, 2).map((item, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                          <span className="line-clamp-1">{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <Button
                    variant="link"
                    size="sm"
                    className="h-auto p-0 text-primary"
                    onClick={() => navigate(`${basePath}/meeting/${meeting.id}`)}
                  >
                    View full notes →
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default TeamMemberDashboard;
