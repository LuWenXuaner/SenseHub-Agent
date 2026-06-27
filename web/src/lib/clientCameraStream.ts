import type { CameraFramePayload } from "@/lib/cameraStreamHub";

type FrameListener = (payload: CameraFramePayload) => void;
type StatusListener = (status: { streaming: boolean; loading: boolean; error: string | null }) => void;

let stream: MediaStream | null = null;
let videoEl: HTMLVideoElement | null = null;
let canvasEl: HTMLCanvasElement | null = null;
let frameTimer: ReturnType<typeof setInterval> | null = null;
let refCount = 0;
let starting: Promise<void> | null = null;
let streaming = false;
let loading = false;
let error: string | null = null;

const frameListeners = new Set<FrameListener>();
const statusListeners = new Set<StatusListener>();

function emitStatus() {
  statusListeners.forEach((fn) => fn({ streaming, loading, error }));
}

function captureFrame() {
  if (!videoEl || !canvasEl || videoEl.readyState < 2) return;
  const w = videoEl.videoWidth;
  const h = videoEl.videoHeight;
  if (!w || !h) return;
  canvasEl.width = w;
  canvasEl.height = h;
  const ctx = canvasEl.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(videoEl, 0, 0, w, h);
  const dataUrl = canvasEl.toDataURL("image/jpeg", 0.72);
  const base64 = dataUrl.split(",")[1] || "";
  if (!base64) return;
  const payload: CameraFramePayload = { image: base64, detections: [] };
  frameListeners.forEach((fn) => fn(payload));
}

async function connectInternal() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("当前浏览器不支持摄像头");
  }
  const media = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
    audio: false,
  });
  stream = media;
  videoEl = document.createElement("video");
  videoEl.playsInline = true;
  videoEl.muted = true;
  videoEl.srcObject = media;
  await videoEl.play();
  canvasEl = document.createElement("canvas");
  frameTimer = setInterval(captureFrame, 150);
  streaming = true;
  error = null;
  emitStatus();
}

export async function ensureClientCameraStream() {
  if (stream && streaming) {
    refCount += 1;
    emitStatus();
    return;
  }
  refCount += 1;
  if (starting) {
    await starting;
    return;
  }
  loading = true;
  error = null;
  emitStatus();
  starting = connectInternal()
    .catch((e) => {
      refCount = Math.max(0, refCount - 1);
      error = e instanceof Error ? e.message : "摄像头启动失败";
      streaming = false;
      throw e;
    })
    .finally(() => {
      loading = false;
      starting = null;
      emitStatus();
    });
  await starting;
}

function teardown() {
  if (frameTimer) {
    clearInterval(frameTimer);
    frameTimer = null;
  }
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  videoEl = null;
  canvasEl = null;
  streaming = false;
  loading = false;
}

export async function releaseClientCameraStream() {
  refCount = Math.max(0, refCount - 1);
  if (refCount > 0) return;
  refCount = 0;
  teardown();
  emitStatus();
}

export async function forceReleaseClientCameraStream() {
  refCount = 0;
  teardown();
  emitStatus();
}

export function subscribeClientCameraFrames(listener: FrameListener) {
  frameListeners.add(listener);
  return () => frameListeners.delete(listener);
}

export function subscribeClientCameraStatus(listener: StatusListener) {
  statusListeners.add(listener);
  listener({ streaming, loading, error });
  return () => statusListeners.delete(listener);
}
