import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Terminal, Wrench, ShieldAlert } from "lucide-react";
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
      <div className="flex-1 overflow-y-auto p-6 space-y-8">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`flex gap-4 max-w-4xl mx-auto ${isUser ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                  isUser
                    ? "bg-surface-secondary text-slate-400"
                    : "bg-brand-500/10 text-brand-400"
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div className={`space-y-2 max-w-[85%] ${isUser ? "flex flex-col items-end" : ""}`}>
                <div
                  className={`text-sm leading-relaxed ${
                    isUser
                      ? "bg-surface-secondary text-slate-200 px-5 py-3 rounded-2xl rounded-tr-sm"
                      : "text-slate-200 py-2 whitespace-pre-line"
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

                <div className={`flex flex-wrap items-center gap-3 px-1 text-[11px] text-slate-400 ${isUser ? "justify-end" : ""}`}>
                  {!isUser && msg.activities && msg.activities.length > 0 && (
                    <button
                      onClick={() => onSelectMessageActivities?.(msg)}
                      className="hover:text-brand-400 flex items-center gap-1 transition-colors"
                    >
                      <Terminal className="w-3.5 h-3.5" />
                      <span>{msg.activities.length} steps</span>
                    </button>
                  )}
                  {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div className="flex items-center gap-1 text-slate-400">
                      <Wrench className="w-3.5 h-3.5" />
                      <span>Used tools</span>
                    </div>
                  )}
                  {!isUser && msg.status === "waiting_approval" && (
                    <div className="flex items-center gap-1 text-amber-500 font-medium">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>Needs your approval</span>
                    </div>
                  )}
                  <span className="opacity-50">{formatTime(msg.timestamp)}</span>
                </div>
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex gap-4 max-w-4xl mx-auto">
            <div className="w-8 h-8 rounded-full bg-brand-500/10 text-brand-400 flex items-center justify-center shrink-0 mt-1">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="py-3 space-y-2 w-48">
              <div className="h-2 bg-surface-secondary rounded animate-pulse w-full"></div>
              <div className="h-2 bg-surface-secondary rounded animate-pulse w-2/3"></div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 bg-background">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative flex items-center shadow-sm rounded-2xl border border-surface-border bg-surface focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 transition-all">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Reply to AI..."
            rows={1}
            className="w-full bg-transparent text-slate-200 text-sm pl-5 pr-14 py-4 border-none focus:outline-none resize-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="absolute right-2 top-2 bottom-2 w-10 bg-brand-600 hover:bg-brand-500 disabled:opacity-30 text-white rounded-xl flex items-center justify-center transition-colors"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
