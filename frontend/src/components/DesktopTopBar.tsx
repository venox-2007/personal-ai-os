import React, { useState, useEffect } from "react";
import { HealthCheckData } from "../types";
import { Wifi, Battery, Activity } from "lucide-react";

interface TopBarProps {
  health: HealthCheckData | null;
  onToggleActivity?: () => void;
}

export const DesktopTopBar: React.FC<TopBarProps> = ({ health, onToggleActivity }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  const formatDate = (date: Date) => {
    return date.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <header className="h-8 bg-slate-950/40 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-4 text-xs font-medium text-slate-300 select-none z-50">
      {/* Left items */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
          <div className="w-4 h-4 bg-brand-500 rounded flex items-center justify-center text-[10px] font-bold text-white">A</div>
          <span className="font-semibold tracking-wide text-slate-100">Personal AI OS</span>
        </div>
      </div>

      {/* Right items */}
      <div className="flex items-center gap-4 h-full">
        {onToggleActivity && (
          <button 
            onClick={onToggleActivity}
            className="flex items-center gap-1.5 px-2 h-full hover:bg-white/10 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Activity</span>
          </button>
        )}
        
        <div className="flex items-center gap-3 px-2">
          {health?.status === "ok" ? (
            <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" title="Backend OK" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]" title="Backend Offline" />
          )}
          <Wifi className="w-3.5 h-3.5" />
          <Battery className="w-4 h-4" />
        </div>
        
        <div className="flex items-center gap-3 px-2 h-full hover:bg-white/10 transition-colors cursor-default">
          <span>{formatDate(time)}</span>
          <span className="font-semibold">{formatTime(time)}</span>
        </div>
      </div>
    </header>
  );
};
