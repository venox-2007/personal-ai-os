import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, CornerDownLeft, Sparkles, Terminal, Wrench, ShieldAlert } from "lucide-react";
import { ApprovalCard } from "./ApprovalCard";
import { ChatMessage } from "../types";
import { formatTime } from "../lib/utils";

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onSelectMessageActivities?: (msg: ChatMessage) => void;
  onApproveAction?: (approvalId: string, reason?: string) => Promise<void>;
  onRejectAction?: (approvalId: string, reason?: string) => Promise<void>;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onSelectMessageActivities,
  onApproveAction,
  onRejectAction,
}) => {
  const [inputText, setInputText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background relative overflow-hidden">
      {/* Scrollable messages container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto p-8 border border-dashed border-surface-border rounded-xl">
            <div className="w-12 h-12 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-semibold text-slate-100 mb-2">
              Personal AI OS Orchestrator
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              Welcome to the local-first Personal AI OS. The Orchestrator manages planning, memory retrieval,
              agent delegation, and safety permissions with zero cloud dependency.
            </p>
            <div className="w-full grid grid-cols-2 gap-2 text-left">
              <button
                onClick={() => setInputText("What are the core safety permission levels in this OS?")}
                className="p-2.5 rounded-lg bg-surface hover:bg-surface-secondary border border-surface-border text-xs text-slate-300 transition-colors"
              >
                🛡️ Query safety levels
              </button>
              <button
                onClick={() => setInputText("Review registered agents and tool execution capabilities")}
                className="p-2.5 rounded-lg bg-surface hover:bg-surface-secondary border border-surface-border text-xs text-slate-300 transition-colors"
              >
                🤖 Inspect registered agents
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    isUser
                      ? "bg-slate-700 text-slate-200"
                      : "bg-brand-600 text-white shadow-md shadow-brand-500/20"
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                <div className="space-y-1.5 max-w-[85%]">
                  <div
                    className={`p-4 rounded-xl text-xs leading-relaxed ${
                      isUser
                        ? "bg-brand-600 text-white rounded-tr-none"
                        : "bg-surface border border-surface-border text-slate-200 rounded-tl-none whitespace-pre-line"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {msg.approval && (
                    <ApprovalCard
                      approval={msg.approval}
                      onApprove={onApproveAction || (async () => {})}
                      onReject={onRejectAction || (async () => {})}
                    />
                  )}

                  <div className="flex flex-wrap items-center gap-2 px-1 text-[11px] text-slate-400">
                    <span>{formatTime(msg.timestamp)}</span>
                    {!isUser && msg.activities && msg.activities.length > 0 && (
                      <button
                        onClick={() => onSelectMessageActivities?.(msg)}
                        className="text-brand-400 hover:text-brand-300 font-mono flex items-center gap-1 bg-surface-secondary px-2 py-0.5 rounded border border-surface-border transition-colors"
                      >
                        <Terminal className="w-3 h-3" />
                        <span>{msg.activities.length} steps recorded</span>
                      </button>
                    )}
                    {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
                      <div className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">
                        <Wrench className="w-3 h-3" />
                        <span>{msg.tool_calls.map((t: any) => t.name).join(", ")}</span>
                      </div>
                    )}
                    {!isUser && msg.status === "waiting_approval" && (
                      <div className="flex items-center gap-1 text-[10px] text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded font-mono">
                        <ShieldAlert className="w-3 h-3" />
                        <span>Awaiting Confirmation</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}

        {isLoading && (
          <div className="flex gap-3 max-w-3xl mr-auto animate-pulse">
            <div className="w-8 h-8 rounded-lg bg-brand-600/30 text-brand-400 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-xl bg-surface border border-surface-border rounded-tl-none space-y-2 w-80">
              <div className="h-2.5 bg-surface-secondary rounded w-3/4"></div>
              <div className="h-2.5 bg-surface-secondary rounded w-1/2"></div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 border-t border-surface-border bg-surface">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Type a message or instruction to the Orchestrator... (Press Enter to send)"
            rows={1}
            className="w-full bg-surface-secondary text-slate-100 text-xs rounded-xl pl-4 pr-14 py-3.5 border border-surface-border focus:outline-none focus:border-brand-500 transition-colors resize-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="absolute right-2 top-2 bottom-2 px-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:hover:bg-brand-600 text-white rounded-lg flex items-center justify-center transition-colors"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
        <div className="text-[10px] text-slate-400 text-center mt-2 flex items-center justify-center gap-1 font-mono">
          <CornerDownLeft className="w-3 h-3" /> Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};
