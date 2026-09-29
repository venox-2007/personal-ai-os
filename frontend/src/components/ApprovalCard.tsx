import React, { useState } from "react";
import {
  ShieldAlert,
  Check,
  X,
  Clock,
  Code,
  AlertTriangle,
} from "lucide-react";
import { ApprovalRequestData } from "../types";
import { formatTime } from "../lib/utils";

interface ApprovalCardProps {
  approval: ApprovalRequestData;
  onApprove: (approvalId: string, reason?: string) => Promise<void>;
  onReject: (approvalId: string, reason?: string) => Promise<void>;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  approval,
  onApprove,
  onReject,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showArgs, setShowArgs] = useState(false);

  const isPending = approval.status === "pending";
  const isApproved = approval.status === "approved";
  const isRejected = approval.status === "rejected";
  const isExpired = approval.status === "expired";

  const handleApprove = async () => {
    if (isSubmitting || !isPending) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await onApprove(approval.id);
    } catch (err: any) {
      setError(err.message || "Failed to authorize action");
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (isSubmitting || !isPending) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await onReject(approval.id);
    } catch (err: any) {
      setError(err.message || "Failed to reject action");
      setIsSubmitting(false);
    }
  };

  // Determine permission color styling
  const isDestructive = approval.permission_level === 3;
  const borderTone = isDestructive
    ? "border-rose-500/40 bg-rose-950/20"
    : "border-amber-500/40 bg-amber-950/20";
  const badgeTone = isDestructive
    ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
    : "bg-amber-500/20 text-amber-300 border-amber-500/30";

  return (
    <div className={`mt-3 p-4 rounded-xl border ${borderTone} backdrop-blur-sm space-y-3 max-w-xl transition-all`}>
      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-surface-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <ShieldAlert className={`w-4 h-4 ${isDestructive ? "text-rose-400" : "text-amber-400"} animate-pulse`} />
          <span className="text-xs font-semibold text-slate-100 uppercase tracking-wider font-mono">
            Action Authorization Required
          </span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded border font-mono font-medium ${badgeTone}`}>
          {approval.permission_label} (Level {approval.permission_level})
        </span>
      </div>

      {/* Target Action Summary */}
      <div className="space-y-1">
        <div className="text-xs font-semibold text-slate-200">
          Tool: <span className="font-mono text-brand-400">{approval.tool_name}</span>
        </div>
        <div className="text-xs text-slate-300 leading-relaxed">
          {approval.action_description}
        </div>
        {approval.tool_description && (
          <div className="text-[11px] text-slate-400 italic">
            {approval.tool_description}
          </div>
        )}
      </div>

      {/* Relevant Arguments Preview */}
      {approval.arguments && Object.keys(approval.arguments).length > 0 && (
        <div className="bg-surface-secondary/90 rounded-lg p-2.5 border border-surface-border text-xs space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>Arguments</span>
            <button
              type="button"
              onClick={() => setShowArgs(!showArgs)}
              className="text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              <Code className="w-3 h-3" />
              <span>{showArgs ? "Collapse" : "Expand JSON"}</span>
            </button>
          </div>

          {!showArgs ? (
            <div className="space-y-1">
              {Object.entries(approval.arguments).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-[11px]">
                  <span className="text-slate-400 font-mono">{k}:</span>
                  <span className="text-slate-200 font-medium truncate max-w-sm">
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <pre className="text-[10px] font-mono text-slate-300 bg-background/80 p-2 rounded overflow-x-auto max-h-36">
              {JSON.stringify(approval.arguments, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Metadata & Timestamp */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Requested at {formatTime(approval.created_at)}
        </span>
        <span>ID: {approval.id.slice(0, 8)}...</span>
      </div>

      {/* Error Notice */}
      {error && (
        <div className="flex items-center gap-1.5 p-2 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Controls / Status Display */}
      {isPending ? (
        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={handleReject}
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-surface-secondary hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium border border-surface-border transition-colors"
          >
            <X className="w-3.5 h-3.5 text-rose-400" />
            <span>Reject Action</span>
          </button>
          <button
            type="button"
            onClick={handleApprove}
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-500/20 transition-colors"
          >
            {isSubmitting ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>Authorize & Execute</span>
          </button>
        </div>
      ) : (
        <div className="p-2.5 rounded-lg bg-surface-secondary text-center text-xs font-mono font-medium">
          {isApproved && (
            <span className="text-emerald-400 flex items-center justify-center gap-1.5">
              <Check className="w-4 h-4" /> Action Authorized & Executed
            </span>
          )}
          {isRejected && (
            <span className="text-rose-400 flex items-center justify-center gap-1.5">
              <X className="w-4 h-4" /> Action Declined by User
            </span>
          )}
          {isExpired && (
            <span className="text-slate-400 flex items-center justify-center gap-1.5">
              <Clock className="w-4 h-4" /> Authorization Request Expired
            </span>
          )}
        </div>
      )}
    </div>
  );
};
