import React from "react";
import { HealthCheckData } from "../types";
import { Activity, ShieldAlert, Cpu } from "lucide-react";

interface HeaderProps {
  currentTab: string;
  health: HealthCheckData | null;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, health }) => {
  const backendHealthy = health?.status === "ok";
  const ollamaOnline = health?.components?.llm_provider?.status === "online";

  return (
    <header className="h-16 bg-surface border-b border-surface-border px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider font-semibold text-slate-400 font-mono">
          WORKSPACE
        </span>
        <span className="text-slate-600">/</span>
        <span className="text-sm font-medium text-slate-100 capitalize">
          {currentTab === "home" ? "Central Orchestrator" : `${currentTab} Workspace`}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs font-mono">
        {/* Backend health status badge */}
        <div className="flex items-center gap-2 bg-surface-secondary px-3 py-1.5 rounded-md border border-surface-border">
          <Activity
            className={`w-3.5 h-3.5 ${backendHealthy ? "text-emerald-400" : "text-amber-400 animate-pulse"}`}
          />
          <span className="text-slate-300">FastAPI Backend:</span>
          <span className={backendHealthy ? "text-emerald-400 font-semibold" : "text-amber-400"}>
            {backendHealthy ? "ONLINE" : "CONNECTING"}
          </span>
        </div>

        {/* Ollama local LLM status badge */}
        <div className="flex items-center gap-2 bg-surface-secondary px-3 py-1.5 rounded-md border border-surface-border">
          <Cpu className={`w-3.5 h-3.5 ${ollamaOnline ? "text-emerald-400" : "text-slate-400"}`} />
          <span className="text-slate-300">Ollama:</span>
          <span className={ollamaOnline ? "text-emerald-400 font-semibold" : "text-slate-400"}>
            {ollamaOnline ? "READY" : "OFFLINE (STANDBY)"}
          </span>
        </div>

        {/* Permission level enforcement */}
        <div className="flex items-center gap-1.5 bg-brand-500/10 text-brand-400 px-3 py-1.5 rounded-md border border-brand-500/20">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Levels 2 & 3 Guarded</span>
        </div>
      </div>
    </header>
  );
};
