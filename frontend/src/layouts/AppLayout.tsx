import React, { useState } from "react";
import { Sidebar, NavItem } from "../components/Sidebar";
import { Header } from "../components/Header";
import { ActivityPanel } from "../components/ActivityPanel";
import { HealthCheckData, AgentActivityEvent } from "../types";
import { X } from "lucide-react";

interface AppLayoutProps {
  activeTab: NavItem;
  onSelectTab: (tab: NavItem) => void;
  health: HealthCheckData | null;
  activities: AgentActivityEvent[];
  isLoading: boolean;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  activeTab,
  onSelectTab,
  health,
  activities,
  isLoading,
  children,
}) => {
  const [isActivityOpen, setIsActivityOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-slate-800 font-sans">
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
      
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <Header 
          currentTab={activeTab} 
          health={health} 
          onToggleActivity={() => setIsActivityOpen(!isActivityOpen)} 
        />
        
        <main className="flex-1 overflow-hidden flex flex-col relative z-0">
          {children}
        </main>
        
        {/* Activity Drawer */}
        {isActivityOpen && (
          <>
            <div 
              className="absolute inset-0 bg-slate-900/10 z-40 backdrop-blur-[1px]"
              onClick={() => setIsActivityOpen(false)}
            />
            <div className="absolute right-0 top-0 bottom-0 w-80 bg-surface border-l border-surface-border shadow-xl z-50 flex flex-col transform transition-transform">
              <div className="h-14 border-b border-surface-border flex items-center justify-between px-4 shrink-0">
                <h3 className="font-semibold text-sm text-slate-800">Activity</h3>
                <button onClick={() => setIsActivityOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden relative">
                <ActivityPanel activities={activities} isStreaming={isLoading} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
