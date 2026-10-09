import React, { useEffect, useState } from "react";
import { NavItem } from "../components/Sidebar";
import { MessageSquare, Search, GraduationCap, FolderTree, Code2, Network, Calendar, Database, Clock } from "lucide-react";
import { calendarUpcoming } from "../api/client";
import { AgentActivityEvent } from "../types";

interface DesktopOverviewProps {
  onSelectTab: (tab: NavItem) => void;
  recentActivities: AgentActivityEvent[];
}

export const DesktopOverview: React.FC<DesktopOverviewProps> = ({ onSelectTab, recentActivities }) => {
  const [events, setEvents] = useState<any[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);

  useEffect(() => {
    calendarUpcoming(3).then((data) => {
      setEvents(data);
      setLoadingEvents(false);
    }).catch((e) => {
      console.error(e);
      setLoadingEvents(false);
    });
  }, []);

  const quickLaunch = [
    { id: "home", label: "AI Assistant", desc: "General chat & planning", icon: <MessageSquare className="w-5 h-5 text-brand-400" /> },
    { id: "research", label: "Research", desc: "Web research & insights", icon: <Search className="w-5 h-5 text-cyan-400" /> },
    { id: "study", label: "Study", desc: "Documents & RAG", icon: <GraduationCap className="w-5 h-5 text-emerald-400" /> },
    { id: "coding", label: "Coding", desc: "Code generation", icon: <Code2 className="w-5 h-5 text-orange-400" /> },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 overflow-y-auto">
      <div className="max-w-5xl w-full flex flex-col gap-12">
        {/* Header Greeting */}
        <div className="flex flex-col items-center text-center gap-2">
          <h1 className="text-4xl font-semibold text-white tracking-tight">Good evening, Yug.</h1>
          <p className="text-lg text-slate-400 font-medium">Let's make progress today.</p>
        </div>

        {/* Quick Launch Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickLaunch.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id as NavItem)}
              className="flex items-center gap-4 p-4 rounded-2xl bg-surface-secondary/50 hover:bg-slate-700/50 border border-white/10 transition-all text-left group hover:-translate-y-1 shadow-lg"
            >
              <div className="w-12 h-12 rounded-xl bg-surface/80 flex items-center justify-center shrink-0 shadow-inner group-hover:scale-110 transition-transform">
                {item.icon}
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-white text-sm">{item.label}</span>
                <span className="text-xs text-slate-400">{item.desc}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Bottom Split Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar Widget */}
          <div className="col-span-1 flex flex-col gap-4 bg-surface-secondary/30 border border-white/5 p-6 rounded-3xl backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" />
                Up Next
              </h3>
              <button 
                onClick={() => onSelectTab("calendar")}
                className="text-xs text-brand-400 hover:text-brand-300 font-medium"
              >
                View all
              </button>
            </div>
            
            <div className="flex flex-col gap-3 flex-1">
              {loadingEvents ? (
                <div className="text-sm text-slate-400 animate-pulse">Loading events...</div>
              ) : events.length > 0 ? (
                events.map(ev => (
                  <div key={ev.id} className="flex items-start gap-3 p-3 rounded-xl bg-surface/50 border border-white/5">
                    <div className="flex flex-col items-center justify-center px-3 py-1 bg-brand-500/10 text-brand-400 rounded-lg shrink-0">
                      <span className="text-xs font-bold leading-none">
                        {new Date(ev.start_datetime).getDate()}
                      </span>
                    </div>
                    <div className="flex flex-col flex-1 min-w-0">
                      <span className="text-sm font-medium text-slate-200 truncate">{ev.title}</span>
                      <span className="text-xs text-slate-400">
                        {new Date(ev.start_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-400 py-4 text-center">No upcoming events.</div>
              )}
            </div>
          </div>

          {/* Activity Widget */}
          <div className="col-span-2 flex flex-col gap-4 bg-surface-secondary/30 border border-white/5 p-6 rounded-3xl backdrop-blur-sm">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              Recent Agent Activity
            </h3>
            <div className="flex flex-col gap-2 overflow-hidden flex-1">
              {recentActivities.slice(0, 4).map((act, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-secondary/50 transition-colors border border-transparent hover:border-white/5 cursor-default">
                  <div className="w-2 h-2 rounded-full shrink-0 bg-brand-500" />
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="text-sm font-medium text-slate-300 truncate">{act.action}</span>
                    <span className="text-xs text-slate-400 truncate">{act.description}</span>
                  </div>
                  <span className="text-xs text-slate-400 uppercase font-medium tracking-wide">
                    {act.agent}
                  </span>
                </div>
              ))}
              {recentActivities.length === 0 && (
                <div className="text-sm text-slate-400 py-4 text-center">No recent activity.</div>
              )}
            </div>
          </div>
        </div>
        
        {/* System & Tools */}
        <div className="flex items-center justify-center gap-6 pt-4">
           <button onClick={() => onSelectTab("workflows")} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
             <Network className="w-4 h-4" /> Workflows
           </button>
           <button onClick={() => onSelectTab("memory")} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
             <Database className="w-4 h-4" /> Memory
           </button>
           <button onClick={() => onSelectTab("files")} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
             <FolderTree className="w-4 h-4" /> Files
           </button>
        </div>
      </div>
    </div>
  );
};
