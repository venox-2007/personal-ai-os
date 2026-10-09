import React from "react";
import {
  Home,
  Calendar,
  GraduationCap,
  Code2,
  Compass,
  FolderTree,
  Database,
  Settings,
  Cpu,
  CheckSquare
} from "lucide-react";

export type NavItem =
  | "desktop"
  | "home"
  | "calendar"
  | "tasks"
  | "study"
  | "research"
  | "coding"
  | "files"
  | "memory"
  | "workflows"
  | "settings";

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

const NAV_GROUPS: { title: string; items: NavConfig[] }[] = [
  {
    title: "",
    items: [{ id: "home", label: "Home", icon: Home }],
  },
  {
    title: "WORK",
    items: [
      { id: "calendar", label: "Calendar", icon: Calendar },
      { id: "tasks", label: "Tasks", icon: CheckSquare, tag: "Soon" },
    ],
  },
  {
    title: "LEARN",
    items: [
      { id: "study", label: "Study", icon: GraduationCap },
      { id: "research", label: "Research", icon: Compass },
    ],
  },
  {
    title: "CREATE",
    items: [
      { id: "coding", label: "Coding", icon: Code2 },
      { id: "files", label: "Files", icon: FolderTree },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { id: "memory", label: "Memory", icon: Database },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  }
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  return (
    <aside className="w-64 bg-surface border-r border-surface-border flex flex-col h-full select-none">
      {/* Brand logo & OS header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-surface-border shrink-0">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-sm">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-wide text-slate-800">Personal AI OS</h1>
          <span className="text-[10px] text-slate-500 font-medium flex items-center gap-1 mt-0.5">
            Local & Private
          </span>
        </div>
      </div>

      {/* Navigation menu */}
      <div className="flex-1 py-4 px-3 overflow-y-auto space-y-6">
        {NAV_GROUPS.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            {group.title && (
              <div className="px-3 pb-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                {group.title}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-brand-50 text-brand-600"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-brand-600" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.tag && (
                    <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-md font-medium">
                      {item.tag}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </aside>
  );
};
