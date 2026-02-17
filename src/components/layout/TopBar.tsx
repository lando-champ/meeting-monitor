import { Bell, Search, Radio, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { mockNotifications } from '@/data/mockData';

interface TopBarProps {
  userName?: string;
  userRole?: string;
  userAvatar?: string;
  showMeetingStatus?: boolean;
}

const TopBar = ({ 
  userName = "Sarah Chen", 
  userRole = "Product Manager",
  userAvatar = "https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah",
  showMeetingStatus = true
}: TopBarProps) => {
  const unreadCount = mockNotifications.filter(n => !n.isRead).length;

  return (
    <header className="h-16 border-b bg-card flex items-center justify-between px-6">
      {/* Left side - Search */}
      <div className="flex items-center gap-4 flex-1">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search meetings, tasks, notes..." 
            className="pl-10 bg-muted/50 border-0"
          />
        </div>
      </div>

      {/* Center - Meeting Status */}
      {showMeetingStatus && (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 text-success">
            <Radio className="h-3 w-3 animate-pulse" />
            <span className="text-sm font-medium">Live Meeting</span>
          </div>
          <Badge variant="outline" className="text-muted-foreground">
            Weekly Standup • 15:32
          </Badge>
        </div>
      )}

      {/* Right side - Actions */}
      <div className="flex items-center gap-2 flex-1 justify-end">
        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 bg-popover">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {mockNotifications.slice(0, 4).map((notification) => (
              <DropdownMenuItem key={notification.id} className="flex flex-col items-start gap-1 p-3">
                <div className="flex items-center gap-2 w-full">
                  <span className="font-medium text-sm">{notification.title}</span>
                  {!notification.isRead && (
                    <span className="h-2 w-2 rounded-full bg-primary ml-auto" />
                  )}
                </div>
                <span className="text-xs text-muted-foreground">{notification.message}</span>
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-center justify-center text-primary">
              View all notifications
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2">
              <Avatar className="h-8 w-8">
                <AvatarImage src={userAvatar} alt={userName} />
                <AvatarFallback>{userName.split(' ').map(n => n[0]).join('')}</AvatarFallback>
              </Avatar>
              <div className="hidden md:flex flex-col items-start">
                <span className="text-sm font-medium">{userName}</span>
                <span className="text-xs text-muted-foreground">{userRole}</span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 bg-popover">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile Settings</DropdownMenuItem>
            <DropdownMenuItem>Team Settings</DropdownMenuItem>
            <DropdownMenuItem>Billing</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default TopBar;
