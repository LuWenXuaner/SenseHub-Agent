import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useCameraStream } from "@/hooks/useCameraStream";
import { clickToImageCoords } from "@/lib/imageCoords";
import { drawJpegToCanvas } from "@/lib/jpegPreview";
import { TierGate } from "@/components/tier/TierGate";

const GRID = [
  [0.1, 0.1],
  [0.5, 0.1],
  [0.9, 0.1],
  [0.1, 0.5],
  [0.5, 0.5],
  [0.9, 0.5],
  [0.1, 0.9],
  [0.5, 0.9],
  [0.9, 0.9],
];

function CalibrationDot({ step, active }: { step: number; active: boolean }) {
  if (!active) return null;
  const [nx, ny] = GRID[step];
  const left = window.screenX + nx * window.screen.width;
  const top = window.screenY + ny * window.screen.height;
  return createPortal(
    <div
      className="pointer-events-none fixed z-[9999] flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-4 border-primary bg-primary/30 shadow-lg"
      style={{ left, top }}
    >
      <span className="text-xs font-bold text-white">{step + 1}</span>
    </div>,
    document.body
  );
}

export function VirtualScreenPage() {
  const navigate = useNavigate();
  const [calibrated, setCalibrated] = useState(false);
  const [step, setStep] = useState(0);
  const [screenPoints, setScreenPoints] = useState<number[][]>([]);
  const [cameraPoints, setCameraPoints] = useState<number[][]>([]);
  const [calibrating, setCalibrating] = useState(false);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const onFrame = useCallback((payload: { image: string }) => {
    drawJpegToCanvas(canvasRef.current, payload.image);
  }, []);

  const { streaming, loading: camLoading, error, start, stop } = useCameraStream(onFrame);

  useEffect(() => {
    api
      .getVirtualCalibration()
      .then((c) => {
        setCalibrated(c.calibrated);
        if (c.screen_points?.length) setScreenPoints(c.screen_points);
        if (c.camera_points?.length) setCameraPoints(c.camera_points);
      })
      .catch(() => {});
  }, []);

  const beginCalibration = async () => {
    setMsg("");
    setStep(0);
    setScreenPoints([]);
    setCameraPoints([]);
    setCalibrating(true);
    if (!streaming) await start();
    setMsg(`第 1/9 点：请看屏幕上的圆点，在下方画面中点击手指尖端位置`);
  };

  const cancelCalibration = async () => {
    setCalibrating(false);
    setMsg("");
  };

  const onImageClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!calibrating || !canvasRef.current) return;
    const coords = clickToImageCoords(e.clientX, e.clientY, canvasRef.current);
    if (!coords) {
      setMsg("请点击画面内的手指位置");
      return;
    }
    const [nx, ny] = GRID[step];
    const sx = nx * window.screen.width;
    const sy = ny * window.screen.height;
    setScreenPoints((p) => [...p, [sx, sy]]);
    setCameraPoints((p) => [...p, [coords[0], coords[1]]]);
    if (step >= GRID.length - 1) {
      setCalibrating(false);
      setMsg("9 点已采集，请点击「保存校准」");
    } else {
      setStep(step + 1);
      setMsg(`第 ${step + 2}/9 点：点击手指在画面中的位置`);
    }
  };

  const saveCalibration = async () => {
    if (screenPoints.length < 4) {
      setMsg("至少需要 4 对校准点");
      return;
    }
    setLoading(true);
    try {
      await api.saveVirtualCalibration(screenPoints, cameraPoints);
      setCalibrated(true);
      setMsg("校准已保存");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const airClick = async () => {
    setLoading(true);
    setMsg("");
    try {
      if (!streaming) await start();
      const r = await api.airClick();
      setMsg(`已点击屏幕 (${Math.round(r.x)}, ${Math.round(r.y)})`);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "点击失败");
    } finally {
      setLoading(false);
    }
  };

  const closeAndBack = () => {
    if (window.opener && !window.opener.closed) {
      window.close();
      return;
    }
    navigate("/");
  };

  return (
    <TierGate requiredTier="max">
      <div className="mx-auto max-w-3xl space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-bold">虚拟屏</h1>
          <button type="button" className="btn-ghost border border-border text-sm" onClick={closeAndBack}>
            完成并返回综合控制台
          </button>
        </div>

        <div className="card space-y-3">
          <p className="text-sm text-text-secondary">
            {calibrated ? "已校准" : "未校准"}
            {screenPoints.length > 0 && ` · 已采集 ${screenPoints.length} 点`}
          </p>

          <div className="flex flex-wrap gap-2">
            {!streaming ? (
              <button type="button" className="btn-secondary" onClick={start} disabled={camLoading}>
                {camLoading ? "启动中…" : "打开摄像头"}
              </button>
            ) : (
              <button type="button" className="btn-ghost border border-border" onClick={stop}>
                关闭摄像头
              </button>
            )}
            {!calibrating ? (
              <button type="button" className="btn-secondary" onClick={beginCalibration} disabled={camLoading}>
                开始校准
              </button>
            ) : (
              <button type="button" className="btn-ghost border border-border" onClick={cancelCalibration}>
                取消校准
              </button>
            )}
            <button type="button" className="btn-primary" onClick={saveCalibration} disabled={loading}>
              保存校准
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={airClick}
              disabled={loading || !calibrated}
            >
              空中点击
            </button>
          </div>

          <div className="relative aspect-video overflow-hidden rounded bg-black/90">
            <canvas
              ref={canvasRef}
              className={`h-full w-full object-contain ${calibrating ? "cursor-crosshair" : ""}`}
              onClick={onImageClick}
            />
            {!streaming && !camLoading && (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-text-secondary">
                先打开摄像头
              </div>
            )}
          </div>
        </div>

        {calibrating && <CalibrationDot step={step} active={streaming} />}
        {(error || msg) && (
          <p className={`text-sm ${error ? "text-danger" : "text-text-secondary"}`}>{error || msg}</p>
        )}
      </div>
    </TierGate>
  );
}
