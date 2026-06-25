import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/api";
import { useCameraStream } from "@/hooks/useCameraStream";
import { clickToImageCoords } from "@/lib/imageCoords";

function CalibrationDot({
  screenX,
  screenY,
  step,
  active,
}: {
  screenX: number;
  screenY: number;
  step: number;
  active: boolean;
}) {
  if (!active) return null;
  return createPortal(
    <div
      className="pointer-events-none fixed z-[10001] flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-4 border-primary bg-primary/30 shadow-lg"
      style={{ left: screenX, top: screenY }}
    >
      <span className="text-xs font-bold text-white">{step + 1}</span>
    </div>,
    document.body
  );
}

export function VirtualScreenCalibPanel({
  active,
  onSaved,
  onStartCamera,
}: {
  active: boolean;
  onSaved?: () => void;
  onStartCamera?: () => void;
}) {
  const [calibrated, setCalibrated] = useState(false);
  const [step, setStep] = useState(0);
  const [gridTargets, setGridTargets] = useState<number[][]>([]);
  const [screenPoints, setScreenPoints] = useState<number[][]>([]);
  const [cameraPoints, setCameraPoints] = useState<number[][]>([]);
  const [calibrating, setCalibrating] = useState(false);
  const [validating, setValidating] = useState(false);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [mapPreview, setMapPreview] = useState<{ x: number; y: number } | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const camStartedRef = useRef(false);

  const onFrame = useCallback((payload: { image: string }) => {
    if (!active) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx || !canvasRef.current || !payload.image) return;
    const binary = atob(payload.image);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    createImageBitmap(new Blob([bytes], { type: "image/jpeg" }))
      .then((bitmap) => {
        const c = canvasRef.current;
        if (!c) return;
        if (c.width !== bitmap.width) c.width = bitmap.width;
        if (c.height !== bitmap.height) c.height = bitmap.height;
        ctx.drawImage(bitmap, 0, 0);
        bitmap.close();
      })
      .catch(() => {});
  }, [active]);

  const { streaming, loading: camLoading, error, start } = useCameraStream(onFrame);

  useEffect(() => {
    if (!active) return;
    api
      .getVirtualCalibration()
      .then((c) => {
        setCalibrated(c.calibrated);
        if (c.screen_points?.length) setScreenPoints(c.screen_points);
        if (c.camera_points?.length) setCameraPoints(c.camera_points);
      })
      .catch(() => {});
  }, [active]);

  useEffect(() => {
    if (!active) {
      camStartedRef.current = false;
      return;
    }
    if (camStartedRef.current || streaming || camLoading) return;
    camStartedRef.current = true;
    onStartCamera?.();
    void start();
  }, [active, streaming, camLoading, start, onStartCamera]);

  useEffect(() => {
    if (!active || !validating || !streaming) return;
    const timer = window.setInterval(() => {
      api
        .previewVirtualMap()
        .then((r) => {
          if (r.ok && r.screen_x != null && r.screen_y != null) {
            setMapPreview({ x: r.screen_x, y: r.screen_y });
            setMsg(`映射点：(${Math.round(r.screen_x)}, ${Math.round(r.screen_y)})`);
          } else {
            setMapPreview(null);
            setMsg(r.error || "未检测到食指");
          }
        })
        .catch(() => {});
    }, 800);
    return () => window.clearInterval(timer);
  }, [active, validating, streaming]);

  const beginCalibration = async () => {
    setMsg("");
    setStep(0);
    setScreenPoints([]);
    setCameraPoints([]);
    setValidating(false);
    try {
      const grid = await api.getVirtualCalibGrid();
      setGridTargets(grid.points);
      setCalibrating(true);
      setMsg("请对准屏幕上的 1 号圆点，在画面中点击你的指尖");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "无法获取屏幕标定点");
    }
  };

  const cancelCalibration = () => {
    setCalibrating(false);
    setValidating(false);
    setMsg("");
  };

  const onImageClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!calibrating || !canvasRef.current || !gridTargets[step]) return;
    const coords = clickToImageCoords(e.clientX, e.clientY, canvasRef.current);
    if (!coords) {
      setMsg("请点击画面内的食指尖端");
      return;
    }
    const [sx, sy] = gridTargets[step];
    setScreenPoints((p) => [...p, [sx, sy]]);
    setCameraPoints((p) => [...p, [coords[0], coords[1]]]);
    if (step >= gridTargets.length - 1) {
      setCalibrating(false);
      setMsg("已完成，请保存");
    } else {
      setStep(step + 1);
      setMsg(`请对准 ${step + 2} 号圆点，再点击画面中的指尖`);
    }
  };

  const saveCalibration = async () => {
    if (screenPoints.length < 4) {
      setMsg("至少需要 4 对校准点");
      return;
    }
    setLoading(true);
    try {
      const fw = canvasRef.current?.width || 0;
      const fh = canvasRef.current?.height || 0;
      await api.saveVirtualCalibration(screenPoints, cameraPoints, fw, fh);
      setCalibrated(true);
      setMsg("已保存");
      onSaved?.();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const dot = gridTargets[step];

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className={calibrated ? "text-success" : "text-warning"}>
          {calibrated ? "已校准" : "未校准"}
        </span>
        {screenPoints.length > 0 && (
          <span className="text-text-secondary">· 已采集 {screenPoints.length} 点</span>
        )}
        {camLoading && <span className="text-text-secondary">· 摄像头启动中…</span>}
      </div>

      <div className="flex flex-wrap gap-2">
        {!calibrating ? (
          <button type="button" className="btn-primary" onClick={() => void beginCalibration()} disabled={camLoading}>
            开始校准
          </button>
        ) : (
          <button type="button" className="btn-ghost border border-border" onClick={cancelCalibration}>
            取消校准
          </button>
        )}
        <button type="button" className="btn-secondary" onClick={saveCalibration} disabled={loading}>
          保存校准
        </button>
        <button
          type="button"
          className="btn-ghost border border-border"
          onClick={() => {
            setValidating((v) => !v);
            setMsg(validating ? "" : "伸出食指，查看绿点是否跟上");
          }}
          disabled={!calibrated}
        >
          {validating ? "停止验证" : "验证映射"}
        </button>
      </div>

      <div className="relative min-h-[240px] flex-1 overflow-hidden rounded-lg bg-black/90">
        <canvas
          ref={canvasRef}
          className={`h-full w-full object-contain ${calibrating ? "cursor-crosshair" : ""}`}
          onClick={onImageClick}
        />
        {!streaming && !camLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-text-secondary">
            等待摄像头画面…
          </div>
        )}
      </div>

      {(error || msg) && (
        <p className={`text-sm ${error ? "text-danger" : "text-text-secondary"}`}>{error || msg}</p>
      )}

      {calibrating && dot && (
        <CalibrationDot screenX={dot[0]} screenY={dot[1]} step={step} active={streaming} />
      )}
      {validating && mapPreview && (
        <div
          className="pointer-events-none fixed z-[10000] h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-green-400 bg-green-400/40"
          style={{ left: mapPreview.x, top: mapPreview.y }}
        />
      )}
    </div>
  );
}
