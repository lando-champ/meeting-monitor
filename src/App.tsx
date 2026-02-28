import { Component, type ReactNode } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { businessRoutes } from "@/routes/businessRoutes";

// Pages
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

class AuthErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error: Error) {
    if (error?.message?.includes("useAuth must be used within AuthProvider")) {
      this.setState({ hasError: true });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="text-center space-y-2">
            <p className="text-muted-foreground">Session issue. Redirecting to login…</p>
            <a href="/auth" className="text-primary underline">Go to login</a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AuthProvider>
      <WorkspaceProvider>
          <AuthErrorBoundary>
          <BrowserRouter>
            <Routes>
              {/* Public */}
              <Route path="/" element={<Landing />} />
              <Route path="/auth" element={<Auth />} />

              {/* All routes below require login */}
              <Route element={<ProtectedRoute />}>
                <Route path="/profile" element={<Profile />} />
                {businessRoutes}

                {/* Legacy Redirects */}
                <Route path="/corporate" element={<Navigate to="/business" replace />} />
                <Route path="/corporate/manager" element={<Navigate to="/business/manager/workspaces" replace />} />
                <Route path="/corporate/manager/*" element={<Navigate to="/business/manager/workspaces" replace />} />
                <Route path="/corporate/team-member" element={<Navigate to="/business/member/workspaces" replace />} />
                <Route path="/corporate/team-member/*" element={<Navigate to="/business/member/workspaces" replace />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
          </AuthErrorBoundary>
      </WorkspaceProvider>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
