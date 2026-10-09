import React from "react";
import {
  Brain,
  Bot,
  PlayCircle,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Info,
  XCircle,
  Activity,
} from "lucide-react";
import { AgentActivityEvent, ActivityType, ActivityStatus } from "../types";
import { formatTime } from "../lib/utils";

interface ActivityPanelProps {
  activities: AgentActivityEvent[];
  isStreaming?: boolean;
}

const getActivityIcon = (type: ActivityType) => {
  switch (type) {
    case "planning":
      return <Brain className="w-4 h-4 text-purple-400" />;
    case "agent_selected":
      return <Bot className="w-4 h-4 text-blue-400" />;
    case "tool_started":
      return <PlayCircle className="w-4 h-4 text-amber-400" />;
    case "tool_completed":
      return <CheckCircle2 className="w-4 h-4 text-emerald-700" />;
    case "reasoning":
    case "status_message":
      return <Info className="w-4 h-4 text-sky-400" />;
    case "approval_required":
      return <ShieldAlert className="w-4 h-4 text-rose-400 animate-pulse" />;
    case "error":
      return <XCircle className="w-4 h-4 text-rose-500" />;
    case "completed":
      return <CheckCircle2 className="w-4 h-4 text-emerald-700" />;
    default:
      return <Activity className="w-4 h-4 text-slate-400" />;
  }
};

const getStatusBadge = (status: ActivityStatus) => {
  switch (status) {
    case "success":
      return (
        <span className="text-[10px] text-emerald-700 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-mono">
          SUCCESS
        </span>
      );
    case "running":
    case "pending":
      return (
        <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 font-mono animate-pulse">
          RUNNING
        </span>
      );
    case "waiting_approval":
      return (
        <span className="text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20 font-mono">
          APPROVAL REQ
        </span>
      );
    case "failed":
      return (
        <span className="text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20 font-mono">
          FAILED
        </span>
      );
    default:
      return null;
  }
};

export const ActivityPanel: React.FC<ActivityPanelProps> = ({ activities, isStreaming }) => {
  return (
    <aside className="w-80 bg-surface border-l border-surface-border flex flex-col h-full overflow-hidden select-none">
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand-400" />
          <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Agent Observability
          </h2>
        </div>
        {isStreaming ? (
          <span className="flex items-center gap-1.5 text-[10px] text-amber-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
            ACTIVE
          </span>
        ) : (
          <span className="text-[10px] text-slate-400 font-mono">
            {activities.length} EVENTS
          </span>
        )}
      </div>

      {/* Events timeline */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {activities.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
            <AlertTriangle className="w-8 h-8 text-slate-400 mb-2" />
            <p className="text-xs font-medium text-slate-400">No activity recorded yet</p>
            <p className="text-[11px] text-slate-400 mt-1 leading-normal">
              Send a prompt to the Orchestrator to observe multi-step planning, tool verification, and reasoning events.
            </p>
          </div>
        ) : (
          activities.map((event, idx) => (
            <div
              key={event.id || idx}
              className="p-3 bg-surface-secondary/70 border border-surface-border rounded-lg space-y-1.5 hover:border-surface-border/80 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getActivityIcon(event.activity_type)}
                  <span className="text-[11px] font-semibold text-slate-200">{event.agent}</span>
                </div>
                {getStatusBadge(event.status)}
              </div>

              <div className="text-xs text-slate-300 font-medium pl-6">{event.action}</div>

              {event.description && (
                <div className="text-[11px] text-slate-400 pl-6 leading-relaxed">
                  {event.description}
                </div>
              )}

              <div className="flex items-center justify-between pl-6 pt-1 text-[10px] text-slate-400 font-mono border-t border-surface-border/40 mt-1">
                <span>{event.activity_type}</span>
                <span>{formatTime(event.timestamp)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
