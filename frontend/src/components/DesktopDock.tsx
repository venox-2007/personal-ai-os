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
  Network,
} from "lucide-react";
import { useWindowManager } from "../lib/WindowContext";

interface DockItemDef {
  id: NavItem;
  label: string;
  icon: React.ReactNode;
  color: string;
}

export const DesktopDock: React.FC = () => {
  const { windows, activeWindowId, openWindow, restoreWindow, focusWindow, minimizeWindow } =
    useWindowManager();

  const dockItems: DockItemDef[] = [
    { id: "desktop", label: "Overview", icon: <Home className="w-5 h-5" />, color: "text-slate-200" },
    { id: "home", label: "AI Assistant", icon: <MessageSquare className="w-5 h-5" />, color: "text-brand-400" },
    { id: "research", label: "Research", icon: <Search className="w-5 h-5" />, color: "text-cyan-400" },
    { id: "study", label: "Study", icon: <GraduationCap className="w-5 h-5" />, color: "text-emerald-400" },
    { id: "coding", label: "Coding", icon: <Code2 className="w-5 h-5" />, color: "text-orange-400" },
    { id: "files", label: "Files", icon: <FolderTree className="w-5 h-5" />, color: "text-yellow-400" },
    { id: "calendar", label: "Calendar", icon: <Calendar className="w-5 h-5" />, color: "text-rose-400" },
    { id: "memory", label: "Memory", icon: <Database className="w-5 h-5" />, color: "text-purple-400" },
    { id: "workflows", label: "Workflows", icon: <Network className="w-5 h-5" />, color: "text-indigo-400" },
  ];

  const handleDockClick = (item: DockItemDef) => {
    const win = windows.find((w) => w.id === item.id);
    if (!win) {
      // Open new window
      openWindow(item.id, item.label);
    } else if (win.isMinimized) {
      // If minimized, restore to foreground
      restoreWindow(win.id);
    } else if (activeWindowId === win.id) {
      // If already active and focused in foreground, minimize it
      minimizeWindow(win.id);
    } else {
      // If open in background, bring to front and focus
      focusWindow(win.id);
    }
  };

  return (
    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-50 select-none">
      <div className="flex items-center gap-2 p-2 bg-slate-950/70 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl shadow-black/60">
        {dockItems.map((item) => {
          const win = windows.find((w) => w.id === item.id);
          const isOpen = Boolean(win);
          const isMinimized = Boolean(win?.isMinimized);
          const isActive = activeWindowId === item.id && isOpen && !isMinimized;

          return (
            <div key={item.id} className="relative group">
              <button
                onClick={() => handleDockClick(item)}
                className={`w-12 h-12 flex flex-col items-center justify-center rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.25)] border border-brand-400/30 scale-105"
                    : isOpen
                    ? "bg-white/5 hover:bg-white/10 hover:-translate-y-0.5"
                    : "hover:bg-white/10 hover:-translate-y-0.5 opacity-85 hover:opacity-100"
                }`}
                aria-label={item.label}
              >
                <div
                  className={`${
                    isActive || isOpen
                      ? item.color
                      : "text-slate-400 group-hover:text-slate-200"
                  } transition-colors`}
                >
                  {item.icon}
                </div>

                {/* State indicator pills / dots */}
                {isOpen && (
                  <div className="absolute bottom-1 left-1/2 -translate-x-1/2 flex items-center justify-center">
                    {isActive ? (
                      // Active, focused window indicator
                      <div className="w-3.5 h-1 rounded-full bg-brand-400 shadow-[0_0_6px_rgba(96,165,250,0.8)]" />
                    ) : isMinimized ? (
                      // Minimized window indicator (subtle hollow/slate dot)
                      <div className="w-1.5 h-1.5 rounded-full border border-slate-400/80 bg-transparent" />
                    ) : (
                      // Open background window indicator (solid slate dot)
                      <div className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                    )}
                  </div>
                )}
              </button>

              {/* Tooltip */}
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2.5 py-1 bg-slate-900/95 border border-white/10 text-slate-100 text-[11px] font-medium rounded-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap shadow-xl z-50">
                {item.label}
                {isMinimized && <span className="text-slate-400 ml-1">(minimized)</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
