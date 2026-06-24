import { createContext, useContext, useState, type ReactNode } from "react";
import type { HubSession } from "@/lib/hubSessions";

export type ClawSessionApi = {
  sessions: HubSession[];
  sessionId: string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  newSession: () => void;
};

type ClawSessionCtx = {
  api: ClawSessionApi | null;
  setApi: (api: ClawSessionApi | null) => void;
};

const ClawSessionContext = createContext<ClawSessionCtx | null>(null);

export function ClawSessionProvider({ children }: { children: ReactNode }) {
  const [api, setApi] = useState<ClawSessionApi | null>(null);
  return <ClawSessionContext.Provider value={{ api, setApi }}>{children}</ClawSessionContext.Provider>;
}

export function useClawSessionBridge() {
  const ctx = useContext(ClawSessionContext);
  if (!ctx) throw new Error("useClawSessionBridge must be used within ClawSessionProvider");
  return ctx;
}

export function useClawSessions() {
  return useClawSessionBridge().api;
}
