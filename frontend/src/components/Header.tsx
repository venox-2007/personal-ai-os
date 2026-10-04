import React from "react";
import { NavItem } from "./Sidebar";
import { HealthCheckData } from "../types";
import { Activity } from "lucide-react";

interface HeaderProps {
  currentTab: NavItem;
  health: HealthCheckData | null;
  onToggleActivity?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onToggleActivity }) => {
  const getTabName = () => {
    switch (currentTab) {
      case "home": return "Home";
      case "calendar": return "Calendar";
      case "tasks": return "Tasks";
      case "study": return "Study";
      case "coding": return "Coding";
      case "research": return "Research";
      case "files": return "Files";
      case "memory": return "Memory";
      case "settings": return "Settings";
      default: return "";
    }
  };

  return (
    <header className="h-14 border-b border-surface-border bg-surface flex items-center justify-between px-6 shrink-0">
      <h2 className="text-sm font-semibold text-slate-800 capitalize tracking-wide">{getTabName()}</h2>
      <div className="flex items-center gap-3">
        {onToggleActivity && (
          <button 
            onClick={onToggleActivity}
            className="p-1.5 text-slate-500 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors flex items-center gap-2"
          >
            <Activity className="w-4 h-4" />
            <span className="text-xs font-medium">Activity</span>
          </button>
        )}
      </div>
    </header>
  );
};
