import { randomId } from "@/lib/randomId";

export type CodeMessage = { role: "user" | "assistant"; content: string };

export type CodeSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: CodeMessage[];
  projectName?: string;
};

const STORAGE_PREFIX = "sensehub_code_sessions";
const MAX_SESSIONS = 40;

function storageKey(scope: string): string {
  return `${STORAGE_PREFIX}::${scope}`;
}

export function codeTitleFromMessages(messages: CodeMessage[]): string {
  const first = messages.find((m) => m.role === "user" && m.content.trim())?.content.trim();
  if (!first) return "新任务";
  return first.length > 28 ? `${first.slice(0, 28)}…` : first;
}

export function loadCodeSessions(scope = "guest"): CodeSession[] {
  try {
    const raw = localStorage.getItem(storageKey(scope));
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .filter((s) => s && typeof s.id === "string" && Array.isArray(s.messages))
      .map((s) => ({
        id: String(s.id),
        title: String(s.title || "新任务"),
        createdAt: Number(s.createdAt) || Date.now(),
        updatedAt: Number(s.updatedAt) || Date.now(),
        messages: s.messages as CodeMessage[],
        projectName: s.projectName ? String(s.projectName) : undefined,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function saveCodeSessions(sessions: CodeSession[], scope = "guest"): void {
  const trimmed = sessions
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_SESSIONS);
  localStorage.setItem(storageKey(scope), JSON.stringify(trimmed));
}

export function upsertCodeSession(sessions: CodeSession[], session: CodeSession): CodeSession[] {
  const rest = sessions.filter((s) => s.id !== session.id);
  return [session, ...rest].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_SESSIONS);
}

export function createCodeSession(id?: string): CodeSession {
  const now = Date.now();
  return { id: id || randomId(), title: "新任务", createdAt: now, updatedAt: now, messages: [] };
}
