export type ActivityType =
  | 'planning'
  | 'agent_selected'
  | 'tool_started'
  | 'tool_completed'
  | 'reasoning'
  | 'status_message'
  | 'approval_required'
  | 'error'
  | 'completed';

export type ActivityStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'warning'
  | 'failed'
  | 'waiting_approval';

export interface AgentActivityEvent {
  id: string;
  timestamp: string;
  agent: string;
  activity_type: ActivityType;
  status: ActivityStatus;
  action: string;
  description?: string | null;
  metadata?: Record<string, any>;
}

export interface ApprovalRequestData {
  id: string;
  tool_name: string;
  tool_description: string;
  permission_level: PermissionLevel;
  permission_label: string;
  arguments: Record<string, any>;
  action_description: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';
  created_at: string;
  expires_at: string;
  resolved_at?: string | null;
  resolution_reason?: string | null;
  conversation_id?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  activities?: AgentActivityEvent[];
  tool_calls?: any[];
  status?: string;
  approval?: ApprovalRequestData;
}

export type PermissionLevel = 0 | 1 | 2 | 3;

export interface ToolMetadata {
  name: string;
  description: string;
  permission_level: PermissionLevel;
  permission_label: string;
  requires_approval: boolean;
  parameters_schema: Record<string, any>;
}

export interface AgentMetadata {
  name: string;
  description: string;
  tools: string[];
}

export interface HealthCheckData {
  status: string;
  app: string;
  version: string;
  environment: string;
  components: {
    api?: { status: string; details: Record<string, any> };
    database?: { status: string; details: Record<string, any> };
    llm_provider?: { status: string; details: Record<string, any> };
    agents?: { status: string; details: Record<string, any> };
    tools?: { status: string; details: Record<string, any> };
  };
}
