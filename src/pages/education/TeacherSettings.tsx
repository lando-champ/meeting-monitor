import { 
  LayoutDashboard, 
  BookOpen, 
  Video, 
  FileText, 
  Users, 
  Settings,
  Bell,
  Shield,
  Palette,
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useParams } from 'react-router-dom';
import { useClass } from '@/context/ClassContext';

const TeacherSettings = () => {
  const { classId = "cs101" } = useParams();
  const basePath = `/education/teacher/classes/${classId}`;
  const { currentClass } = useClass();
  const inviteCode = currentClass?.inviteCode ?? "N/A";
  const inviteLink = `${window.location.origin}/join/class/${inviteCode}`;
  const handleCopy = (value: string) => {
    void navigator.clipboard.writeText(value);
  };
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
      <div className="space-y-6 max-w-4xl">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Class Invite</CardTitle>
            <CardDescription>Share access to this class</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-2">
              <Label>Invite Code</Label>
              <div className="flex items-center gap-2">
                <Button variant="outline" className="justify-start flex-1" disabled>
                  {inviteCode}
                </Button>
                <Button variant="secondary" onClick={() => handleCopy(inviteCode)}>
                  Copy Code
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Invite Link</Label>
              <div className="flex items-center gap-2">
                <Button variant="outline" className="justify-start flex-1" disabled>
                  {inviteLink}
                </Button>
                <Button variant="secondary" onClick={() => handleCopy(inviteLink)}>
                  Copy Link
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account and preferences
          </p>
        </div>

        {/* Notification Preferences */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notification Preferences
            </CardTitle>
            <CardDescription>Choose what notifications you receive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Assignment Submissions</Label>
                <p className="text-sm text-muted-foreground">Get notified when students submit work</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label>Lecture Summaries</Label>
                <p className="text-sm text-muted-foreground">Receive AI-generated summaries after lectures</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label>Student Questions</Label>
                <p className="text-sm text-muted-foreground">Notifications for student inquiries</p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* Other Settings */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>More Settings</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {[
              { icon: Shield, title: 'Privacy & Security', description: 'Manage account security' },
              { icon: Palette, title: 'Appearance', description: 'Customize the look and feel' },
              { icon: HelpCircle, title: 'Help & Support', description: 'Get help and contact support' },
            ].map((section, index) => (
              <div key={section.title}>
                <button className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors text-left">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                      <section.icon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{section.title}</p>
                      <p className="text-sm text-muted-foreground">{section.description}</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground" />
                </button>
                {index < 2 && <Separator />}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default TeacherSettings;
