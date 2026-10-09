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
    ? "border-red-200 bg-red-900/20"
    : "border-amber-200 bg-amber-50";

  return (
    <div className={`mt-3 p-4 rounded-xl border ${borderTone} space-y-4 max-w-xl transition-all`}>
      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-black/5 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className={`w-4 h-4 ${isDestructive ? "text-red-500" : "text-amber-500"}`} />
          <span className="text-sm font-semibold text-slate-200">
            This action needs your approval
          </span>
        </div>
      </div>

      {/* Target Action Summary */}
      <div className="space-y-1 text-slate-300">
        <div className="text-sm font-medium">
          {approval.action_description || approval.tool_description || `Tool: ${approval.tool_name}`}
        </div>
      </div>

      {/* Relevant Arguments Preview */}
      {approval.arguments && Object.keys(approval.arguments).length > 0 && (
        <div className="bg-surface/60 rounded-lg p-3 border border-black/5 text-sm space-y-2">
          {!showArgs ? (
            <div className="space-y-1.5">
              {Object.entries(approval.arguments).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-slate-400">{k}:</span>
                  <span className="text-slate-200 font-medium truncate">
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <pre className="text-[11px] font-mono text-slate-300 bg-surface p-2 rounded border border-black/5 overflow-x-auto max-h-36">
              {JSON.stringify(approval.arguments, null, 2)}
            </pre>
          )}
          <button
            type="button"
            onClick={() => setShowArgs(!showArgs)}
            className="text-brand-400 hover:text-brand-700 text-xs font-medium flex items-center gap-1 pt-1"
          >
            <Code className="w-3 h-3" />
            <span>{showArgs ? "Show less" : "Show raw JSON"}</span>
          </button>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div className="flex items-center gap-2 p-2.5 bg-red-900/20 border border-red-900/30 text-red-400 text-sm rounded-lg">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Controls / Status Display */}
      {isPending ? (
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={handleReject}
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-surface hover:bg-surface-secondary disabled:opacity-50 text-slate-300 text-sm font-medium border border-surface-border transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleApprove}
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            {isSubmitting ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : null}
            <span>Approve</span>
          </button>
        </div>
      ) : (
        <div className="p-3 rounded-xl bg-surface border border-surface-border text-center text-sm font-medium">
          {isApproved && (
            <span className="text-emerald-600 flex items-center justify-center gap-2">
              <Check className="w-4 h-4" /> Approved
            </span>
          )}
          {isRejected && (
            <span className="text-slate-400 flex items-center justify-center gap-2">
              <X className="w-4 h-4" /> Cancelled
            </span>
          )}
          {isExpired && (
            <span className="text-slate-400 flex items-center justify-center gap-2">
              <Clock className="w-4 h-4" /> Expired
            </span>
          )}
        </div>
      )}
    </div>
  );
};
