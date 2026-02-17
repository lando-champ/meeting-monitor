import { useState } from "react";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useWorkspace } from "@/context/WorkspaceContext";

const JoinWorkspaceModal = () => {
  const { joinWorkspace } = useWorkspace();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  const handleJoin = () => {
    if (!code.trim()) {
      return;
    }
    const result = joinWorkspace(code.trim());
    if (!result) {
      setError("Invite code not found. Check with your manager.");
      return;
    }
    setCode("");
    setError("");
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="secondary">
          <KeyRound className="h-4 w-4 mr-2" />
          Join Project
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Join a project</DialogTitle>
          <DialogDescription>
            Enter an invite code shared by your manager.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            placeholder="Invite code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={handleJoin} disabled={!code.trim()}>
            Join Project
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default JoinWorkspaceModal;
