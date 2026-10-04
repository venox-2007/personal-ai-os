import React from "react";
import { NavItem } from "../components/Sidebar";
import {
  Mail,
  Calendar,
  FolderTree,
  Database,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

interface PlaceholderViewProps {
  tab: NavItem;
}

interface ViewDetail {
  title: string;
  phase: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  capabilities: string[];
  architectureNotes: string;
}

const VIEW_DETAILS: Record<string, ViewDetail> = {
  home: {
    title: "Central Orchestrator",
    phase: "Phase 1 (Operational)",
    icon: Mail,
    description: "Primary orchestrator agent managing user intents and delegating tasks.",
    capabilities: ["Intent routing", "Context retrieval", "Safety permission verification"],
    architectureNotes: "Active in Phase 1 as the central coordinating brain.",
  },
  calendar: {
    title: "Calendar Agent",
    phase: "Phase 2 Target",
    icon: Calendar,
    description: "Intelligent scheduling, event management, and natural language conflict detection.",
    capabilities: [
      "Query agenda and free/busy slots (Level 0)",
      "Schedule meetings and update invites (Level 1 / 2)",
      "Detect double-bookings and propose alternative times",
    ],
    architectureNotes: "Will integrate with Google Calendar API and BaseTool contracts.",
  },
  files: {
    title: "Local File Agent",
    phase: "Phase 4 Target",
    icon: FolderTree,
    description: "Local-first filesystem indexing, smart file organization, and semantic search.",
    capabilities: [
      "Fast local file search and metadata indexing (Level 0)",
      "Document content preview and summarization (Level 0)",
      "File moving and renaming (Level 2 - Requires Approval)",
      "File deletion (Level 3 - Destructive)",
    ],
    architectureNotes: "Runs local path scanning with security boundaries.",
  },
  memory: {
    title: "Unified Memory Subsystem",
    phase: "Phase 1 Foundation",
    icon: Database,
    description: "5-facet memory architecture: Conversation, Long-term, Semantic, Episodic, Preferences.",
    capabilities: [
      "Short-term conversation context buffer",
      "Long-term user fact and profile store",
      "Semantic memory chunk indexer",
      "Episodic problem-solving recall",
      "Persistent user preferences and tone control",
    ],
    architectureNotes: "Interfaces and in-memory/SQLite baseline operational in app/memory.",
  },
  security: {
    title: "Permission & Safety Matrix",
    phase: "Phase 1 Foundation",
    icon: ShieldCheck,
    description: "Four-tier permission hierarchy with human-in-the-loop approval barriers.",
    capabilities: [
      "Level 0 (Read-Only): Auto-approved safe inspection",
      "Level 1 (Low Impact): Non-destructive drafts and staging",
      "Level 2 (External Side Effect): Confirmation modal required",
      "Level 3 (Destructive): Strict explicit human confirmation required",
    ],
    architectureNotes: "Enforced via PermissionLevel enum and PermissionContext models.",
  },
};

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({ tab }) => {
  const detail = VIEW_DETAILS[tab];
  const Icon = detail.icon;

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-background">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Title card */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center shrink-0">
            <Icon className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-slate-100">{detail.title}</h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-surface-secondary text-brand-400 border border-brand-500/20 font-mono">
                {detail.phase}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{detail.description}</p>
          </div>
        </div>

        {/* Planned capabilities */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl space-y-4">
          <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Planned Agent Capabilities & Tools
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {detail.capabilities.map((cap, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 p-3 rounded-lg bg-surface-secondary/70 border border-surface-border text-xs text-slate-300"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{cap}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Architectural foundation status */}
        <div className="p-6 bg-surface border border-surface-border rounded-xl space-y-2">
          <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Architecture & Foundation Status
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed font-mono">
            {detail.architectureNotes}
          </p>
        </div>
      </div>
    </div>
  );
};
