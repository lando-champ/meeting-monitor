import { useEffect, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useClass } from "@/context/ClassContext";

const ClassSwitcher = () => {
  const { classes, currentClassId, setCurrentClassId, role, setRole, hasAccessToClass } = useClass();
  const location = useLocation();
  const navigate = useNavigate();

  const derivedRole = useMemo(() => {
    if (location.pathname.includes("/education/teacher/")) {
      return "teacher";
    }
    if (location.pathname.includes("/education/student/")) {
      return "student";
    }
    return null;
  }, [location.pathname]);

  useEffect(() => {
    if (derivedRole && role !== derivedRole) {
      setRole(derivedRole);
    }
  }, [derivedRole, role, setRole]);

  if (!derivedRole) {
    return null;
  }

  const basePath =
    derivedRole === "teacher" ? "/education/teacher/classes" : "/education/student/classes";

  const visibleClasses =
    role === "student" ? classes.filter((cls) => hasAccessToClass(cls.id)) : classes;
  const activeClass = visibleClasses.find((cls) => cls.id === currentClassId) ?? visibleClasses[0];

  const handleSwitch = (classId: string) => {
    setCurrentClassId(classId);
    navigate(`${basePath}/${classId}/dashboard`);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" className="w-full justify-between">
          <span className="flex items-center gap-2 truncate">
            <GraduationCap className="h-4 w-4" />
            {activeClass?.name ?? "Select class"}
          </span>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Classes</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {visibleClasses.map((cls) => (
          <DropdownMenuItem key={cls.id} onClick={() => handleSwitch(cls.id)}>
            <span className="truncate">{cls.name}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ClassSwitcher;
