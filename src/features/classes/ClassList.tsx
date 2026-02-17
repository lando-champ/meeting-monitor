import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Users, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useClass, ClassRole } from "@/context/ClassContext";
import CreateClassModal from "./CreateClassModal";
import JoinClassModal from "./JoinClassModal";

interface ClassListProps {
  role: ClassRole;
}

const ClassList = ({ role }: ClassListProps) => {
  const { classes, currentClassId, setRole, hasAccessToClass } = useClass();

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
              <CardContent className="flex items-center justify-between">
                <Button variant="outline" asChild>
                  <Link to={`${basePath}/${cls.id}/dashboard`}>
                    Open Class
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
                {role === "teacher" ? (
                  <Badge className="bg-secondary/10 text-secondary border border-secondary/20">
                    Instructor
                  </Badge>
                ) : (
                  <Badge className="bg-muted text-muted-foreground border border-muted">Student</Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

      </main>
    </div>
  );
};

export default ClassList;
