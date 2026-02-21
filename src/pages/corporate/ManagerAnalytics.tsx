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
  Lock,
  MessageSquare,
  Sparkles
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { mockTeamAnalytics, mockWeeklyProgress } from '@/data/mockData';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { cn } from '@/lib/utils';
import { useParams } from 'react-router-dom';

const ManagerAnalytics = () => {
  const { workspaceId = "alpha" } = useParams();
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
  return (
    <DashboardLayout
      sidebarItems={managerSidebarItems}
      sidebarTitle="Manager"
      sidebarSubtitle="Business Dashboard"
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              Team Analytics
              <Badge className="gradient-premium text-premium-foreground">
                Pro
              </Badge>
            </h1>
            <p className="text-muted-foreground">Track team performance and productivity trends</p>
          </div>
        </div>

        {/* Team Score Overview */}
        <div className="grid md:grid-cols-4 gap-4">
          <Card className="shadow-card md:col-span-2 bg-gradient-to-br from-primary/5 to-secondary/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Team Productivity Score</p>
                  <p className="text-5xl font-bold">{mockTeamAnalytics.teamScore}%</p>
                  <div className="flex items-center gap-2 mt-2">
                    {mockTeamAnalytics.trend === 'up' ? (
                      <Badge className="bg-success/10 text-success border-0">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        +8% this month
                      </Badge>
                    ) : (
                      <Badge className="bg-destructive/10 text-destructive border-0">
                        <TrendingDown className="h-3 w-3 mr-1" />
                        -3% this month
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="h-24 w-24 rounded-full border-8 border-primary/20 flex items-center justify-center">
                  <div className="h-16 w-16 rounded-full gradient-primary flex items-center justify-center">
                    <TrendingUp className="h-8 w-8 text-primary-foreground" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Tasks Completed</p>
              <p className="text-3xl font-bold mt-1">142</p>
              <p className="text-xs text-success mt-2">↑ 23 from last month</p>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Meetings Held</p>
              <p className="text-3xl font-bold mt-1">28</p>
              <p className="text-xs text-muted-foreground mt-2">Avg. 7 per week</p>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Productivity Trend */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Productivity Trend</CardTitle>
              <CardDescription>Weekly team productivity score</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockWeeklyProgress}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="week" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }} 
                    />
                    <Line 
                      type="monotone" 
                      dataKey="productivityScore" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={3}
                      dot={{ fill: 'hsl(var(--primary))' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Tasks Completed */}
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Tasks Completed</CardTitle>
              <CardDescription>Weekly task completion</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mockWeeklyProgress}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="week" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }} 
                    />
                    <Bar dataKey="tasksCompleted" fill="hsl(var(--secondary))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Individual Performance */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Individual Performance</CardTitle>
              <CardDescription>Team member contribution scores</CardDescription>
            </div>
            <Badge variant="outline" className="text-premium border-premium">
              <Lock className="h-3 w-3 mr-1" />
              Pro Feature
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockTeamAnalytics.memberMetrics.map((metric) => (
                <div key={metric.member.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={metric.member.avatar} alt={metric.member.name} />
                    <AvatarFallback>{metric.member.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{metric.member.name}</p>
                      {metric.trend === 'up' && <TrendingUp className="h-4 w-4 text-success" />}
                      {metric.trend === 'down' && <TrendingDown className="h-4 w-4 text-destructive" />}
                    </div>
                    <p className="text-sm text-muted-foreground">{metric.member.role}</p>
                  </div>
                  <div className="text-right mr-4">
                    <p className="font-medium">{metric.contributionScore}%</p>
                    <p className="text-xs text-muted-foreground">contribution</p>
                  </div>
                  <div className="text-right mr-4">
                    <p className="font-medium">{metric.tasksCompleted}</p>
                    <p className="text-xs text-muted-foreground">tasks</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{metric.meetingParticipation}%</p>
                    <p className="text-xs text-muted-foreground">attendance</p>
                  </div>
                  <Progress value={metric.contributionScore} className="w-24 h-2" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* AI Chatbot Panel */}
        <Card className="shadow-card border-2 border-secondary/20 bg-gradient-to-r from-secondary/5 to-transparent">
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-secondary/10 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-secondary" />
              </div>
              <div>
                <CardTitle className="flex items-center gap-2">
                  AI Coaching Assistant
                  <Badge className="gradient-premium text-premium-foreground text-xs">Pro</Badge>
                </CardTitle>
                <CardDescription>Get personalized insights about your team</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-card border">
                <p className="text-sm mb-3">
                  <span className="font-medium text-secondary">💡 Insight:</span> James Wilson has been 
                  working on blocked tasks for 3 days. Consider checking in or reassigning resources.
                </p>
                <p className="text-sm mb-3">
                  <span className="font-medium text-secondary">📈 Trend:</span> Emily Rodriguez has 
                  the highest completion rate this week. Her work patterns could be shared with the team.
                </p>
                <p className="text-sm">
                  <span className="font-medium text-secondary">⚠️ Alert:</span> 2 tasks from last week's 
                  Sprint Planning are still in "To Do" status. They were assigned during the meeting.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input 
                  type="text" 
                  placeholder="Ask about team performance, bottlenecks, or suggestions..."
                  className="flex-1 px-4 py-2 rounded-lg border bg-background text-sm"
                />
                <Button className="gradient-primary">
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Ask AI
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default ManagerAnalytics;
