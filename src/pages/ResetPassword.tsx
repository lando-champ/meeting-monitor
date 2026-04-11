import { useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Sparkles, Lock, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { resetPassword } from "@/lib/api";

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = useMemo(() => (searchParams.get("token") || "").trim(), [searchParams]);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const token =
      tokenFromUrl || (form.querySelector("#rp-token") as HTMLInputElement)?.value?.trim();
    const pw = (form.querySelector("#rp-password") as HTMLInputElement)?.value;
    const pw2 = (form.querySelector("#rp-password2") as HTMLInputElement)?.value;
    if (!token) {
      toast({ variant: "destructive", title: "Missing token", description: "Use the link from your email." });
      return;
    }
    if (!pw || pw.length < 6) {
      toast({ variant: "destructive", title: "Invalid password", description: "Use at least 6 characters." });
      return;
    }
    if (pw !== pw2) {
      toast({ variant: "destructive", title: "Passwords do not match" });
      return;
    }
    setIsLoading(true);
    try {
      const res = await resetPassword(token, pw);
      toast({ title: "Password updated", description: res.message });
      form.reset();
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Reset failed",
        description: err instanceof Error ? err.message : "Invalid or expired link.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <nav className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">MeetingAI</span>
          </Link>
        </div>
      </nav>

      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Set new password</CardTitle>
            <CardDescription>Enter a new password for your account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              {!tokenFromUrl && (
                <div className="space-y-2">
                  <Label htmlFor="rp-token">Reset token</Label>
                  <Input id="rp-token" type="text" placeholder="Paste token from email" autoComplete="off" />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="rp-password">New password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="rp-password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10"
                    required
                    minLength={6}
                    autoComplete="new-password"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="rp-password2">Confirm password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="rp-password2"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10"
                    required
                    minLength={6}
                    autoComplete="new-password"
                  />
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Saving…" : "Update password"}
              </Button>
            </form>

            <Button variant="ghost" className="w-full" asChild>
              <Link to="/auth" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ResetPassword;
