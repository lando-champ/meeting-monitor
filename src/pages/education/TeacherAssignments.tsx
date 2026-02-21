import { useState } from "react";
import {
  LayoutDashboard,
  BookOpen,
  Video,
  FileText,
  Users,
  Settings,
  Plus,
  Clock,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { SidebarItem } from "@/components/layout/Sidebar";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { useParams } from "react-router-dom";
import { useEducation } from "@/context/EducationContext";

const TeacherAssignments = () => {
  const { classId = "cs101" } = useParams();
  const basePath = `/education/teacher/classes/${classId}`;
  const { getAssignmentsByClass, addAssignment, getSubmissionsByAssignment } =
    useEducation();
  const assignments = getAssignmentsByClass(classId);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    dueDate: "",
  });
  const [submissionsDialog, setSubmissionsDialog] = useState<{ assignmentId: string; title: string } | null>(null);

  const teacherSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "Class", href: `${basePath}/class`, icon: BookOpen },
    { title: "Lecture", href: `${basePath}/lecture`, icon: Video, badge: 2 },
    { title: "Assignments", href: `${basePath}/assignments`, icon: FileText, badge: assignments.length },
    { title: "Students", href: `${basePath}/students`, icon: Users },
    { title: "Settings", href: `${basePath}/settings`, icon: Settings },
  ];

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    addAssignment({
      title: form.title,
      description: form.description,
      dueDate: form.dueDate || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      classId,
      createdAt: new Date().toISOString(),
    });
    setForm({ title: "", description: "", dueDate: "" });
    setCreateOpen(false);
  };

  const submissionCounts = assignments.reduce(
    (acc, a) => ({ ...acc, [a.id]: getSubmissionsByAssignment(a.id).length }),
    {} as Record<string, number>
  );

  return (
    <DashboardLayout
      sidebarItems={teacherSidebarItems}
      sidebarTitle="Teacher"
      sidebarSubtitle="Education Dashboard"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Assignments</h1>
            <p className="text-muted-foreground">
              Manage and track student assignments
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Assignment
          </Button>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">{assignments.length}</p>
                  <p className="text-sm text-muted-foreground">Total</p>
                </div>
                <FileText className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-primary">
                    {assignments.filter((a) => new Date(a.dueDate) >= new Date()).length}
                  </p>
                  <p className="text-sm text-muted-foreground">Active</p>
                </div>
                <Clock className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-success">
                    {assignments.filter((a) => new Date(a.dueDate) < new Date()).length}
                  </p>
                  <p className="text-sm text-muted-foreground">Past Due</p>
                </div>
                <CheckCircle2 className="h-8 w-8 text-success/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-secondary">
                    {Object.values(submissionCounts).reduce((a, b) => a + b, 0)}
                  </p>
                  <p className="text-sm text-muted-foreground">Submissions</p>
                </div>
                <Sparkles className="h-8 w-8 text-secondary/20" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>All Assignments</CardTitle>
            <CardDescription>Track submission status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {assignments.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No assignments yet. Create one to get started.
                </p>
              ) : (
                assignments.map((assignment) => {
                  const submitted = submissionCounts[assignment.id] ?? 0;
                  const isPastDue = new Date(assignment.dueDate) < new Date();
                  return (
                    <div
                      key={assignment.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={cn(
                            "h-10 w-10 rounded-lg flex items-center justify-center",
                            isPastDue ? "bg-success/10" : "bg-primary/10"
                          )}
                        >
                          {isPastDue ? (
                            <CheckCircle2 className="h-5 w-5 text-success" />
                          ) : (
                            <FileText className="h-5 w-5 text-primary" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium">{assignment.title}</p>
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {assignment.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm font-medium">
                            {submitted} submission{submitted !== 1 ? "s" : ""}
                          </p>
                          <p
                            className={cn(
                              "text-xs flex items-center justify-end gap-1",
                              isPastDue ? "text-muted-foreground" : "text-muted-foreground"
                            )}
                          >
                            <Clock className="h-3 w-3" />
                            Due {formatDistanceToNow(new Date(assignment.dueDate), { addSuffix: true })}
                          </p>
                        </div>
                        <Badge variant={isPastDue ? "default" : "secondary"}>
                          {isPastDue ? "Past due" : "Active"}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setSubmissionsDialog({
                              assignmentId: assignment.id,
                              title: assignment.title,
                            })
                          }
                        >
                          {submitted > 0 ? "View Submissions" : "Review"}
                        </Button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {submissionsDialog && (
        <Dialog open={!!submissionsDialog} onOpenChange={() => setSubmissionsDialog(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Submissions: {submissionsDialog.title}</DialogTitle>
              <DialogDescription>Student submissions for this assignment</DialogDescription>
            </DialogHeader>
            <div className="max-h-64 overflow-y-auto space-y-3">
              {getSubmissionsByAssignment(submissionsDialog.assignmentId).length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No submissions yet.</p>
              ) : (
                getSubmissionsByAssignment(submissionsDialog.assignmentId).map((sub) => (
                  <div
                    key={sub.id}
                    className="p-3 rounded-lg border"
                  >
                    <p className="font-medium text-sm">{sub.studentName}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Submitted {formatDistanceToNow(new Date(sub.submittedAt), { addSuffix: true })}
                    </p>
                    <p className="text-sm mt-2 whitespace-pre-wrap">{sub.content}</p>
                  </div>
                ))
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Assignment</DialogTitle>
            <DialogDescription>
              Create a new assignment for your students.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <Label htmlFor="a-title">Assignment Title</Label>
              <Input
                id="a-title"
                value={form.title}
                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                placeholder="e.g. Chapter 2 Exercises"
                required
              />
            </div>
            <div>
              <Label htmlFor="a-desc">Description</Label>
              <Textarea
                id="a-desc"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="Instructions and requirements for the assignment"
                rows={4}
              />
            </div>
            <div>
              <Label htmlFor="a-due">Due Date</Label>
              <Input
                id="a-due"
                type="date"
                value={form.dueDate}
                onChange={(e) => setForm((p) => ({ ...p, dueDate: e.target.value }))}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Create Assignment</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default TeacherAssignments;
