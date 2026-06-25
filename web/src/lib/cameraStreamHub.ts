import { api, DetectionBox, getToken } from "@/lib/api";

export type CameraFramePayload = {
  image: string;
  detections: DetectionBox[];
  gestures?: Array<Record<string, unknown>>;
  gesture?: Record<string, unknown>;
  person_count?: number;
  fps?: number;
  hands?: Array<{
    hand_box?: { x1: number; y1: number; x2: number; y2: number };
    index_tip?: { x: number; y: number };
    tracking?: boolean;
    pinch?: boolean;
  }>;
};

type FrameListener = (payload: CameraFramePayload) => void;
type StatusListener = (status: { streaming: boolean; loading: boolean; error: string | null }) => void;

let ws: WebSocket | null = null;
let refCount = 0;
let starting: Promise<void> | null = null;
let streaming = false;
let loading = false;
let error: string | null = null;
const frameListeners = new Set<FrameListener>();
const statusListeners = new Set<StatusListener>();
const lastFrameAt = { value: 0 };
const FRAME_MIN_MS = 120;

function emitStatus() {
  const snapshot = { streaming, loading, error };
  statusListeners.forEach((fn) => fn(snapshot));
}

function handleMessage(ev: MessageEvent) {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(String(ev.data));
  } catch {
    return;
  }
  if (data.type === "error") {
    error = String(data.message || "摄像头错误");
    streaming = false;
    emitStatus();
    ws?.close();
    return;
  }
  if (data.type === "frame") {
    const now = performance.now();
    if (now - lastFrameAt.value < FRAME_MIN_MS) return;
    lastFrameAt.value = now;
    streaming = true;
    error = null;
    emitStatus();
    const payload: CameraFramePayload = {
      image: String(data.image || ""),
      detections: (data.detections as DetectionBox[]) || [],
      gestures: data.gestures as Array<Record<string, unknown>> | undefined,
      gesture: data.gesture as Record<string, unknown> | undefined,
      person_count: data.person_count as number | undefined,
      fps: data.fps as number | undefined,
      hands: data.hands as CameraFramePayload["hands"],
    };
    frameListeners.forEach((fn) => fn(payload));
  }
}

let connectGen = 0;

function isConnectAborted(err: unknown): boolean {
  return err instanceof Error && err.name === "ConnectAbortedError";
}

function abortConnect(): void {
  connectGen += 1;
}

async function connectInternal() {
  const token = getToken();
  if (!token) throw new Error("请先登录");

  const myGen = ++connectGen;

  await api.cameraStart();
  if (myGen !== connectGen) {
    const err = new Error("aborted");
    err.name = "ConnectAbortedError";
    throw err;
  }

  await new Promise<void>((resolve, reject) => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${proto}://${window.location.host}/ws/camera?token=${encodeURIComponent(token)}`
    );
    if (myGen !== connectGen) {
      socket.close();
      const err = new Error("aborted");
      err.name = "ConnectAbortedError";
      reject(err);
      return;
    }
    ws = socket;
    let opened = false;

    const fail = (message: string) => {
      if (myGen !== connectGen) {
        const err = new Error("aborted");
        err.name = "ConnectAbortedError";
        reject(err);
        return;
      }
      reject(new Error(message));
    };

    socket.onopen = () => {
      if (myGen !== connectGen) {
        socket.close();
        const err = new Error("aborted");
        err.name = "ConnectAbortedError";
        reject(err);
        return;
      }
      opened = true;
      resolve();
    };
    socket.onerror = () => {
      if (!opened) fail("摄像头连接失败");
    };
    socket.onclose = (ev) => {
      if (myGen !== connectGen) {
        const err = new Error("aborted");
        err.name = "ConnectAbortedError";
        reject(err);
        return;
      }
      streaming = false;
      ws = null;
      emitStatus();
      if (!opened) {
        if (ev.code === 4401) fail("登录已过期，请重新登录");
        else fail("摄像头连接被关闭");
      }
    };
    socket.onmessage = handleMessage;
  });

  if (myGen !== connectGen) {
    const err = new Error("aborted");
    err.name = "ConnectAbortedError";
    throw err;
  }

  streaming = true;
  emitStatus();
}

export async function ensureCameraStream() {
  if (ws?.readyState === WebSocket.OPEN) {
    refCount += 1;
    emitStatus();
    return;
  }
  refCount += 1;
  if (starting) {
    try {
      await starting;
    } catch (e) {
      if (!isConnectAborted(e)) throw e;
    }
    if (ws?.readyState === WebSocket.OPEN) {
      emitStatus();
      return;
    }
  }
  loading = true;
  error = null;
  emitStatus();
  starting = connectInternal()
    .catch(async (e) => {
      if (isConnectAborted(e)) {
        refCount = Math.max(0, refCount - 1);
        return;
      }
      refCount = Math.max(0, refCount - 1);
      error = e instanceof Error ? e.message : "启动失败";
      streaming = false;
      ws?.close();
      ws = null;
      await api.cameraStop().catch(() => {});
      throw e;
    })
    .finally(() => {
      loading = false;
      starting = null;
      emitStatus();
    });
  await starting;
}

async function teardownCameraSocket() {
  abortConnect();
  const socket = ws;
  ws = null;
  streaming = false;
  loading = false;

  if (socket) {
    socket.onmessage = null;
    if (socket.readyState === WebSocket.OPEN) {
      await new Promise<void>((resolve) => {
        const finish = () => resolve();
        socket.addEventListener("close", finish, { once: true });
        socket.close();
        window.setTimeout(finish, 400);
      });
    } else if (socket.readyState === WebSocket.CONNECTING) {
      socket.onopen = () => socket.close();
      socket.onerror = null;
      socket.onclose = null;
      socket.close();
    }
  }

  await api.cameraStop().catch(() => {});
  emitStatus();
}

export async function releaseCameraStream() {
  refCount = Math.max(0, refCount - 1);
  if (refCount > 0) {
    emitStatus();
    return;
  }
  refCount = 0;
  await teardownCameraSocket();
}

/** 用户主动关摄像头：无视引用计数，强制断开 */
export async function forceReleaseCameraStream() {
  refCount = 0;
  await teardownCameraSocket();
}

export function subscribeCameraFrames(listener: FrameListener) {
  frameListeners.add(listener);
  return () => frameListeners.delete(listener);
}

export function subscribeCameraStatus(listener: StatusListener) {
  statusListeners.add(listener);
  listener({ streaming, loading, error });
  return () => statusListeners.delete(listener);
}
