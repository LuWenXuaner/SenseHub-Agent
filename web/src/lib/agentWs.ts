import { getToken } from "@/lib/api";

export type AgentWsStatus = "connecting" | "connected" | "reconnecting" | "offline";

export type AgentWsClient = {
  close: () => void;
  getStatus: () => AgentWsStatus;
};

type Options = {
  token?: string | null;
  sessionId?: string;
  onEvent: (event: Record<string, unknown>) => void;
  onStatus?: (status: AgentWsStatus) => void;
  onReconnected?: () => void;
};

export function createAgentWs(options: Options): AgentWsClient {
  const { onEvent, onStatus, onReconnected, sessionId = "" } = options;
  let ws: WebSocket | null = null;
  let pingTimer: number | null = null;
  let reconnectTimer: number | null = null;
  let reconnectAttempt = 0;
  let closed = false;
  let hadConnected = false;
  let status: AgentWsStatus = "connecting";

  const setStatus = (next: AgentWsStatus) => {
    status = next;
    onStatus?.(next);
  };

  const clearTimers = () => {
    if (pingTimer != null) {
      window.clearInterval(pingTimer);
      pingTimer = null;
    }
    if (reconnectTimer != null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const scheduleReconnect = () => {
    if (closed) return;
    setStatus("reconnecting");
    const delay = Math.min(30_000, 1000 * 2 ** reconnectAttempt);
    reconnectAttempt += 1;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  };

  const connect = () => {
    if (closed) return;
    const token = options.token ?? getToken();
    if (!token) {
      setStatus("offline");
      return;
    }
    setStatus(hadConnected ? "reconnecting" : "connecting");
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const qs = new URLSearchParams({ token });
    if (sessionId) qs.set("session_id", sessionId);
    ws = new WebSocket(`${proto}://${window.location.host}/ws/agent?${qs.toString()}`);

    ws.onopen = () => {
      reconnectAttempt = 0;
      setStatus("connected");
      if (hadConnected) onReconnected?.();
      hadConnected = true;
      pingTimer = window.setInterval(() => {
        try {
          ws?.send(JSON.stringify({ type: "ping" }));
        } catch {
          /* ignore */
        }
      }, 25_000);
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(String(ev.data)) as Record<string, unknown>;
        if (data.type === "pong") return;
        onEvent(data);
      } catch {
        /* ignore */
      }
    };

    ws.onclose = (ev) => {
      clearTimers();
      ws = null;
      if (closed) return;
      if (ev.code === 4401) {
        setStatus("offline");
        return;
      }
      scheduleReconnect();
    };

    ws.onerror = () => {
      /* onclose handles reconnect */
    };
  };

  connect();

  return {
    close: () => {
      closed = true;
      clearTimers();
      ws?.close();
      ws = null;
      setStatus("offline");
    },
    getStatus: () => status,
  };
}
