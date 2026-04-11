import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Mail, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { forgotPassword } from "@/lib/api";

const ForgotPassword = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [devInfo, setDevInfo] = useState<{ reset_url?: string; reset_token?: string } | null>(null);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const email = (form.querySelector("#fp-email") as HTMLInputElement)?.value?.trim();
    if (!email) return;
    setIsLoading(true);
    setDevInfo(null);
    try {
      const res = await forgotPassword(email);
      toast({
        title: "Check your email",
        description: res.message,
      });
      if (res.reset_url || res.reset_token) {
        setDevInfo({ reset_url: res.reset_url, reset_token: res.reset_token });
      }
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Request failed",
        description: err instanceof Error ? err.message : "Could not send reset request.",
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
            <CardTitle className="text-2xl">Forgot password</CardTitle>
            <CardDescription>
              Enter your email. If an account exists, we will send reset instructions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fp-email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input id="fp-email" type="email" placeholder="you@example.com" className="pl-10" required />
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Sending…" : "Send reset link"}
              </Button>
            </form>

            {devInfo?.reset_url && (
              <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm space-y-2">
                <p className="font-medium text-amber-900 dark:text-amber-100">Dev mode: use this link</p>
                <a href={devInfo.reset_url} className="text-primary break-all underline">
                  {devInfo.reset_url}
                </a>
                {devInfo.reset_token && (
                  <p className="text-xs text-muted-foreground break-all">token: {devInfo.reset_token}</p>
                )}
              </div>
            )}

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

export default ForgotPassword;
