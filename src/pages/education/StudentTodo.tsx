import { useState } from "react";
import {
  LayoutDashboard,
  BookOpen,
  ListTodo,
  FileText,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Upload,
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { useParams } from "react-router-dom";
import { useEducation } from "@/context/EducationContext";
import { useClass } from "@/context/ClassContext";

const StudentTodo = () => {
  const { classId = "cs101" } = useParams();
  const basePath = `/education/student/classes/${classId}`;
  const { getAssignmentsForStudent, submitAssignment, submissions } = useEducation();
  const { currentUserEmail } = useClass();
  const assignments = getAssignmentsForStudent(classId);

  const hasSubmitted = (assignmentId: string) =>
    submissions.some(
      (s) => s.assignmentId === assignmentId && s.studentId === currentUserEmail
    );

  const pendingCount = assignments.filter(
    (a) => !hasSubmitted(a.id) && new Date(a.dueDate) >= new Date()
  ).length;
  const completedCount = assignments.filter((a) => hasSubmitted(a.id)).length;
  const overdueCount = assignments.filter(
    (a) => !hasSubmitted(a.id) && new Date(a.dueDate) < new Date()
  ).length;

  const [submitDialog, setSubmitDialog] = useState<{
    assignmentId: string;
    title: string;
  } | null>(null);
  const [submitContent, setSubmitContent] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!submitDialog) return;
    submitAssignment({
      assignmentId: submitDialog.assignmentId,
      studentId: currentUserEmail,
      studentName: "Emma Thompson",
      content: submitContent,
      submittedAt: new Date().toISOString(),
    });
    setSubmitContent("");
    setSubmitDialog(null);
  };

  const studentSidebarItems: SidebarItem[] = [
    { title: "Dashboard", href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: "My Class", href: `${basePath}/my-class`, icon: BookOpen },
    { title: "To-Do List", href: `${basePath}/todo-list`, icon: ListTodo, badge: pendingCount },
    { title: "Lecture Notes", href: `${basePath}/lecture-notes`, icon: FileText },
    { title: "Calendar", href: `${basePath}/calendar`, icon: Calendar },
  ];

  return (
    <DashboardLayout
      sidebarItems={studentSidebarItems}
      sidebarTitle="Student"
      sidebarSubtitle="Learning Dashboard"
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Assignments</h1>
          <p className="text-muted-foreground">
            Submit your homework and assignments
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-destructive">{overdueCount}</p>
                  <p className="text-sm text-muted-foreground">Overdue</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-destructive/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-primary">{pendingCount}</p>
                  <p className="text-sm text-muted-foreground">Pending</p>
                </div>
                <Clock className="h-8 w-8 text-primary/20" />
              </div>
            </CardContent>
          </Card>
          <Card className="shadow-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-success">{completedCount}</p>
                  <p className="text-sm text-muted-foreground">Submitted</p>
                </div>
                <CheckCircle2 className="h-8 w-8 text-success/20" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Submit Assignments</CardTitle>
            <CardDescription>
              Complete and submit your homework. Submissions appear on your
              teacher&apos;s dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {assignments.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No assignments yet.
                </p>
              ) : (
                assignments.map((assignment) => {
                  const submitted = hasSubmitted(assignment.id);
                  const isOverdue =
                    !submitted && new Date(assignment.dueDate) < new Date();

                  return (
                    <div
                      key={assignment.id}
                      className={cn(
                        "flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50",
                        submitted && "opacity-75"
                      )}
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={cn(
                            "h-10 w-10 rounded-lg flex items-center justify-center",
                            submitted ? "bg-success/10" : "bg-primary/10"
                          )}
                        >
                          {submitted ? (
                            <CheckCircle2 className="h-5 w-5 text-success" />
                          ) : (
                            <FileText className="h-5 w-5 text-primary" />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p
                              className={cn(
                                "font-medium",
                                submitted && "line-through"
                              )}
                            >
                              {assignment.title}
                            </p>
                            {submitted && (
                              <Badge variant="secondary" className="text-xs">
                                Submitted
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {assignment.description}
                          </p>
                          <span
                            className={cn(
                              "text-xs flex items-center gap-1 mt-1",
                              isOverdue ? "text-destructive" : "text-muted-foreground"
                            )}
                          >
                            <Clock className="h-3 w-3" />
                            Due{" "}
                            {formatDistanceToNow(new Date(assignment.dueDate), {
                              addSuffix: true,
                            })}
                          </span>
                        </div>
                      </div>
                      {!submitted && (
                        <Button
                          size="sm"
                          onClick={() =>
                            setSubmitDialog({
                              assignmentId: assignment.id,
                              title: assignment.title,
                            })
                          }
                        >
                          <Upload className="h-4 w-4 mr-1" />
                          Submit
                        </Button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog
        open={!!submitDialog}
        onOpenChange={() => {
          setSubmitDialog(null);
          setSubmitContent("");
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Submit Assignment</DialogTitle>
            <DialogDescription>
              {submitDialog?.title} — Enter your submission below. It will be
              visible to your teacher.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="sub-content">Your submission</Label>
              <Textarea
                id="sub-content"
                value={submitContent}
                onChange={(e) => setSubmitContent(e.target.value)}
                placeholder="Paste your work, write a response, or provide a link..."
                rows={6}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSubmitDialog(null);
                  setSubmitContent("");
                }}
              >
                Cancel
              </Button>
              <Button type="submit">Submit</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default StudentTodo;
