import { Link } from 'react-router-dom';
import { 
  Building2, 
  GraduationCap, 
  Mic, 
  ListTodo, 
  LayoutDashboard, 
  TrendingUp,
  CheckCircle2,
  Lock,
  Sparkles,
  ArrowRight,
  Play,
  Users,
  Clock,
  Zap,
  User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/context/AuthContext';

const Landing = () => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">MeetingAI</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#pricing" className="text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
            <a href="#testimonials" className="text-muted-foreground hover:text-foreground transition-colors">Testimonials</a>
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.avatar ?? undefined} alt={user.name} />
                      <AvatarFallback>{user.name.split(' ').map(n => n[0]).join('') || 'U'}</AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline font-medium">{user.name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem asChild>
                    <Link to="/profile" className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Profile
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => logout()}
                  >
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <Link to="/auth">
                  <Button variant="outline">Sign In</Button>
                </Link>
                <Link to="/auth">
                  <Button>Sign Up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 lg:py-32">
        <div className="max-w-4xl mx-auto text-center">
          <Badge variant="secondary" className="mb-6 px-4 py-2">
            <Sparkles className="h-3 w-3 mr-2" />
            AI-Powered Meeting Intelligence
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            Every output derived{' '}
            <span className="text-primary">only from what's spoken</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Transform your meetings into actionable insights. Automatic transcription, 
            task extraction, and productivity tracking—all powered by AI.
          </p>

          {/* Domain Selection Cards */}
          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            <Link to="/business" className="group">
              <Card className="h-full shadow-card hover:shadow-hover transition-all duration-300 border-2 border-transparent hover:border-primary/20">
                <CardHeader className="text-center pb-4">
                  <div className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <Building2 className="h-8 w-8 text-primary" />
                  </div>
                  <CardTitle className="text-2xl">For Business</CardTitle>
                  <CardDescription className="text-base">
                    Managers & Teams
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <ul className="space-y-3 text-sm text-muted-foreground mb-6">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Team productivity analytics
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Auto-updated Kanban boards
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Smart task assignments
                    </li>
                  </ul>
                  <Button className="w-full group-hover:bg-primary/90">
                    Get Started
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>
            </Link>

            <Link to="/education" className="group">
              <Card className="h-full shadow-card hover:shadow-hover transition-all duration-300 border-2 border-transparent hover:border-secondary/20">
                <CardHeader className="text-center pb-4">
                  <div className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-secondary/10 flex items-center justify-center group-hover:bg-secondary/20 transition-colors">
                    <GraduationCap className="h-8 w-8 text-secondary" />
                  </div>
                  <CardTitle className="text-2xl">For Education</CardTitle>
                  <CardDescription className="text-base">
                    Teachers & Students
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <ul className="space-y-3 text-sm text-muted-foreground mb-6">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Lecture transcription & summaries
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Auto-generated to-do lists
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Assignment tracking
                    </li>
                  </ul>
                  <Button variant="secondary" className="w-full">
                    Get Started
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything extracted from meetings
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              No manual input required. Our AI listens, understands, and acts.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="shadow-card border-0 bg-card">
              <CardHeader>
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                  <Mic className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-lg">Live Transcription</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  Real-time speech-to-text with speaker detection. Every word captured accurately.
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-card border-0 bg-card">
              <CardHeader>
                <div className="h-12 w-12 rounded-xl bg-secondary/10 flex items-center justify-center mb-4">
                  <ListTodo className="h-6 w-6 text-secondary" />
                </div>
                <CardTitle className="text-lg">Auto Task Extraction</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  AI identifies action items, assigns owners, and sets deadlines automatically.
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-card border-0 bg-card">
              <CardHeader>
                <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center mb-4">
                  <LayoutDashboard className="h-6 w-6 text-success" />
                </div>
                <CardTitle className="text-lg">Smart Kanban</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  Boards that update themselves based on meeting discussions.
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-card border-0 bg-card">
              <CardHeader>
                <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center mb-4">
                  <TrendingUp className="h-6 w-6 text-warning" />
                </div>
                <CardTitle className="text-lg">Productivity Insights</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">
                  Track team performance, identify bottlenecks, and optimize workflows.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">How it works</h2>
            <p className="text-muted-foreground text-lg">Three simple steps to transform your meetings</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="mx-auto mb-6 h-16 w-16 rounded-full gradient-primary flex items-center justify-center text-2xl font-bold text-primary-foreground">
                1
              </div>
              <h3 className="text-xl font-semibold mb-3">Start or Upload</h3>
              <p className="text-muted-foreground">
                Begin a live meeting with our AI or upload a recording for analysis.
              </p>
            </div>

            <div className="text-center">
              <div className="mx-auto mb-6 h-16 w-16 rounded-full gradient-primary flex items-center justify-center text-2xl font-bold text-primary-foreground">
                2
              </div>
              <h3 className="text-xl font-semibold mb-3">AI Processes</h3>
              <p className="text-muted-foreground">
                Our AI transcribes, summarizes, and extracts all action items automatically.
              </p>
            </div>

            <div className="text-center">
              <div className="mx-auto mb-6 h-16 w-16 rounded-full gradient-primary flex items-center justify-center text-2xl font-bold text-primary-foreground">
                3
              </div>
              <h3 className="text-xl font-semibold mb-3">Take Action</h3>
              <p className="text-muted-foreground">
                Tasks appear in your dashboard, Kanban updates, and deadlines are tracked.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section id="testimonials" className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Trusted by teams everywhere</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <Card className="shadow-card border-0">
              <CardContent className="pt-6">
                <p className="text-muted-foreground mb-6">
                  "Finally, a tool that actually captures what matters in meetings. My team's productivity jumped 40%."
                </p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <Users className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">Sarah Chen</p>
                    <p className="text-xs text-muted-foreground">Product Manager, TechCorp</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-card border-0">
              <CardContent className="pt-6">
                <p className="text-muted-foreground mb-6">
                  "My students never miss an assignment now. The AI extracts everything they need from my lectures."
                </p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-secondary/10 flex items-center justify-center">
                    <GraduationCap className="h-5 w-5 text-secondary" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">Prof. James Wilson</p>
                    <p className="text-xs text-muted-foreground">Computer Science, MIT</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-card border-0">
              <CardContent className="pt-6">
                <p className="text-muted-foreground mb-6">
                  "The auto-updated Kanban board is a game changer. No more status update meetings!"
                </p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-success/10 flex items-center justify-center">
                    <Zap className="h-5 w-5 text-success" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">Emily Rodriguez</p>
                    <p className="text-xs text-muted-foreground">Engineering Lead, StartupXYZ</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Simple, transparent pricing</h2>
            <p className="text-muted-foreground text-lg">Start free, upgrade when you need more</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Free Tier */}
            <Card className="shadow-card">
              <CardHeader>
                <CardTitle className="text-2xl">Free</CardTitle>
                <CardDescription>Perfect for getting started</CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold">$0</span>
                  <span className="text-muted-foreground">/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-4 mb-8">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>Up to 5 meetings/month</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>AI transcription & summaries</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>Basic task extraction</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>Personal Kanban board</span>
                  </li>
                  <li className="flex items-center gap-3 text-muted-foreground">
                    <Lock className="h-5 w-5 flex-shrink-0" />
                    <span>Team analytics</span>
                  </li>
                  <li className="flex items-center gap-3 text-muted-foreground">
                    <Lock className="h-5 w-5 flex-shrink-0" />
                    <span>AI coaching chatbot</span>
                  </li>
                </ul>
                <Button variant="outline" className="w-full">Get Started Free</Button>
              </CardContent>
            </Card>

            {/* Pro Tier */}
            <Card className="shadow-card border-2 border-premium/30 relative overflow-hidden">
              <div className="absolute top-0 right-0 px-4 py-1 gradient-premium text-premium-foreground text-sm font-medium rounded-bl-lg">
                Popular
              </div>
              <CardHeader>
                <CardTitle className="text-2xl">Pro</CardTitle>
                <CardDescription>For teams that want more</CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold">$19</span>
                  <span className="text-muted-foreground">/user/month</span>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-4 mb-8">
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>Unlimited meetings</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0" />
                    <span>Everything in Free</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-premium flex-shrink-0" />
                    <span className="flex items-center gap-2">
                      Team productivity analytics
                      <Badge className="gradient-premium text-premium-foreground text-xs">Pro</Badge>
                    </span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-premium flex-shrink-0" />
                    <span className="flex items-center gap-2">
                      AI coaching chatbot
                      <Badge className="gradient-premium text-premium-foreground text-xs">Pro</Badge>
                    </span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-premium flex-shrink-0" />
                    <span className="flex items-center gap-2">
                      Advanced moderation insights
                      <Badge className="gradient-premium text-premium-foreground text-xs">Pro</Badge>
                    </span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-premium flex-shrink-0" />
                    <span>Priority support</span>
                  </li>
                </ul>
                <Button className="w-full gradient-primary hover:opacity-90">
                  Start Free Trial
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to transform your meetings?
          </h2>
          <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto">
            Join thousands of teams already using MeetingAI to save time and boost productivity.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="gradient-primary hover:opacity-90">
              <Play className="h-5 w-5 mr-2" />
              Get Started Free
            </Button>
            <Button size="lg" variant="outline">
              <Clock className="h-5 w-5 mr-2" />
              Book a Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">MeetingAI</span>
            </div>
            <p className="text-muted-foreground text-sm">
              © 2025 MeetingAI. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
