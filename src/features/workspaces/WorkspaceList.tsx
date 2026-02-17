import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Users, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useWorkspace, WorkspaceRole } from "@/context/WorkspaceContext";
import CreateWorkspaceModal from "./CreateWorkspaceModal";
import JoinWorkspaceModal from "./JoinWorkspaceModal";

interface WorkspaceListProps {
  role: WorkspaceRole;
}

const WorkspaceList = ({ role }: WorkspaceListProps) => {
  const { workspaces, currentWorkspaceId, setRole, hasAccessToWorkspace } = useWorkspace();

  useEffect(() => {
    setRole(role);
  }, [role, setRole]);

  const basePath = useMemo(
    () => (role === "manager" ? "/business/manager/workspaces" : "/business/member/workspaces"),
    [role],
  );

  const canCreate = role === "manager";

  const visibleWorkspaces =
    role === "manager" ? workspaces : workspaces.filter((workspace) => hasAccessToWorkspace(workspace.id));

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50">
        <div className="container mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {role === "manager" ? "Your Projects" : "Joined Projects"}
            </h1>
            <p className="text-muted-foreground">
              {role === "manager"
                ? "Create and manage workspaces for your teams."
                : "Join a project to access your workspace tools."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {canCreate ? (
              <CreateWorkspaceModal />
            ) : (
              <JoinWorkspaceModal />
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-10 space-y-8">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleWorkspaces.map((workspace) => (
            <Card key={workspace.id} className="shadow-card">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Badge variant="secondary">{workspace.id}</Badge>
                  {currentWorkspaceId === workspace.id && (
                    <Badge className="bg-success/10 text-success border border-success/20">
                      Active
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-lg">{workspace.name}</CardTitle>
                <CardDescription className="space-y-2">
                  <span className="block text-sm">{workspace.description}</span>
                  <span className="inline-flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    {workspace.membersCount} members
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <Button variant="outline" asChild>
                  <Link to={`${basePath}/${workspace.id}/dashboard`}>
                    Open Workspace
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
                {role === "manager" ? (
                  <Badge className="bg-primary/10 text-primary border border-primary/20">Owner</Badge>
                ) : (
                  <Badge className="bg-muted text-muted-foreground border border-muted">Member</Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

      </main>
    </div>
  );
};

export default WorkspaceList;
