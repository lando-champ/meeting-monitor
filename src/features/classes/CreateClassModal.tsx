import { useMemo, useState } from "react";
import { GraduationCap } from "lucide-react";
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

const CreateClassModal = () => {
  const { createClass } = useClass();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const isValid = useMemo(
    () => Boolean(name.trim() && description.trim() && inviteCode.trim()),
    [name, description, inviteCode],
  );

  const generateCode = () => {
    const seed = Math.random().toString(36).slice(2, 8).toUpperCase();
    setInviteCode(`CL-${seed}`);
  };

  const handleCreate = () => {
    if (!isValid) {
      return;
    }
    createClass(name.trim(), description.trim(), inviteCode.trim());
    setName("");
    setDescription("");
    setInviteCode("");
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="secondary">
          <GraduationCap className="h-4 w-4 mr-2" />
          Create Class
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a new class</DialogTitle>
          <DialogDescription>
            Set up a class and invite students to join.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            placeholder="Class name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Input
            placeholder="Class description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <div className="flex items-center gap-2">
            <Input
              placeholder="Invite code"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value)}
            />
            <Button type="button" variant="outline" onClick={generateCode}>
              Generate
            </Button>
          </div>
          <div className="text-xs text-muted-foreground">
            Invite codes are required and cannot be changed after creation.
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={handleCreate} disabled={!isValid}>
            Create Class
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CreateClassModal;
