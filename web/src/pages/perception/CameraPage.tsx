import { useEffect, useCallback, useRef, useState } from "react";
import { api, CameraStatus, PerceptionEvent } from "@/lib/api";
import { useCameraStream } from "@/hooks/useCameraStream";
import { drawJpegToCanvas } from "@/lib/jpegPreview";

export function CameraPage() {
  const [status, setStatus] = useState<CameraStatus | null>(null);
  const [alerts, setAlerts] = useState<PerceptionEvent[]>([]);
  const [fps, setFps] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const onFrame = useCallback((payload: { image: string; fps?: number }) => {
    if (payload.fps) setFps(payload.fps);
    drawJpegToCanvas(canvasRef.current, payload.image);
  }, []);

  const { streaming, loading, error, setError, start, stop } = useCameraStream(onFrame);

  useEffect(() => {
    api.perceptionStatus().then(setStatus).catch(() => {});
    api.perceptionEvents().then(setAlerts).catch(() => {});
  }, []);

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
