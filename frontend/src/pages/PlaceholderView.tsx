import React from "react";
import { NavItem } from "../components/Sidebar";
import { Clock } from "lucide-react";

interface PlaceholderViewProps {
  tab: NavItem;
}

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({ tab }) => {
  const getTabTitle = (t: NavItem) => {
    switch (t) {
      case "calendar": return "Calendar";
      case "tasks": return "Tasks";
      case "memory": return "Memory";
      case "settings": return "Settings";
      default: return "Coming Soon";
    }
  };

  const title = getTabTitle(tab);

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-background">
      <div className="w-16 h-16 rounded-2xl bg-brand-500/10 flex items-center justify-center text-brand-400 mb-6">
        <Clock className="w-8 h-8" />
      </div>
      <h2 className="text-2xl font-semibold text-slate-200 mb-2">{title}</h2>
      <p className="text-slate-400 text-center max-w-sm leading-relaxed">
        This feature is currently in development. It will be available in a future update.
      </p>
    </div>
  );
};
