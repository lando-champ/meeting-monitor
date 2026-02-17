import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, Mail, Lock, User, ArrowRight, Building2, GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

const Auth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<'business' | 'education' | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate authentication
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    toast({
      title: "Welcome back!",
      description: "You have successfully signed in.",
    });
    
    // Navigate based on selected domain or default to corporate
    if (selectedDomain === 'education') {
      navigate('/education');
    } else {
      navigate('/business');
    }
    setIsLoading(false);
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate registration
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    toast({
      title: "Account created!",
      description: "Welcome to MeetingAI. Let's get started.",
    });
    
    // Navigate based on selected domain
    if (selectedDomain === 'education') {
      navigate('/education');
    } else {
      navigate('/business');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Navigation */}
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

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-card">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Welcome to MeetingAI</CardTitle>
            <CardDescription>
              Sign in to your account or create a new one
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="signin" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="signin">Sign In</TabsTrigger>
                <TabsTrigger value="signup">Sign Up</TabsTrigger>
              </TabsList>

              <TabsContent value="signin">
                <form onSubmit={handleSignIn} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="signin-email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signin-email" 
                        type="email" 
                        placeholder="you@example.com"
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signin-password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signin-password" 
                        type="password" 
                        placeholder="••••••••"
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  {/* Domain Selection */}
                  <div className="space-y-2">
                    <Label>Sign in as</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <Button
                        type="button"
                        variant={selectedDomain === 'business' ? 'default' : 'outline'}
                        className="h-auto py-3 flex flex-col gap-1"
                        onClick={() => setSelectedDomain('business')}
                      >
                        <Building2 className="h-5 w-5" />
                        <span className="text-xs">Business</span>
                      </Button>
                      <Button
                        type="button"
                        variant={selectedDomain === 'education' ? 'secondary' : 'outline'}
                        className="h-auto py-3 flex flex-col gap-1"
                        onClick={() => setSelectedDomain('education')}
                      >
                        <GraduationCap className="h-5 w-5" />
                        <span className="text-xs">Education</span>
                      </Button>
                    </div>
                  </div>

                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? 'Signing in...' : 'Sign In'}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>

                  <p className="text-center text-sm text-muted-foreground">
                    <a href="#" className="hover:text-primary">Forgot password?</a>
                  </p>
                </form>
              </TabsContent>

              <TabsContent value="signup">
                <form onSubmit={handleSignUp} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="signup-name">Full Name</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signup-name" 
                        type="text" 
                        placeholder="John Doe"
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signup-email" 
                        type="email" 
                        placeholder="you@example.com"
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input 
                        id="signup-password" 
                        type="password" 
                        placeholder="••••••••"
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  {/* Domain Selection */}
                  <div className="space-y-2">
                    <Label>I want to use MeetingAI for</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <Button
                        type="button"
                        variant={selectedDomain === 'business' ? 'default' : 'outline'}
                        className="h-auto py-3 flex flex-col gap-1"
                        onClick={() => setSelectedDomain('business')}
                      >
                        <Building2 className="h-5 w-5" />
                        <span className="text-xs">Business</span>
                      </Button>
                      <Button
                        type="button"
                        variant={selectedDomain === 'education' ? 'secondary' : 'outline'}
                        className="h-auto py-3 flex flex-col gap-1"
                        onClick={() => setSelectedDomain('education')}
                      >
                        <GraduationCap className="h-5 w-5" />
                        <span className="text-xs">Education</span>
                      </Button>
                    </div>
                  </div>

                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? 'Creating account...' : 'Create Account'}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>

                  <p className="text-center text-sm text-muted-foreground">
                    By signing up, you agree to our{' '}
                    <a href="#" className="hover:text-primary">Terms</a> and{' '}
                    <a href="#" className="hover:text-primary">Privacy Policy</a>
                  </p>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Auth;
