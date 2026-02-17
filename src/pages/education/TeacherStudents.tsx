import { 
  LayoutDashboard, 
  BookOpen, 
  Video, 
  FileText, 
  Users, 
  Settings,
  Search,
  Mail,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { useParams } from 'react-router-dom';
import { useClass } from '@/context/ClassContext';
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
import { useMemo, useState } from 'react';

const mockStudents = [
  { id: '1', name: 'Emma Thompson', email: 'emma.t@university.edu', grade: 'A', progress: 92, engagement: 'high' },
  { id: '2', name: 'James Chen', email: 'james.c@university.edu', grade: 'B+', progress: 85, engagement: 'medium' },
  { id: '3', name: 'Sofia Martinez', email: 'sofia.m@university.edu', grade: 'A-', progress: 88, engagement: 'high' },
  { id: '4', name: 'Michael Johnson', email: 'michael.j@university.edu', grade: 'B', progress: 78, engagement: 'medium' },
  { id: '5', name: 'Olivia Brown', email: 'olivia.b@university.edu', grade: 'C+', progress: 65, engagement: 'low' },
];

const TeacherStudents = () => {
  const { classId = "cs101" } = useParams();
  const basePath = `/education/teacher/classes/${classId}`;
  const { currentClass, addStudentToClass } = useClass();
  const [newStudent, setNewStudent] = useState("");
  const [error, setError] = useState("");
  const isValid = useMemo(() => {
    const value = newStudent.trim();
    if (!value) {
      return false;
    }
    if (value.includes("@")) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    }
    return value.length >= 3;
  }, [newStudent]);
  const teacherSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Class', href: `${basePath}/class`, icon: BookOpen },
    { title: 'Lecture', href: `${basePath}/lecture`, icon: Video, badge: 2 },
    { title: 'Assignments', href: `${basePath}/assignments`, icon: FileText, badge: 5 },
    { title: 'Students', href: `${basePath}/students`, icon: Users },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
      userName="Prof. James Wilson"
      userRole="Computer Science"
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Students</h1>
            <p className="text-muted-foreground">
              Track student progress and engagement
            </p>
          </div>
          <Dialog>
            <DialogTrigger asChild>
              <Button>
                <Mail className="h-4 w-4 mr-2" />
                Add Student
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add a student</DialogTitle>
                <DialogDescription>
                  Enter a username or email to add them to this class.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <Label htmlFor="student-input">Username or Email</Label>
                <Input
                  id="student-input"
                  placeholder="e.g. emma.thompson@university.edu"
                  value={newStudent}
                  onChange={(event) => {
                    setNewStudent(event.target.value);
                    setError("");
                  }}
                />
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>
              <DialogFooter>
                <Button
                  variant="secondary"
                  disabled={!isValid}
                  onClick={() => {
                    if (!isValid || !currentClass) {
                      setError("Enter a valid username or email.");
                      return;
                    }
                    addStudentToClass(currentClass.id, newStudent.trim().toLowerCase());
                    setNewStudent("");
                  }}
                >
                  Add Student
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {currentClass && (
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Class Roster</CardTitle>
              <CardDescription>Students with access to this class</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {currentClass.students.map((student) => (
                  <div key={student} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{student}</span>
                    <Badge variant="secondary">Student</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search students..." className="pl-10" />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">95</p>
                  <p className="text-sm text-muted-foreground">Total Students</p>
                </div>
                <Users className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-success">82%</p>
                  <p className="text-sm text-muted-foreground">Avg. Completion</p>
                </div>
                <TrendingUp className="h-8 w-8 text-success/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">B+</p>
                  <p className="text-sm text-muted-foreground">Avg. Grade</p>
                </div>
                <FileText className="h-8 w-8 text-secondary/20" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Students List */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Student Roster</CardTitle>
            <CardDescription>All students across your classes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockStudents.map((student) => (
                <div 
                  key={student.id} 
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex items-center gap-4">
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={`https://api.dicebear.com/7.x/initials/svg?seed=${student.name}`} />
                      <AvatarFallback>
                        {student.name.split(' ').map(n => n[0]).join('')}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{student.name}</p>
                      <p className="text-sm text-muted-foreground">{student.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="w-32">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="font-medium flex items-center gap-1">
                          {student.progress}%
                          {student.progress >= 80 ? (
                            <TrendingUp className="h-3 w-3 text-success" />
                          ) : student.progress < 70 ? (
                            <TrendingDown className="h-3 w-3 text-destructive" />
                          ) : null}
                        </span>
                      </div>
                      <Progress value={student.progress} className="h-1.5" />
                    </div>
                    <Badge variant="outline" className="w-12 justify-center">{student.grade}</Badge>
                    <Badge 
                      variant={student.engagement === 'high' ? 'default' : student.engagement === 'low' ? 'destructive' : 'secondary'}
                      className="capitalize w-20 justify-center"
                    >
                      {student.engagement}
                    </Badge>
                    <Button size="sm" variant="ghost">
                      <Mail className="h-4 w-4" />
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

export default TeacherStudents;
