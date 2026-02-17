import {
  LayoutDashboard,
  BookOpen,
  Presentation,
  ClipboardList,
  Users,
  Settings,
  Clock,
  Radio,
  Sparkles,
  Calendar,
} from "lucide-react";
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { format } from 'date-fns';
import { useParams, useNavigate } from 'react-router-dom';
import { useEducation } from '@/context/EducationContext';
import { useClass } from '@/context/ClassContext';

const TeacherDashboard = () => {
  const { classId = "cs101" } = useParams();
  const navigate = useNavigate();
  const basePath = `/education/teacher/classes/${classId}`;
  const { classes } = useClass();
  const { getLecturesByClass, getAssignmentsByClass, getSubmissionsByAssignment } = useEducation();
  const teacherSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Class', href: `${basePath}/class`, icon: BookOpen },
    { title: 'Lecture', href: `${basePath}/lecture`, icon: Presentation, badge: 1 },
    { title: 'Assignments', href: `${basePath}/assignments`, icon: ClipboardList, badge: 3 },
    { title: 'Students', href: `${basePath}/students`, icon: Users },
    { title: 'Calendar', href: `${basePath}/calendar`, icon: Calendar },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  const allLectures = classes.flatMap((cls) => getLecturesByClass(cls.id));
  const liveLecture = allLectures.find((l) => l.status === 'live');
  const upcomingLectures = allLectures.filter((l) => l.status === 'scheduled').slice(0, 3);
  const completedLectures = allLectures.filter((l) => l.status === 'completed' && l.summary).slice(0, 2);
  const allAssignments = classes.flatMap((cls) => getAssignmentsByClass(cls.id));
  const pendingAssignments = allAssignments.filter((a) => new Date(a.dueDate) >= new Date());

  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
      userName="Prof. James Wilson"
      userRole="Computer Science"
      userAvatar="https://api.dicebear.com/7.x/avataaars/svg?seed=James"
      showMeetingStatus={false}
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Good morning, Professor</h1>
            <p className="text-muted-foreground">You have {upcomingLectures.length} lectures scheduled today.</p>
          </div>
          <Button
            className="bg-secondary hover:bg-secondary/90 text-secondary-foreground"
            onClick={() => navigate(`${basePath}/lecture`)}
          >
            <Presentation className="h-4 w-4 mr-2" />
            Start Lecture
          </Button>
        </div>

        {/* Live Lecture Banner */}
        {liveLecture && (
          <Card className="border-secondary/30 bg-secondary/5">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-secondary/20 flex items-center justify-center">
                    <Radio className="h-5 w-5 text-secondary animate-pulse" />
                  </div>
                  <div>
                    <p className="font-medium">{liveLecture.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {liveLecture.className} • Live now
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-secondary text-secondary">
                    <Sparkles className="h-3 w-3 mr-1" />
                    AI Recording
                  </Badge>
                  <Button variant="outline" className="border-secondary text-secondary hover:bg-secondary/10">
                    View Live Transcript
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Today's Schedule */}
        <div className="grid lg:grid-cols-3 gap-6">
          <Card className="shadow-card lg:col-span-2">
            <CardHeader>
              <CardTitle>Today's Schedule</CardTitle>
              <CardDescription>Your classes for today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {classes.map((cls, index) => {
                  const classLectures = getLecturesByClass(cls.id);
                  const nextLecture = classLectures.find((l) => l.status === 'live') || classLectures.find((l) => l.status === 'scheduled');
                  return (
                    <div key={cls.id} className="flex items-center gap-4 p-4 rounded-lg border hover:shadow-sm transition-shadow">
                      <div className="h-12 w-12 rounded-lg bg-secondary/10 flex items-center justify-center text-lg font-bold text-secondary">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{cls.name}</p>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {nextLecture ? `${nextLecture.date} at ${nextLecture.time}` : 'No session scheduled'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {cls.studentCount} students
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          nextLecture &&
                          navigate(
                            `/education/teacher/classes/${cls.id}/lecture/${nextLecture.id}/meeting`
                          )
                        }
                        disabled={!nextLecture}
                      >
                        <Presentation className="h-4 w-4 mr-2" />
                        Start
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <div className="space-y-4">
            <Card className="shadow-card">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-muted-foreground">This Week</p>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-2xl font-bold">8</p>
                    <p className="text-xs text-muted-foreground">Lectures</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">96</p>
                    <p className="text-xs text-muted-foreground">Students</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{pendingAssignments.length}</p>
                    <p className="text-xs text-muted-foreground">Pending Reviews</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-success">87%</p>
                    <p className="text-xs text-muted-foreground">Attendance</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Class Engagement</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span>Intro to CS</span>
                      <span className="font-medium">92%</span>
                    </div>
                    <Progress value={92} className="h-2" />
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span>Data Structures</span>
                      <span className="font-medium">85%</span>
                    </div>
                    <Progress value={85} className="h-2" />
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span>Web Dev</span>
                      <span className="font-medium">78%</span>
                    </div>
                    <Progress value={78} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Recent Lectures with AI Summaries */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-secondary" />
                Recent Lecture Summaries
              </CardTitle>
              <CardDescription>AI-generated notes and extracted assignments</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate(`${basePath}/lecture`)}>
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              {completedLectures.map((lecture) => (
                <div key={lecture.id} className="p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="font-medium">{lecture.title}</p>
                      <p className="text-sm text-muted-foreground">{lecture.className}</p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {format(new Date(lecture.date), 'MMM d')}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {lecture.summary?.overview}
                  </p>
                  
                  {/* Key Points */}
                  <div className="mb-3">
                    <p className="text-xs font-medium text-muted-foreground mb-2">Key Points:</p>
                    <div className="flex flex-wrap gap-1">
                      {(lecture.summary?.keyPoints ?? []).slice(0, 3).map((point, i) => (
                        <Badge key={i} variant="secondary" className="text-xs font-normal">
                          {point.slice(0, 25)}...
                        </Badge>
                      ))}
                    </div>
                  </div>
                  
                  {/* Auto-extracted assignments */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground flex items-center gap-1">
                      <ClipboardList className="h-3 w-3" />
                      {(lecture.summary?.actionItems?.length ?? 0)} assignments extracted
                    </span>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0 text-secondary"
                      onClick={() => navigate(`/education/teacher/classes/${lecture.classId}/lecture/${lecture.id}/summary`)}
                    >
                      View details →
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pending Assignments */}
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Pending Assignments</CardTitle>
              <CardDescription>Submissions waiting for review</CardDescription>
            </div>
            <Badge variant="secondary">{pendingAssignments.length} pending</Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingAssignments.slice(0, 4).map((assignment) => {
                const submissionCount = getSubmissionsByAssignment(assignment.id).length;
                return (
                  <div key={assignment.id} className="flex items-center gap-4 p-3 rounded-lg border hover:shadow-sm transition-shadow">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium">{assignment.title}</p>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        {assignment.description}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">Due {format(new Date(assignment.dueDate), 'MMM d')}</p>
                      <p className="text-xs text-muted-foreground">{submissionCount} submission{submissionCount !== 1 ? 's' : ''}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`${basePath}/assignments`)}
                    >
                      Review
                    </Button>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default TeacherDashboard;
