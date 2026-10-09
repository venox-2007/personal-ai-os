import React from "react";
import { NavItem } from "./Sidebar";
import { 
  Home, 
  MessageSquare,
  Search, 
  GraduationCap, 
  Code2, 
  FolderTree, 
  Calendar, 
  Database,
  Network
} from "lucide-react";

interface DesktopDockProps {
  activeTab: NavItem;
  onSelectTab: (tab: NavItem) => void;
}

export const DesktopDock: React.FC<DesktopDockProps> = ({ activeTab, onSelectTab }) => {
  const dockItems: { id: NavItem; label: string; icon: React.ReactNode; color: string }[] = [
    { id: "desktop", label: "Overview", icon: <Home className="w-5 h-5" />, color: "text-slate-300" },
    { id: "home", label: "AI Assistant", icon: <MessageSquare className="w-5 h-5" />, color: "text-brand-400" },
    { id: "research", label: "Research", icon: <Search className="w-5 h-5" />, color: "text-cyan-400" },
    { id: "study", label: "Study", icon: <GraduationCap className="w-5 h-5" />, color: "text-emerald-400" },
    { id: "coding", label: "Coding", icon: <Code2 className="w-5 h-5" />, color: "text-orange-400" },
    { id: "files", label: "Files", icon: <FolderTree className="w-5 h-5" />, color: "text-yellow-400" },
    { id: "calendar", label: "Calendar", icon: <Calendar className="w-5 h-5" />, color: "text-rose-400" },
    { id: "memory", label: "Memory", icon: <Database className="w-5 h-5" />, color: "text-purple-400" },
    { id: "workflows", label: "Workflows", icon: <Network className="w-5 h-5" />, color: "text-indigo-400" },
  ];

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50">
      <div className="flex items-center gap-2 p-2 bg-surface/60 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
        {dockItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <div key={item.id} className="relative group">
              <button
                onClick={() => onSelectTab(item.id)}
                className={`w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-300 ${
                  isActive 
                    ? "bg-surface/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.2)]" 
                    : "hover:bg-surface/10 hover:-translate-y-1"
                }`}
              >
                <div className={`${isActive ? item.color : "text-slate-400 group-hover:text-slate-200"} transition-colors`}>
                  {item.icon}
                </div>
                
                {/* Active indicator dot */}
                {isActive && (
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-surface rounded-full opacity-80" />
                )}
              </button>
              
              {/* Tooltip */}
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-3 py-1 bg-surface-secondary border border-white/10 text-white text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap shadow-lg">
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
