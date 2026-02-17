import { ReactNode } from 'react';
import Sidebar, { SidebarItem } from './Sidebar';
import TopBar from './TopBar';

interface DashboardLayoutProps {
  children: ReactNode;
  sidebarItems: SidebarItem[];
  sidebarTitle: string;
  sidebarSubtitle?: string;
  userName?: string;
  userRole?: string;
  userAvatar?: string;
  showMeetingStatus?: boolean;
}

const DashboardLayout = ({
  children,
  sidebarItems,
  sidebarTitle,
  sidebarSubtitle,
  userName,
  userRole,
  userAvatar,
  showMeetingStatus = true,
}: DashboardLayoutProps) => {
  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar 
        items={sidebarItems} 
        title={sidebarTitle}
        subtitle={sidebarSubtitle}
      />
      <div className="flex-1 flex flex-col">
        <TopBar 
          userName={userName}
          userRole={userRole}
          userAvatar={userAvatar}
          showMeetingStatus={showMeetingStatus}
        />
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
