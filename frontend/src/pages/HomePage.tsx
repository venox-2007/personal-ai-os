import React from "react";
import { ChatArea } from "../components/ChatArea";
import { ChatMessage } from "../types";
import { Search } from "lucide-react";

interface HomePageProps {
  messages: ChatMessage[];
  activities: any[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onSelectMessageActivities: (msg: ChatMessage) => void;
  onApproveAction?: (approvalId: string, reason?: string) => Promise<void>;
  onRejectAction?: (approvalId: string, reason?: string) => Promise<void>;
}

export const HomePage: React.FC<HomePageProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onSelectMessageActivities,
  onApproveAction,
  onRejectAction,
}) => {
  const [input, setInput] = React.useState("");

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-background px-6">
        <div className="max-w-2xl w-full space-y-8">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-semibold text-slate-800">Good afternoon, Yug</h1>
            <p className="text-slate-500">What can I help you with?</p>
          </div>
          
          <div className="relative shadow-sm rounded-xl border border-surface-border bg-surface flex items-center p-2 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 transition-all">
            <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0" />
            <input 
              type="text" 
              placeholder="Ask anything or tell me what you need..."
              className="flex-1 bg-transparent border-none outline-none px-4 py-3 text-slate-700 placeholder:text-slate-400"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && input.trim()) {
                  onSendMessage(input.trim());
                  setInput("");
                }
              }}
              autoFocus
            />
          </div>

          <div className="flex justify-center gap-3">
            <button className="px-4 py-2 bg-surface border border-surface-border rounded-full text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
              Research something
            </button>
            <button className="px-4 py-2 bg-surface border border-surface-border rounded-full text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
              Study
            </button>
            <button className="px-4 py-2 bg-surface border border-surface-border rounded-full text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
              Work with files
            </button>
          </div>

          <div className="pt-12">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Recent</h3>
            <div className="space-y-2">
              {[
                { title: "Research on speech enhancement", time: "2h ago" },
                { title: "GitHub repository review", time: "Yesterday" },
                { title: "Study session", time: "Monday" }
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center py-3 px-4 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer group border border-transparent hover:border-surface-border">
                  <span className="text-sm font-medium text-slate-700 group-hover:text-brand-600">{item.title}</span>
                  <span className="text-xs text-slate-400">{item.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex h-full overflow-hidden justify-center bg-background">
      <div className="max-w-4xl w-full flex-1">
        <ChatArea
          messages={messages}
          isLoading={isLoading}
          onSendMessage={onSendMessage}
          onSelectMessageActivities={onSelectMessageActivities}
          onApproveAction={onApproveAction}
          onRejectAction={onRejectAction}
        />
      </div>
    </div>
  );
};
