import { 
  LayoutDashboard, 
  Calendar, 
  ListTodo, 
  LayoutGrid, 
  Users, 
  BarChart3, 
  Settings,
  Bell,
  Shield,
  Palette,
  Globe,
  CreditCard,
  HelpCircle,
  ChevronRight,
  Github,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { SidebarItem } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useParams } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { getProject, patchProjectGitHub, getGithubWebhookCallbackUrl } from '@/lib/api';
import { Input } from '@/components/ui/input';

function shortDeliveryId(id: string | null | undefined): string {
  if (!id) return "—";
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}

function summarizeGithubWebhookResult(r: Record<string, unknown> | null | undefined): string {
  if (!r || typeof r !== "object") return "";
  if (r.error != null && typeof r.error === "string") return r.error;
  if (typeof r.skipped === "string") return `Skipped: ${r.skipped}`;
  const parts: string[] = [];
  if (typeof r.event === "string") parts.push(r.event);
  if (typeof r.tasks_updated === "number") parts.push(`${r.tasks_updated} task(s) updated`);
  if (typeof r.tasks_finalized_after_ci === "number")
    parts.push(`${r.tasks_finalized_after_ci} finalized after CI`);
  if (Array.isArray(r.keys) && r.keys.length) parts.push(`Keys: ${r.keys.map(String).join(", ")}`);
  if (typeof r.conclusion === "string") parts.push(`CI: ${r.conclusion}`);
  return parts.join(" · ") || (r.ok === false ? "Error" : "OK");
}

const settingsSections = [
  {
    icon: Bell,
    title: 'Notifications',
    description: 'Configure how you receive alerts and updates',
  },
  {
    icon: Shield,
    title: 'Privacy & Security',
    description: 'Manage your account security settings',
  },
  {
    icon: Palette,
    title: 'Appearance',
    description: 'Customize the look and feel',
  },
  {
    icon: Globe,
    title: 'Language & Region',
    description: 'Set your language and timezone preferences',
  },
  {
    icon: CreditCard,
    title: 'Billing & Subscription',
    description: 'Manage your plan and payment methods',
  },
  {
    icon: HelpCircle,
    title: 'Help & Support',
    description: 'Get help and contact support',
  },
];

