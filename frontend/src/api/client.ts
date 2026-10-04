import { AgentActivityEvent, HealthCheckData, ApprovalRequestData } from "../types";

export interface ChatResponsePayload {
  conversation_id: string;
  response: string;
  activities: AgentActivityEvent[];
  tool_calls?: any[];
  status?: string;
  approval?: ApprovalRequestData;
  metadata: Record<string, any>;
}

export interface ApprovalExecutionPayload {
  approval_id: string;
  status: string;
  tool_name: string;
  response: string;
  activities: AgentActivityEvent[];
  tool_calls: any[];
  conversation_id?: string;
}

export async function checkHealth(): Promise<HealthCheckData | null> {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch (error) {
    console.warn("Backend not yet reachable on /health:", error);
    return null;
  }
}

export async function sendChatMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponsePayload> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId || undefined,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to communicate with orchestrator");
  }

  return await res.json();
}

export async function approveAction(
  approvalId: string,
  reason?: string
): Promise<ApprovalExecutionPayload> {
  const res = await fetch(`/api/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to approve action");
  }

  return await res.json();
}

export async function rejectAction(
  approvalId: string,
  reason?: string
): Promise<ApprovalExecutionPayload> {
  const res = await fetch(`/api/approvals/${approvalId}/reject`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to reject action");
  }

  return await res.json();
}

export async function fetchApprovals(status?: string): Promise<ApprovalRequestData[]> {
  try {
    const url = status ? `/api/approvals?status=${status}` : "/api/approvals";
    const res = await fetch(url);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchAgents(): Promise<any[]> {
  try {
    const res = await fetch("/api/agents");
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchTools(): Promise<any[]> {
  try {
    const res = await fetch("/api/tools");
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchMemoryStats(): Promise<Record<string, any>> {
  try {
    const res = await fetch("/api/memory/stats");
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

export async function searchFiles(directory: string, pattern: string = "*.*"): Promise<any> {
  const res = await fetch("/api/files/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ directory, pattern }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to search files");
  }
  return res.json();
}

export async function getFileMetadata(file_path: string): Promise<any> {
  const res = await fetch("/api/files/metadata", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to get file metadata");
  }
  return res.json();
}

export async function readFileContent(file_path: string, start_line: number = 1, end_line?: number): Promise<any> {
  const res = await fetch("/api/files/read", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path, start_line, end_line }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to read file");
  }
  return res.json();
}

// Study API
export async function studyIngest(file_path: string): Promise<any> {
  const res = await fetch("/api/study/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to ingest document");
  }
  return res.json();
}

export async function studySearch(query: string, top_k: number = 5): Promise<any> {
  const res = await fetch("/api/study/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to search study material");
  }
  return res.json();
}

export async function studyListDocuments(): Promise<any> {
  const res = await fetch("/api/study/list");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to list documents");
  }
  return res.json();
}

export async function studyRemoveDocument(document_id: string): Promise<any> {
  const res = await fetch("/api/study/remove", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to remove document");
  }
  return res.json();
}

export async function studyAsk(question: string): Promise<any> {
  const res = await fetch("/api/study/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to ask study agent");
  }
  return res.json();
}

// Coding API
export async function codingListRepo(repo_path: string): Promise<any> {
  const res = await fetch("/api/coding/list", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to list repo");
  return res.json();
}

export async function codingMetadata(repo_path: string): Promise<any> {
  const res = await fetch("/api/coding/metadata", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to get metadata");
  return res.json();
}

export async function codingSearch(repo_path: string, pattern: string): Promise<any> {
  const res = await fetch("/api/coding/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path, pattern }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to search code");
  return res.json();
}

export async function codingReadFile(file_path: string): Promise<any> {
  const res = await fetch("/api/coding/read", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to read file");
  return res.json();
}

export async function codingGitStatus(repo_path: string): Promise<any> {
  const res = await fetch("/api/coding/git_status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to get git status");
  return res.json();
}

export async function codingGitLog(repo_path: string): Promise<any> {
  const res = await fetch("/api/coding/git_log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to get git log");
  return res.json();
}

export async function codingProposeEdit(file_path: string, expected_old_content: string, new_content: string, reason: string): Promise<any> {
  const res = await fetch("/api/coding/propose_edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path, expected_old_content, new_content, reason }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to propose edit");
  return res.json();
}

export async function codingGitDiff(repo_path: string): Promise<any> {
  const res = await fetch("/api/coding/git_diff", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to get git diff");
  return res.json();
}

// Research API
export async function researchSearch(query: string, max_results: number = 5): Promise<any> {
  const res = await fetch("/api/research/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_results }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to search");
  return res.json();
}

export async function researchFetch(url: string): Promise<any> {
  const res = await fetch("/api/research/fetch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Failed to fetch source");
  return res.json();
}
