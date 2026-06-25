import { useEffect, useCallback, useRef, useState } from "react";
import { api, CameraStatus, PerceptionEvent } from "@/lib/api";
import { useCameraStream } from "@/hooks/useCameraStream";
import { drawPerceptionOverlay } from "@/lib/perceptionOverlay";

export function CameraPage() {
  const [status, setStatus] = useState<CameraStatus | null>(null);
  const [alerts, setAlerts] = useState<PerceptionEvent[]>([]);
  const [fps, setFps] = useState(0);
  const [cfg, setCfg] = useState<Record<string, unknown>>({});
  const [gestureLabel, setGestureLabel] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const onFrame = useCallback(
    (payload: {
      image: string;
      fps?: number;
      detections?: { x1: number; y1: number; x2: number; y2: number; confidence: number; label?: string }[];
      gesture?: Record<string, unknown>;
      person_count?: number;
      hands?: {
        hand_box?: { x1: number; y1: number; x2: number; y2: number };
        index_tip?: { x: number; y: number };
        tracking?: boolean;
        pinch?: boolean;
      }[];
    }) => {
      if (payload.fps) setFps(payload.fps);
      const g = payload.gesture;
      if (g?.type && g.type !== "none") {
        setGestureLabel(String(g.description || g.type));
      }
      drawPerceptionOverlay(canvasRef.current, payload.image, {
        detections: payload.detections,
        gesture: payload.gesture as { type?: string; description?: string },
        personCount: payload.person_count,
        hands: payload.hands,
      });
    },
    []
  );

  const { streaming, loading, error, setError, start, stop } = useCameraStream(onFrame);

  useEffect(() => {
    api.perceptionStatus().then(setStatus).catch(() => {});
    api.perceptionEvents().then(setAlerts).catch(() => {});
    api.perceptionConfig().then(setCfg).catch(() => {});
  }, []);

  const saveCfg = async (patch: Record<string, unknown>) => {
    const next = await api.patchPerceptionConfig(patch);
    setCfg(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">摄像头</h1>
        <div className="flex gap-2">
          {!streaming ? (
            <button type="button" className="btn-primary" onClick={() => { setError(null); start(); }} disabled={loading}>
              {loading ? "启动中…" : "开启预览"}
            </button>
          ) : (
            <button type="button" className="btn-ghost border border-border" onClick={() => stop()}>
              停止
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="card grid gap-3 md:grid-cols-2">
        <label className="text-sm">
          检测抽帧（每 N 帧）
          <input
            type="number"
            min={1}
            max={30}
            className="input mt-1"
            value={Number(cfg.detect_every_n_frames ?? 5)}
            onChange={(e) => void saveCfg({ detect_every_n_frames: Number(e.target.value) })}
          />
        </label>
        <label className="text-sm">
          手势抽帧（每 N 帧）
          <input
            type="number"
            min={1}
            max={30}
            className="input mt-1"
            value={Number(cfg.gesture_every_n_frames ?? 5)}
            onChange={(e) => void saveCfg({ gesture_every_n_frames: Number(e.target.value) })}
          />
        </label>
      </div>

      <div className="card relative aspect-video overflow-hidden bg-black/90 p-0">
        <canvas ref={canvasRef} className="h-full w-full object-contain" />
        {!streaming && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-text-secondary">
            点击「开启预览」
          </div>
        )}
        {streaming && (
          <div className="absolute right-2 top-2 rounded bg-black/60 px-2 py-1 text-xs text-white">
            {fps > 0 ? `${fps} fps` : "…"}
            {status?.inference_device ? ` · ${status.inference_device}` : ""}
            {gestureLabel ? ` · ${gestureLabel}` : ""}
          </div>
        )}
      </div>

      {alerts.length > 0 && (
        <ul className="space-y-1 text-sm text-text-secondary">
          {alerts.slice(0, 5).map((a, i) => (
            <li key={a.id ?? i}>{a.message || a.event_type}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
