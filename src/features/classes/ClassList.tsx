import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Users, ArrowRight, Trash2, Trash } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useClass, ClassRole } from "@/context/ClassContext";
import CreateClassModal from "./CreateClassModal";
import JoinClassModal from "./JoinClassModal";

interface ClassListProps {
  role: ClassRole;
}

const ClassList = ({ role }: ClassListProps) => {
  const { classes, currentClassId, setRole, hasAccessToClass, deleteClass, deleteAllClasses, currentUserEmail } = useClass();
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [showDeleteAllDialog, setShowDeleteAllDialog] = useState(false);

  useEffect(() => {
    setRole(role);
  }, [role, setRole]);

  const basePath = useMemo(
    () => (role === "teacher" ? "/education/teacher/classes" : "/education/student/classes"),
    [role],
  );

  const canCreate = role === "teacher";
  const visibleClasses =
    role === "teacher" ? classes : classes.filter((cls) => hasAccessToClass(cls.id));
  const myClassCount = visibleClasses.length;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50">
        <div className="container mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {role === "teacher" ? "Your Classes" : "Enrolled Classes"}
            </h1>
            <p className="text-muted-foreground">
              {role === "teacher"
                ? "Create and manage classes for your students."
                : "Join a class to access lecture materials."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {myClassCount > 0 && (
              <Button
                variant="outline"
                className="text-destructive border-destructive/50 hover:bg-destructive/10"
                onClick={() => setShowDeleteAllDialog(true)}
              >
                <Trash className="h-4 w-4 mr-2" />
                Delete all classes
              </Button>
            )}
            {canCreate ? <CreateClassModal /> : <JoinClassModal />}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-10 space-y-8">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleClasses.map((cls) => (
            <Card key={cls.id} className="shadow-card">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Badge variant="secondary">{cls.id}</Badge>
                  {currentClassId === cls.id && (
                    <Badge className="bg-success/10 text-success border border-success/20">
                      Active
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-lg">{cls.name}</CardTitle>
                <CardDescription className="space-y-2">
                  <span className="block text-sm">{cls.description}</span>
                  <span className="inline-flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    {cls.studentCount} students
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-2">
                <Button variant="outline" asChild>
                  <Link to={`${basePath}/${cls.id}/dashboard`}>
                    Open Class
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive border-destructive/50 hover:bg-destructive/10"
                    onClick={() => setDeleteTargetId(cls.id)}
                    aria-label="Delete class"
                  >
                    <Trash2 className="h-4 w-4 mr-1.5" />
                    Delete
                  </Button>
                  {role === "teacher" ? (
                    <Badge className="bg-secondary/10 text-secondary border border-secondary/20">
                      Instructor
                    </Badge>
                  ) : (
                    <Badge className="bg-muted text-muted-foreground border border-muted">Student</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>

      <AlertDialog open={!!deleteTargetId} onOpenChange={(open) => !open && setDeleteTargetId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete class?</AlertDialogTitle>
            <AlertDialogDescription>
              You will leave this class. It will no longer appear on your dashboard and your name will be removed from the class. You can re-enroll later with an invite code.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={async () => {
                if (deleteTargetId) {
                  await deleteClass(deleteTargetId);
                  setDeleteTargetId(null);
                }
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={showDeleteAllDialog} onOpenChange={setShowDeleteAllDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete all classes?</AlertDialogTitle>
            <AlertDialogDescription>
              You will leave all {myClassCount} class(es). They will no longer appear on your dashboard and your name will be removed from the classes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={async () => {
                await deleteAllClasses();
                setShowDeleteAllDialog(false);
              }}
            >
              Delete all
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ClassList;
