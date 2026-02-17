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
import { useClass } from "@/context/ClassContext";

const JoinClassModal = () => {
  const { joinClass } = useClass();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  const handleJoin = () => {
    if (!code.trim()) {
      return;
    }
    const result = joinClass(code.trim());
    if (!result) {
      setError("Invite code not found. Check with your teacher.");
      return;
    }
    setCode("");
    setError("");
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>
          <KeyRound className="h-4 w-4 mr-2" />
          Join Class
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Join a class</DialogTitle>
          <DialogDescription>
            Enter the invite code or link shared by your teacher.
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
            Join Class
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default JoinClassModal;
