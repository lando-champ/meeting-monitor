import { Link } from 'react-router-dom';
import { 
  GraduationCap, 
  BookOpen, 
  ArrowLeft,
  Users,
  ClipboardList,
  BarChart3,
  ListTodo,
  FileText,
  Calendar
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const EducationRoleSelect = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <Link to="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-secondary/10 mb-6">
              <GraduationCap className="h-8 w-8 text-secondary" />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold mb-4">
              Education Dashboard
            </h1>
            <p className="text-muted-foreground text-lg">
              Select your role to access your personalized learning space
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Teacher Card */}
            <Link to="/education/teacher/classes" className="group">
              <Card className="h-full shadow-card hover:shadow-hover transition-all duration-300 border-2 border-transparent hover:border-secondary/20">
                <CardHeader>
                  <div className="h-14 w-14 rounded-xl bg-secondary/10 flex items-center justify-center mb-4 group-hover:bg-secondary/20 transition-colors">
                    <BookOpen className="h-7 w-7 text-secondary" />
                  </div>
                  <CardTitle className="text-xl">Teacher</CardTitle>
                  <CardDescription>
                    Manage classes with AI-powered assistance
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm text-muted-foreground mb-6">
                    <li className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-secondary" />
                      Automated lecture summaries
                    </li>
                    <li className="flex items-center gap-2">
                      <ClipboardList className="h-4 w-4 text-secondary" />
                      Auto-extracted assignments
                    </li>
                    <li className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-secondary" />
                      Student progress tracking
                    </li>
                    <li className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-secondary" />
                      Engagement analytics
                    </li>
                  </ul>
                  <Button variant="secondary" className="w-full">
                    Continue as Teacher
                  </Button>
                </CardContent>
              </Card>
            </Link>

            {/* Student Card */}
            <Link to="/education/student/classes" className="group">
              <Card className="h-full shadow-card hover:shadow-hover transition-all duration-300 border-2 border-transparent hover:border-primary/20">
                <CardHeader>
                  <div className="h-14 w-14 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                    <GraduationCap className="h-7 w-7 text-primary" />
                  </div>
                  <CardTitle className="text-xl">Student</CardTitle>
                  <CardDescription>
                    Never miss an assignment again
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm text-muted-foreground mb-6">
                    <li className="flex items-center gap-2">
                      <ListTodo className="h-4 w-4 text-primary" />
                      Auto-generated to-do list
                    </li>
                    <li className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-primary" />
                      Lecture notes & summaries
                    </li>
                    <li className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-primary" />
                      Assignment reminders
                    </li>
                    <li className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-primary" />
                      Class schedule overview
                    </li>
                  </ul>
                  <Button className="w-full">
                    Continue as Student
                  </Button>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
};

export default EducationRoleSelect;
