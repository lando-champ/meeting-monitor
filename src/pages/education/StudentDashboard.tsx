import { 
  LayoutDashboard, 
  BookOpen, 
  ListTodo, 
  FileText, 
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Radio,
  ArrowRight
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { useNavigate } from 'react-router-dom';
import { useClass } from '@/context/ClassContext';
import { useEducation } from '@/context/EducationContext';
import { format, formatDistanceToNow, differenceInDays } from 'date-fns';
import { cn } from '@/lib/utils';
import { useParams } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

const StudentDashboard = () => {
  const { user } = useAuth();
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const { classes } = useClass();
  const { getLecturesByClass } = useEducation();
  const upcomingClassList = classes.slice(0, 3);
  const classLectures = getLecturesByClass(classId);
  const liveLecture = classLectures.find((l) => l.status === "live");
  const basePath = `/education/student/classes/${classId}`;
  const studentSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'My Class', href: `${basePath}/my-class`, icon: BookOpen },
    { title: 'To-Do List', href: `${basePath}/todo-list`, icon: ListTodo, badge: 4 },
    { title: 'Lecture Notes', href: `${basePath}/lecture-notes`, icon: FileText },
    { title: 'Calendar', href: `${basePath}/calendar`, icon: Calendar },
  ];
  const upcomingClasses = classLectures.filter((l) => l.status === "scheduled").slice(0, 3);
  const recentLectures = classLectures.filter((l) => l.status === "completed" && l.summary).slice(0, 2);
  const { getAssignmentsForStudent } = useEducation();
  const allAssignments = getAssignmentsForStudent(classId);
  const todoItems = allAssignments.slice(0, 5);
  
  const completedAssignments = 3; // Could be derived from submissions
  const totalAssignments = todoItems.length + completedAssignments;
  const progressPercent = (completedAssignments / totalAssignments) * 100;

  // Get assignments due soon
  const urgentAssignments = todoItems.filter(
    (a) => differenceInDays(new Date(a.dueDate), new Date()) <= 3
  );

  return (
    <DashboardLayout
      sidebarItems={studentSidebarItems}
      sidebarTitle="Student"
      sidebarSubtitle="Education Dashboard"
      showMeetingStatus={false}
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold">Hi {user?.name?.split(' ')[0] ?? 'there'}! 👋</h1>
          <p className="text-muted-foreground">
            You have {todoItems.length} tasks to complete this week.
          </p>
        </div>

        {/* Live Class Banner */}
        {liveLecture && (
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center">
                    <Radio className="h-5 w-5 text-primary animate-pulse" />
                  </div>
                  <div>
                    <p className="font-medium">{liveLecture.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {liveLecture.className} • Live now
                    </p>
                  </div>
                </div>
                <Button
                  className="gradient-primary"
                  onClick={() =>
                    liveLecture &&
                    navigate(`${basePath}/lecture/${liveLecture.id}/meeting`)
                  }
                >
                  Join Class
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Progress & Urgent Cards */}
        <div className="grid md:grid-cols-2 gap-4">
          {/* Weekly Progress */}
          <Card className="shadow-card bg-gradient-to-r from-primary/5 to-secondary/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm text-muted-foreground">Weekly Progress</p>
                  <p className="text-2xl font-bold">{completedAssignments} of {totalAssignments} done</p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-primary">{Math.round(progressPercent)}%</p>
                </div>
              </div>
              <Progress value={progressPercent} className="h-3" />
            </CardContent>
          </Card>

          {/* Urgent Deadlines */}
          {urgentAssignments.length > 0 && (
            <Card className="shadow-card border-warning/30 bg-warning/5">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3 mb-3">
                  <AlertCircle className="h-5 w-5 text-warning" />
                  <p className="font-medium">Due Soon!</p>
                </div>
                <div className="space-y-2">
                  {urgentAssignments.slice(0, 2).map((a) => (
                    <div key={a.id} className="flex items-center justify-between text-sm">
                      <span className="truncate">{a.title}</span>
                      <Badge variant="outline" className="border-warning text-warning text-xs">
                        {formatDistanceToNow(a.dueDate, { addSuffix: true })}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* To-Do List */}
          <Card className="shadow-card lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-secondary" />
                  My To-Do
                </CardTitle>
                <CardDescription>Auto-generated from your lectures</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => navigate(`${basePath}/todo-list`)}>
                View All
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {todoItems.map((task) => {
                  const daysUntilDue = differenceInDays(new Date(task.dueDate), new Date());
                  const isUrgent = daysUntilDue <= 3;
                  
                  return (
                    <div 
                      key={task.id} 
                      className={cn(
                        "flex items-start gap-3 p-4 rounded-lg border transition-shadow hover:shadow-sm",
                        isUrgent && "border-warning/30 bg-warning/5"
                      )}
                    >
                      <Checkbox className="mt-1" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium">{task.title}</p>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-1 mb-2">
                          {task.description}
                        </p>
                        <div className="flex items-center gap-3">
                          <span className={cn(
                            "text-xs flex items-center gap-1",
                            isUrgent ? "text-warning font-medium" : "text-muted-foreground"
                          )}>
                            <Clock className="h-3 w-3" />
                            Due {format(new Date(task.dueDate), "MMM d")}
                            {isUrgent && ` (${daysUntilDue} days)`}
                          </span>
                        </div>
                      </div>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Sidebar - Schedule & Quick Links */}
          <div className="space-y-6">
            {/* Upcoming Classes */}
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle>Upcoming Classes</CardTitle>
                <CardDescription>Today's schedule</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {upcomingClassList.length === 0 ? (
                    <p className="text-muted-foreground text-sm py-2">No upcoming classes</p>
                  ) : (
                    upcomingClassList.map((cls) => (
                      <div key={cls.id} className="p-3 rounded-lg border">
                        <p className="font-medium text-sm">{cls.name}</p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                          <Clock className="h-3 w-3" />
                          {cls.description || "—"}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* This Week Calendar */}
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle>This Week</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-7 gap-1 text-center text-xs mb-2">
                  {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, i) => (
                    <div key={i} className="text-muted-foreground py-1">{day}</div>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-1 text-center text-sm">
                  {[27, 28, 29, 30, 31, 1, 2].map((day, i) => (
                    <div 
                      key={i} 
                      className={cn(
                        "py-2 rounded-lg",
                        day === 29 && "bg-primary text-primary-foreground font-medium",
                        day === 30 && "bg-warning/20 text-warning-foreground",
                        day > 31 && "text-muted-foreground"
                      )}
                    >
                      {day > 31 ? day - 31 : day}
                    </div>
                  ))}
                </div>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <span>Today - Data Structures</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-warning" />
                    <span>Assignment Due</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Recent Lecture Notes */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Recent Lecture Notes
              </CardTitle>
              <CardDescription>AI-generated summaries from your classes</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate(`${basePath}/lecture-notes`)}>
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              {recentLectures.map((lecture) => (
                <div key={lecture.id} className="p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="text-xs">
                      {lecture.className}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(lecture.date), "MMM d")}
                    </span>
                  </div>
                  <p className="font-medium mb-2">{lecture.title}</p>
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {lecture.summary?.overview}
                  </p>
                  
                  {/* Key Points Preview */}
                  <div className="mb-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">Key Takeaways:</p>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      {(lecture.summary?.keyPoints ?? []).slice(0, 2).map((point, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <CheckCircle2 className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                          <span className="line-clamp-1">{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <Button
                    variant="link"
                    size="sm"
                    className="h-auto p-0 text-primary"
                    onClick={() =>
                      navigate(`${basePath}/lecture/${lecture.id}/meeting`)
                    }
                  >
                    Read full notes →
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

export default StudentDashboard;
