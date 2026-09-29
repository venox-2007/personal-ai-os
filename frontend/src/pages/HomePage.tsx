import React from "react";
import { ChatArea } from "../components/ChatArea";
import { ActivityPanel } from "../components/ActivityPanel";
import { ChatMessage, AgentActivityEvent } from "../types";

interface HomePageProps {
  messages: ChatMessage[];
  activities: AgentActivityEvent[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onSelectMessageActivities: (msg: ChatMessage) => void;
  onApproveAction?: (approvalId: string, reason?: string) => Promise<void>;
  onRejectAction?: (approvalId: string, reason?: string) => Promise<void>;
}

export const HomePage: React.FC<HomePageProps> = ({
  messages,
  activities,
  isLoading,
  onSendMessage,
  onSelectMessageActivities,
  onApproveAction,
  onRejectAction,
}) => {
  return (
    <div className="flex-1 flex h-full overflow-hidden">
      <ChatArea
        messages={messages}
        isLoading={isLoading}
        onSendMessage={onSendMessage}
        onSelectMessageActivities={onSelectMessageActivities}
        onApproveAction={onApproveAction}
        onRejectAction={onRejectAction}
      />
      <ActivityPanel activities={activities} isStreaming={isLoading} />
    </div>
  );
};
