import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Lock, Sparkles } from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import WorkspaceSwitcher from '@/features/workspaces/WorkspaceSwitcher';

export interface SidebarItem {
  title: string;
  href: string;
  icon: LucideIcon;
  badge?: number;
  isPremium?: boolean;
}

interface SidebarProps {
  items: SidebarItem[];
  title: string;
  subtitle?: string;
}

const Sidebar = ({ items, title, subtitle }: SidebarProps) => {
  const location = useLocation();

  const showWorkspaceSwitcher =
    location.pathname.includes("/business/manager/") ||
    location.pathname.includes("/business/member/");

  return (
    <aside className="w-64 border-r bg-sidebar min-h-screen flex flex-col">
      {/* Logo/Brand */}
      <div className="p-6 border-b">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg">MeetingAI</span>
        </Link>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-2">{subtitle}</p>
        )}
        {showWorkspaceSwitcher && (
          <div className="mt-4 space-y-2">
            <WorkspaceSwitcher />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-4 px-3">
          {title}
        </p>
        <ul className="space-y-1">
          {items.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive 
                      ? "bg-sidebar-accent text-sidebar-accent-foreground" 
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                    item.isPremium && "opacity-75"
                  )}
                >
                  <Icon className={cn(
                    "h-5 w-5",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )} />
                  <span className="flex-1">{item.title}</span>
                  {item.badge && (
                    <Badge variant="secondary" className="h-5 min-w-5 px-1.5 text-xs">
                      {item.badge}
                    </Badge>
                  )}
                  {item.isPremium && (
                    <Lock className="h-3.5 w-3.5 text-premium" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Upgrade CTA */}
      <div className="p-4 border-t">
        <div className="p-4 rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20">
          <p className="font-medium text-sm mb-1">Upgrade to Pro</p>
          <p className="text-xs text-muted-foreground mb-3">
            Unlock advanced analytics and AI coaching
          </p>
          <Link
            to="#"
            className="inline-flex items-center text-xs font-medium text-primary hover:underline"
          >
            Learn more →
          </Link>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
