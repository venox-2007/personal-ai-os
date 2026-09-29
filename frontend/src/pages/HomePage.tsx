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
}

export const HomePage: React.FC<HomePageProps> = ({
  messages,
  activities,
  isLoading,
  onSendMessage,
  onSelectMessageActivities,
}) => {
  return (
    <div className="flex-1 flex h-full overflow-hidden">
      <ChatArea
        messages={messages}
        isLoading={isLoading}
        onSendMessage={onSendMessage}
        onSelectMessageActivities={onSelectMessageActivities}
      />
      <ActivityPanel activities={activities} isStreaming={isLoading} />
    </div>
  );
};
