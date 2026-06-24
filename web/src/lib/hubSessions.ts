import type { ThinkingStep } from "@/lib/thinkingTrace";
import type { Task } from "@/lib/api";

export type HubLogItem = {
  id: string;
  role: "user" | "system";
  text: string;
  thinking?: ThinkingStep[];
  thinkingOpen?: boolean;
  status?: "thinking" | "done" | "error";
  taskId?: string;
  confirmTask?: Task;
  taskSnapshot?: Task;
};

export type HubSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  logs: HubLogItem[];
};

const STORAGE_PREFIX = "sensehub_hub_sessions";
const DELETED_PREFIX = "sensehub_hub_deleted_sessions";
const MAX_SESSIONS = 40;
const MAX_DELETED_TOMBSTONES = 200;

function deletedStorageKey(scope: string): string {
  return `${DELETED_PREFIX}::${scope}`;
}

export function loadDeletedSessionIds(scope = "guest"): Set<string> {
  try {
    const raw = localStorage.getItem(deletedStorageKey(scope));
    if (!raw) return new Set();
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return new Set();
    return new Set(data.filter((id) => typeof id === "string" && id.trim()));
  } catch {
    return new Set();
  }
}

export function markSessionDeleted(sessionId: string, scope = "guest"): void {
  const id = sessionId.trim();
  if (!id) return;
  const set = loadDeletedSessionIds(scope);
  set.add(id);
  const arr = [...set].slice(-MAX_DELETED_TOMBSTONES);
  localStorage.setItem(deletedStorageKey(scope), JSON.stringify(arr));
}

function storageKey(scope: string): string {
  return `${STORAGE_PREFIX}::${scope}`;
}

export function sessionTitleFromLogs(logs: HubLogItem[]): string {
  const first = logs.find((l) => l.role === "user" && l.text.trim())?.text.trim();
  if (!first) return "新对话";
  return first.length > 28 ? `${first.slice(0, 28)}…` : first;
}

export function loadHubSessions(scope = "guest"): HubSession[] {
  try {
    const raw = localStorage.getItem(storageKey(scope));
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .filter((s) => s && typeof s.id === "string" && Array.isArray(s.logs))
      .map((s) => ({
        id: String(s.id),
        title: String(s.title || "新对话"),
        createdAt: Number(s.createdAt) || Date.now(),
        updatedAt: Number(s.updatedAt) || Date.now(),
        logs: s.logs as HubLogItem[],
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function saveHubSessions(sessions: HubSession[], scope = "guest"): void {
  const trimmed = sessions
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_SESSIONS);
  localStorage.setItem(storageKey(scope), JSON.stringify(trimmed));
}

export function upsertHubSession(sessions: HubSession[], session: HubSession): HubSession[] {
  const rest = sessions.filter((s) => s.id !== session.id);
  return [session, ...rest].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_SESSIONS);
}

/** 后端分配了正式 session_id 时，把本地临时 UUID 换成服务端 ID。 */
export function replaceSessionId(sessions: HubSession[], oldId: string, newId: string): HubSession[] {
  const from = oldId.trim();
  const to = newId.trim();
  if (!from || !to || from === to) return sessions;
  return sessions.map((s) => (s.id === from ? { ...s, id: to } : s));
}

export function createHubSession(id?: string): HubSession {
  const now = Date.now();
  return { id: id || crypto.randomUUID(), title: "新对话", createdAt: now, updatedAt: now, logs: [] };
}

export function serverSessionToHub(s: { session_id: string; title: string; updated_at?: string; created_at?: string }): HubSession {
  const updated = s.updated_at ? Date.parse(s.updated_at) : Date.now();
  const created = s.created_at ? Date.parse(s.created_at) : updated;
  return { id: s.session_id, title: s.title || "新对话", createdAt: created, updatedAt: updated, logs: [] };
}

export function messagesToLogs(messages: Array<{ role: string; content: string }>): HubLogItem[] {
  return messages.map((m, i) => ({
    id: `srv-${i}-${Date.now()}`,
    role: m.role === "user" ? "user" : "system",
    text: m.content,
    status: "done" as const,
  }));
}
