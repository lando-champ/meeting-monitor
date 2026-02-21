import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { ClassProvider } from "@/context/ClassContext";
import { EducationProvider } from "@/context/EducationContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { businessRoutes } from "@/routes/businessRoutes";
import { educationRoutes } from "@/routes/educationRoutes";

// Pages
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AuthProvider>
      <WorkspaceProvider>
        <ClassProvider>
          <EducationProvider>
          <BrowserRouter>
            <Routes>
              {/* Public */}
              <Route path="/" element={<Landing />} />
              <Route path="/auth" element={<Auth />} />

              {/* All routes below require login */}
              <Route element={<ProtectedRoute />}>
                <Route path="/profile" element={<Profile />} />
                {businessRoutes}
                {educationRoutes}

                {/* Legacy Redirects */}
              <Route path="/corporate" element={<Navigate to="/business" replace />} />
              <Route path="/corporate/manager" element={<Navigate to="/business/manager/workspaces" replace />} />
              <Route path="/corporate/manager/*" element={<Navigate to="/business/manager/workspaces" replace />} />
                <Route path="/corporate/team-member" element={<Navigate to="/business/member/workspaces" replace />} />
                <Route path="/corporate/team-member/*" element={<Navigate to="/business/member/workspaces" replace />} />
                <Route path="/education/teacher" element={<Navigate to="/education/teacher/classes" replace />} />
                <Route path="/education/teacher/*" element={<Navigate to="/education/teacher/classes" replace />} />
                <Route path="/education/student" element={<Navigate to="/education/student/classes" replace />} />
                <Route path="/education/student/*" element={<Navigate to="/education/student/classes" replace />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
          </EducationProvider>
        </ClassProvider>
      </WorkspaceProvider>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
