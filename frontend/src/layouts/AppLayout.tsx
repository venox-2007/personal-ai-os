import React, { useState } from "react";
import { DesktopTopBar } from "../components/DesktopTopBar";
import { DesktopDock } from "../components/DesktopDock";
import { ActivityPanel } from "../components/ActivityPanel";
import { HealthCheckData, AgentActivityEvent } from "../types";
import { X } from "lucide-react";

interface AppLayoutProps {
  health: HealthCheckData | null;
  activities: AgentActivityEvent[];
  isLoading: boolean;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  health,
  activities,
  isLoading,
  children,
}) => {
  const [isActivityOpen, setIsActivityOpen] = useState(false);

  // We use inline styles for the wallpaper to ensure it covers the viewport properly
  return (
    <div 
      className="flex h-screen w-screen overflow-hidden bg-background text-slate-100 font-sans relative"
      style={{
        backgroundImage: "url('/wallpaper.jpg')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      {/* Dark overlay to ensure contrast against background */}
      <div className="absolute inset-0 bg-slate-950/60 pointer-events-none z-0" />
      
      <div className="flex flex-col h-full w-full relative z-10">
        <DesktopTopBar 
          health={health} 
          onToggleActivity={() => setIsActivityOpen(!isActivityOpen)} 
        />
        
        <main className="flex-1 overflow-hidden relative">
          {children}
        </main>
        
        <DesktopDock />
        
        {/* Activity Drawer - Updated for Dark Theme */}
        {isActivityOpen && (
          <>
            <div 
              className="absolute inset-0 bg-brand-600/40 z-40 backdrop-blur-sm"
              onClick={() => setIsActivityOpen(false)}
            />
            <div className="absolute right-0 top-0 bottom-0 w-80 bg-surface border-l border-white/10 shadow-2xl z-50 flex flex-col transform transition-transform">
              <div className="h-14 border-b border-white/10 flex items-center justify-between px-4 shrink-0 bg-slate-950/50">
                <h3 className="font-semibold text-sm text-slate-200">Activity</h3>
                <button onClick={() => setIsActivityOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden relative bg-surface text-slate-300">
                <ActivityPanel activities={activities} isStreaming={isLoading} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
