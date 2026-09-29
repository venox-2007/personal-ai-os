import React from "react";
import {
  Home,
  Mail,
  Calendar,
  GraduationCap,
  Code2,
  Compass,
  FolderTree,
  Database,
  ShieldCheck,
  Cpu,
} from "lucide-react";

export type NavItem =
  | "home"
  | "gmail"
  | "calendar"
  | "study"
  | "coding"
  | "research"
  | "files"
  | "memory"
  | "security";

interface SidebarProps {
  activeTab: NavItem;
  onSelectTab: (tab: NavItem) => void;
}

interface NavConfig {
  id: NavItem;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  tag?: string;
}

const NAV_ITEMS: NavConfig[] = [
  { id: "home", label: "Orchestrator", icon: Home },
  { id: "gmail", label: "Gmail Agent", icon: Mail, tag: "Phase 2" },
  { id: "calendar", label: "Calendar Agent", icon: Calendar, tag: "Phase 2" },
  { id: "study", label: "Study Agent", icon: GraduationCap, tag: "Phase 3" },
  { id: "coding", label: "Coding Agent", icon: Code2, tag: "Phase 3" },
  { id: "research", label: "Research Agent", icon: Compass, tag: "Phase 4" },
  { id: "files", label: "File Agent", icon: FolderTree, tag: "Phase 4" },
  { id: "memory", label: "Memory Bank", icon: Database },
  { id: "security", label: "Security & Levels", icon: ShieldCheck },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  return (
    <aside className="w-64 bg-surface border-r border-surface-border flex flex-col h-full select-none">
      {/* Brand logo & OS header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-surface-border">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-wide text-white">Personal AI OS</h1>
          <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            v0.1.0 • Local-first
          </span>
        </div>
      </div>

      {/* Navigation menu */}
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Workspace Agents
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-brand-600/20 text-brand-500 border border-brand-500/30"
                  : "text-slate-300 hover:bg-surface-secondary hover:text-white"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-brand-500" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.tag && (
                <span className="text-[10px] bg-surface-secondary text-slate-400 px-1.5 py-0.5 rounded border border-surface-border font-mono">
                  {item.tag}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer system details */}
      <div className="p-4 border-t border-surface-border text-slate-400 text-[11px] space-y-1">
        <div className="flex justify-between items-center text-slate-300">
          <span>Cost Target:</span>
          <span className="text-emerald-400 font-mono">₹0 / month</span>
        </div>
        <div className="flex justify-between items-center text-slate-300">
          <span>Inference:</span>
          <span className="text-brand-400 font-mono">Local Ollama</span>
        </div>
      </div>
    </aside>
  );
};
