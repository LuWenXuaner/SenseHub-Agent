import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  codeTitleFromMessages,
  createCodeSession,
  loadCodeSessions,
  saveCodeSessions,
  upsertCodeSession,
  type CodeMessage,
  type CodeSession,
} from "@/lib/codeSessions";
import { userStorageScope } from "@/lib/userScope";
import { useAuth } from "@/context/AuthContext";

type CodeCtx = {
  sessions: CodeSession[];
  sessionId: string;
  messages: CodeMessage[];
  persistMessages: (msgs: CodeMessage[], projectName?: string) => void;
  newSession: () => void;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
};

const CodeContext = createContext<CodeCtx | null>(null);

export function CodeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const scope = userStorageScope(user?.username);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState<CodeSession[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<CodeMessage[]>([]);

  const persist = useCallback(
    (nextSessions: CodeSession[]) => {
      setSessions(nextSessions);
      saveCodeSessions(nextSessions, scope);
    },
    [scope]
  );

  useEffect(() => {
    const initial = loadCodeSessions(scope);
    const bootstrap = initial[0] ?? createCodeSession();
    const list = initial.length ? initial : [bootstrap];
    setSessions(list);
    setSessionId(bootstrap.id);
    setMessages(bootstrap.messages);
  }, [scope]);

  const persistMessages = useCallback(
    (msgs: CodeMessage[], projectName?: string) => {
      setMessages(msgs);
      setSessions((prev) => {
        const current = prev.find((s) => s.id === sessionId) ?? createCodeSession(sessionId);
        const updated: CodeSession = {
          ...current,
          messages: msgs,
          title: codeTitleFromMessages(msgs),
          updatedAt: Date.now(),
          projectName: projectName ?? current.projectName,
        };
        const next = upsertCodeSession(prev, updated);
        saveCodeSessions(next, scope);
        return next;
      });
    },
    [sessionId, scope]
  );

  const newSession = useCallback(() => {
    const s = createCodeSession();
    persist(upsertCodeSession(sessions, s));
    setSessionId(s.id);
    setMessages([]);
  }, [persist, sessions]);

  const switchSession = useCallback(
    (id: string) => {
      const s = sessions.find((x) => x.id === id);
      if (!s) return;
      setSessionId(id);
      setMessages(s.messages);
    },
    [sessions]
  );

  const deleteSession = useCallback(
    (id: string) => {
      const next = sessions.filter((s) => s.id !== id);
      const fallback = next[0] ?? createCodeSession();
      const list = next.length ? next : [fallback];
      persist(list);
      setSessionId(fallback.id);
      setMessages(fallback.messages);
    },
    [persist, sessions]
  );

  return (
    <CodeContext.Provider
      value={{
        sessions,
        sessionId,
        messages,
        persistMessages,
        newSession,
        switchSession,
        deleteSession,
        sidebarOpen,
        setSidebarOpen,
      }}
    >
      {children}
    </CodeContext.Provider>
  );
}

export function useCode() {
  const ctx = useContext(CodeContext);
  if (!ctx) throw new Error("useCode must be used within CodeProvider");
  return ctx;
}
