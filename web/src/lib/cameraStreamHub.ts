import { api, DetectionBox, getToken } from "@/lib/api";

export type CameraFramePayload = {
  image: string;
  detections: DetectionBox[];
  gestures?: Array<Record<string, unknown>>;
  fps?: number;
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
      fps: data.fps as number | undefined,
    };
    frameListeners.forEach((fn) => fn(payload));
  }
}

async function connectInternal() {
  const token = getToken();
  if (!token) throw new Error("请先登录");

  await api.cameraStart();

  await new Promise<void>((resolve, reject) => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${proto}://${window.location.host}/ws/camera?token=${encodeURIComponent(token)}`
    );
    ws = socket;
    let opened = false;

    socket.onopen = () => {
      opened = true;
      resolve();
    };
    socket.onerror = () => {
      if (!opened) reject(new Error("摄像头连接失败"));
    };
    socket.onclose = (ev) => {
      streaming = false;
      ws = null;
      emitStatus();
      if (!opened) {
        if (ev.code === 4401) reject(new Error("登录已过期，请重新登录"));
        else reject(new Error("摄像头连接被关闭"));
      }
    };
    socket.onmessage = handleMessage;
  });

  streaming = true;
  emitStatus();
}

export async function ensureCameraStream() {
  refCount += 1;
  if (ws?.readyState === WebSocket.OPEN) {
    emitStatus();
    return;
  }
  if (starting) {
    await starting;
    return;
  }
  loading = true;
  error = null;
  emitStatus();
  starting = connectInternal()
    .catch(async (e) => {
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

export function releaseCameraStream() {
  refCount = Math.max(0, refCount - 1);
  if (refCount > 0) return;
  ws?.close();
  ws = null;
  streaming = false;
  loading = false;
  api.cameraStop().catch(() => {});
  emitStatus();
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
