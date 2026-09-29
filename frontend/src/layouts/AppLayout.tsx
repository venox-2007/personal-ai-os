import React from "react";
import { Sidebar, NavItem } from "../components/Sidebar";
import { Header } from "../components/Header";
import { HealthCheckData } from "../types";

interface AppLayoutProps {
  activeTab: NavItem;
  onSelectTab: (tab: NavItem) => void;
  health: HealthCheckData | null;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  activeTab,
  onSelectTab,
  health,
  children,
}) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-slate-100 font-sans">
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header currentTab={activeTab} health={health} />
        <main className="flex-1 overflow-hidden flex flex-col">{children}</main>
      </div>
    </div>
  );
};
