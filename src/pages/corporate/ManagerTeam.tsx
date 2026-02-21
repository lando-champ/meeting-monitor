import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  Users, 
  BarChart3, 
  Settings,
  Plus,
  Mail,
  MoreHorizontal,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useParams } from 'react-router-dom';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useEffect, useMemo, useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TeamMember } from '@/lib/types';

const ManagerTeam = () => {
  const { workspaceId = "alpha" } = useParams();
  const basePath = `/business/manager/workspaces/${workspaceId}`;
  const { currentWorkspace, addMemberToWorkspace, refreshWorkspaces } = useWorkspace();
  const { user } = useAuth();
  type EditableMember = TeamMember & { designation?: string };
  const [newMember, setNewMember] = useState("");
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [messageOpen, setMessageOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editDesignation, setEditDesignation] = useState("");
  const inviteCode = currentWorkspace?.inviteCode ?? "N/A";
  const inviteLink = `${window.location.origin}/join/workspace/${inviteCode}`;
  const isValid = useMemo(() => {
    const value = newMember.trim();
    if (!value) return false;
    if (value.includes("@")) return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    return value.length >= 3;
  }, [newMember]);

  const teamMembers: EditableMember[] = useMemo(() => {
    const details = currentWorkspace?.memberDetails ?? [];
    const ownerId = currentWorkspace?.ownerId;
    return details.map((m) => ({
      id: m.id,
      name: m.name,
      email: m.email,
      avatar: `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(m.name)}`,
      role: m.id === ownerId ? "Owner" : "Member",
      status: "active" as const,
      productivityScore: 0,
      tasksCompleted: 0,
      totalTasks: 0,
    }));
  }, [currentWorkspace?.memberDetails, currentWorkspace?.ownerId]);

  useEffect(() => {
    refreshWorkspaces();
  }, [workspaceId, refreshWorkspaces]);

  const managerSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar, badge: 3 },
    { title: 'Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 5 },
    { title: 'Kanban Board', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Team', href: `${basePath}/team`, icon: Users },
    { title: 'Analytics', href: `${basePath}/analytics`, icon: BarChart3, isPremium: true },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  const statusColors: Record<string, string> = {
    active: 'bg-success',
    away: 'bg-warning',
    busy: 'bg-destructive',
    offline: 'bg-muted-foreground',
  };

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
            <h1 className="text-2xl font-bold">Team</h1>
            <p className="text-muted-foreground">
              Manage your team members and view their productivity
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <Mail className="h-4 w-4 mr-2" />
                  Invite Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite to workspace</DialogTitle>
                  <DialogDescription>Share the invite code or link.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label>Invite Code</Label>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" className="flex-1 justify-start" disabled>
                        {inviteCode}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => navigator.clipboard.writeText(inviteCode)}
                      >
                        Copy Code
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Invite Link</Label>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" className="flex-1 justify-start" disabled>
                        {inviteLink}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => navigator.clipboard.writeText(inviteLink)}
                      >
                        Copy Link
                      </Button>
                    </div>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add a team member</DialogTitle>
                  <DialogDescription>
                    Enter a username or email to add them to this workspace.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <Label htmlFor="member-input">Username or Email</Label>
                  <Input
                    id="member-input"
                    placeholder="e.g. alex.kim@company.com"
                    value={newMember}
                    onChange={(event) => {
                      setNewMember(event.target.value);
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
                      if (!isValid || !currentWorkspace) {
                        setError("Enter a valid username or email.");
                        return;
                      }
                      const normalized = newMember.trim().toLowerCase();
                      addMemberToWorkspace(currentWorkspace.id, normalized);
                      setTeamMembers((prev) => [
                        {
                          id: `member-${Date.now()}`,
                          name: normalized.split("@")[0] ?? normalized,
                          email: normalized,
                          avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${normalized}`,
                          role: "New Member",
                          status: "active",
                          productivityScore: 0,
                          tasksCompleted: 0,
                          totalTasks: 0,
                        },
                        ...prev,
                      ]);
                      setNewMember("");
                    }}
                  >
                    Add Member
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {currentWorkspace && (
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>Workspace Members</CardTitle>
              <CardDescription>All team members with access to this workspace (from database)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(currentWorkspace.memberDetails ?? []).map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-sm">
                    <span className="font-medium">{m.name}</span>
                    <span className="text-muted-foreground">{m.email}</span>
                    <Badge variant={m.id === currentWorkspace.ownerId ? "default" : "secondary"}>
                      {m.id === currentWorkspace.ownerId ? "Owner" : "Member"}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Team Stats */}
        <div className="grid grid-cols-4 gap-4">
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">{teamMembers.length}</p>
                  <p className="text-sm text-muted-foreground">Total Members</p>
                </div>
                <Users className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-success">
                    {teamMembers.filter(m => m.status === 'active').length}
                  </p>
                  <p className="text-sm text-muted-foreground">Active Now</p>
                </div>
                <div className="h-8 w-8 rounded-full bg-success/20 flex items-center justify-center">
                  <div className="h-3 w-3 rounded-full bg-success animate-pulse" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">87%</p>
                  <p className="text-sm text-muted-foreground">Avg Productivity</p>
                </div>
                <TrendingUp className="h-8 w-8 text-success/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">24</p>
                  <p className="text-sm text-muted-foreground">Tasks This Week</p>
                </div>
                <ListTodo className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Team Members Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {teamMembers.map((member) => (
            <Card key={member.id} className="shadow-card hover:shadow-hover transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Avatar className="h-12 w-12">
                        <AvatarImage src={member.avatar} />
                        <AvatarFallback>
                          {member.name.split(' ').map(n => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div className={cn(
                        "absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-background",
                        statusColors[member.status]
                      )} />
                    </div>
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {member.role}
                        {member.designation ? ` • ${member.designation}` : ""}
                      </p>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setSelectedMember(member);
                          setEditName(member.name);
                          setEditRole(member.role);
                          setEditDesignation(member.designation ?? "");
                          setEditOpen(true);
                        }}
                      >
                        Edit
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Productivity</span>
                      <span className="font-medium flex items-center gap-1">
                        {member.productivityScore}%
                        {member.productivityScore >= 80 ? (
                          <TrendingUp className="h-3 w-3 text-success" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-destructive" />
                        )}
                      </span>
                    </div>
                    <Progress value={member.productivityScore} className="h-2" />
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Tasks</span>
                    <span className="font-medium">
                      {member.tasksCompleted}/{member.totalTasks} completed
                    </span>
                  </div>

                  <div className="flex items-center gap-2 pt-2">
                    <Badge variant="outline" className="capitalize text-xs">
                      {member.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="ml-auto h-7 px-2"
                      onClick={() => {
                        setSelectedMember(member);
                        setMessageOpen(true);
                      }}
                    >
                      <Mail className="h-3 w-3 mr-1" />
                      Message
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit member</DialogTitle>
            <DialogDescription>Update name, role, or designation.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Label htmlFor="edit-name">Name</Label>
            <Input
              id="edit-name"
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
            />
            <Label htmlFor="edit-role">Role</Label>
            <Input
              id="edit-role"
              value={editRole}
              onChange={(event) => setEditRole(event.target.value)}
            />
            <Label htmlFor="edit-designation">Designation</Label>
            <Input
              id="edit-designation"
              placeholder="Optional"
              value={editDesignation}
              onChange={(event) => setEditDesignation(event.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => {
                if (!selectedMember) {
                  return;
                }
                setTeamMembers((prev) =>
                  prev.map((member) =>
                    member.id === selectedMember.id
                          ? {
                              ...member,
                              name: editName.trim() || member.name,
                              role: editRole.trim() || member.role,
                              designation: editDesignation.trim() || member.designation,
                            }
                      : member,
                  ),
                );
                setEditOpen(false);
              }}
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={messageOpen} onOpenChange={setMessageOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Message {selectedMember?.name}</DialogTitle>
            <DialogDescription>Chat placeholder for future integration.</DialogDescription>
          </DialogHeader>
          <Textarea placeholder="Write a message..." />
          <DialogFooter>
            <Button variant="secondary" onClick={() => setMessageOpen(false)}>
              Send Message
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default ManagerTeam;