const ManagerSettings = () => {
  const { workspaceId = "alpha" } = useParams();
  const basePath = `/business/manager/workspaces/${workspaceId}`;
  const { currentWorkspace } = useWorkspace();
  const { token, user } = useAuth();
  const inviteCode = currentWorkspace?.inviteCode ?? "N/A";
  const inviteLink = `${window.location.origin}/join/workspace/${inviteCode}`;
  const handleCopy = (value: string) => {
    void navigator.clipboard.writeText(value);
  };

  const [ghRepo, setGhRepo] = useState("");
  const [ghWebhook, setGhWebhook] = useState(false);
  const [ghLoading, setGhLoading] = useState(true);
  const [ghSaving, setGhSaving] = useState(false);
  const [ghError, setGhError] = useState<string | null>(null);
  const [projectOwnerId, setProjectOwnerId] = useState<string | null>(null);
  const [ghWebhookLastAt, setGhWebhookLastAt] = useState<string | null>(null);
  const [ghWebhookLastEvent, setGhWebhookLastEvent] = useState<string | null>(null);
  const [ghWebhookLastDelivery, setGhWebhookLastDelivery] = useState<string | null>(null);
  const [ghWebhookLastResult, setGhWebhookLastResult] = useState<Record<string, unknown> | null>(null);
  const webhookCallbackUrl = getGithubWebhookCallbackUrl();
  const isProjectOwner = Boolean(user?.id && projectOwnerId && user.id === projectOwnerId);

  const loadGithubProject = useCallback(async () => {
    if (!token || !workspaceId) {
      setGhLoading(false);
      return;
    }
    setGhLoading(true);
    setGhError(null);
    try {
      const p = await getProject(token, workspaceId);
      setProjectOwnerId(p.owner_id);
      setGhRepo((p.github_full_name ?? "").trim());
      setGhWebhook(Boolean(p.github_webhook_enabled));
      setGhWebhookLastAt(p.github_webhook_last_at ?? null);
      setGhWebhookLastEvent(p.github_webhook_last_event ?? null);
      setGhWebhookLastDelivery(p.github_webhook_last_delivery ?? null);
      setGhWebhookLastResult(p.github_webhook_last_result ?? null);
    } catch {
      setGhError("Could not load GitHub settings.");
    } finally {
      setGhLoading(false);
    }
  }, [token, workspaceId]);

  useEffect(() => {
    void loadGithubProject();
  }, [loadGithubProject]);

  const saveGithubSettings = async () => {
    if (!token || !workspaceId || !isProjectOwner) return;
    setGhSaving(true);
    setGhError(null);
    try {
      const updated = await patchProjectGitHub(token, workspaceId, {
        github_full_name: ghRepo.trim(),
        github_webhook_enabled: ghWebhook,
      });
      setGhRepo((updated.github_full_name ?? "").trim());
      setGhWebhook(Boolean(updated.github_webhook_enabled));
      setGhWebhookLastAt(updated.github_webhook_last_at ?? null);
      setGhWebhookLastEvent(updated.github_webhook_last_event ?? null);
      setGhWebhookLastDelivery(updated.github_webhook_last_delivery ?? null);
      setGhWebhookLastResult(updated.github_webhook_last_result ?? null);
    } catch (e) {
      setGhError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setGhSaving(false);
    }
  };
  const managerSidebarItems: SidebarItem[] = [
    { title: 'Dashboard', href: `${basePath}/dashboard`, icon: LayoutDashboard },
    { title: 'Meetings', href: `${basePath}/meetings`, icon: Calendar, badge: 3 },
    { title: 'Tasks', href: `${basePath}/tasks`, icon: ListTodo, badge: 5 },
    { title: 'Kanban Board', href: `${basePath}/kanban`, icon: LayoutGrid },
    { title: 'Team', href: `${basePath}/team`, icon: Users },
    { title: 'Analytics', href: `${basePath}/analytics`, icon: BarChart3, isPremium: true },
    { title: 'Settings', href: `${basePath}/settings`, icon: Settings },
  ];
  return (
    <DashboardLayout
      sidebarItems={managerSidebarItems}
      sidebarTitle="Manager"
      sidebarSubtitle="Business Dashboard"
    >
      <div className="space-y-6 max-w-4xl">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Workspace Invite</CardTitle>
            <CardDescription>Share access to this workspace</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-2">
              <Label>Invite Code</Label>
              <div className="flex items-center gap-2">
                <Button variant="outline" className="justify-start flex-1" disabled>
                  {inviteCode}
                </Button>
                <Button variant="secondary" onClick={() => handleCopy(inviteCode)}>
                  Copy Code
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Invite Link</Label>
              <div className="flex items-center gap-2">
                <Button variant="outline" className="justify-start flex-1" disabled>
                  {inviteLink}
                </Button>
                <Button variant="secondary" onClick={() => handleCopy(inviteLink)}>
                  Copy Link
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5" />
              GitHub integration
            </CardTitle>
            <CardDescription>
              Link a repository so merged pull requests can complete Kanban tasks when the PR mentions a task key.
              Only the project owner can change these settings.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-2">
              <Label>Webhook URL (paste in GitHub → Settings → Webhooks)</Label>
              <div className="flex items-center gap-2 flex-wrap">
                <Button variant="outline" className="justify-start flex-1 min-w-0 font-mono text-xs h-auto py-2 px-3" disabled>
                  <span className="truncate text-left">{webhookCallbackUrl}</span>
                </Button>
                <Button type="button" variant="secondary" onClick={() => handleCopy(webhookCallbackUrl)}>
                  Copy URL
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                If you use a separate API host, set <code className="rounded bg-muted px-1">VITE_API_URL</code> so this URL matches where your backend runs.
              </p>
            </div>
            <Separator />
            {ghLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
              </div>
            ) : (
              <>
                {ghError && <p className="text-sm text-destructive">{ghError}</p>}
                <div className="space-y-2">
                  <Label htmlFor="gh-repo">Repository</Label>
                  <Input
                    id="gh-repo"
                    placeholder="owner/repo"
                    value={ghRepo}
                    onChange={(e) => setGhRepo(e.target.value)}
                    disabled={!isProjectOwner}
                  />
                  <p className="text-xs text-muted-foreground">Lowercase recommended (e.g. acme-corp/mobile-app).</p>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <Label htmlFor="gh-wh-enabled">Deliver webhook events</Label>
                    <p className="text-sm text-muted-foreground">Turn off to ignore GitHub deliveries for this project.</p>
                  </div>
                  <Switch
                    id="gh-wh-enabled"
                    checked={ghWebhook}
                    onCheckedChange={setGhWebhook}
                    disabled={!isProjectOwner}
                  />
                </div>
                {!isProjectOwner && (
                  <p className="text-sm text-muted-foreground">
                    You are not the project owner; repository link is read-only here.
                  </p>
                )}
                {isProjectOwner && (
                  <Button type="button" onClick={() => void saveGithubSettings()} disabled={ghSaving}>
                    {ghSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Save GitHub settings
                  </Button>
                )}
                <Separator />
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <Label>Last GitHub webhook</Label>
                      <p className="text-sm text-muted-foreground">
                        Last delivery handled for this linked repository (UTC time from server).
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void loadGithubProject()}
                      disabled={ghLoading}
                    >
                      {ghLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      <span className="ml-2">Refresh</span>
                    </Button>
                  </div>
                  {!ghWebhookLastAt ? (
                    <p className="text-sm text-muted-foreground">
                      No webhook has been recorded yet. After GitHub sends an event, refresh here to see the outcome.
                    </p>
                  ) : (
                    <div className="rounded-md border bg-muted/30 p-3 space-y-1 text-sm">
                      <p>
                        <span className="text-muted-foreground font-sans">Time (UTC): </span>
                        {new Date(ghWebhookLastAt).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " Z")}
                      </p>
                      <p>
                        <span className="text-muted-foreground font-sans">Event: </span>
                        {ghWebhookLastEvent ?? "—"}
                      </p>
                      <p>
                        <span className="text-muted-foreground font-sans">Delivery: </span>
                        {shortDeliveryId(ghWebhookLastDelivery ?? undefined)}
                      </p>
                      <p className="font-sans pt-1">
                        <span className="text-muted-foreground">Summary: </span>
                        {summarizeGithubWebhookResult(ghWebhookLastResult) || "—"}
                      </p>
                      {ghWebhookLastResult && Object.keys(ghWebhookLastResult).length > 0 ? (
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-muted p-2 text-[11px] leading-relaxed">
                          {JSON.stringify(ghWebhookLastResult, null, 2)}
                        </pre>
                      ) : null}
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account and application preferences
          </p>
        </div>

        {/* Notification Preferences */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notification Preferences
            </CardTitle>
            <CardDescription>Choose what notifications you receive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Task Assignments</Label>
                <p className="text-sm text-muted-foreground">Get notified when tasks are assigned to you</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label>Meeting Summaries</Label>
                <p className="text-sm text-muted-foreground">Receive AI-generated summaries after meetings</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label>Deadline Reminders</Label>
                <p className="text-sm text-muted-foreground">Get reminded about upcoming deadlines</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label>Team Updates</Label>
                <p className="text-sm text-muted-foreground">Notifications about team activity</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        {/* Other Settings */}
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>More Settings</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {settingsSections.map((section, index) => (
              <div key={section.title}>
                <button className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors text-left">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                      <section.icon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{section.title}</p>
                      <p className="text-sm text-muted-foreground">{section.description}</p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground" />
                </button>
                {index < settingsSections.length - 1 && <Separator />}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="shadow-card border-destructive/30">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>Irreversible actions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Export Data</p>
                <p className="text-sm text-muted-foreground">Download all your data</p>
              </div>
              <Button variant="outline">Export</Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Delete Account</p>
                <p className="text-sm text-muted-foreground">Permanently delete your account and data</p>
              </div>
              <Button variant="destructive">Delete Account</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default ManagerSettings;
