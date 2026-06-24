import { useCallback, useEffect, useRef, useState } from "react";
import { DetectionBox } from "@/lib/api";
import {
  ensureCameraStream,
  releaseCameraStream,
  subscribeCameraFrames,
  subscribeCameraStatus,
} from "@/lib/cameraStreamHub";

type FrameHandler = (payload: {
  image: string;
  detections: DetectionBox[];
  gestures?: Array<Record<string, unknown>>;
  fps?: number;
}) => void;

export function useCameraStream(onFrame?: FrameHandler) {
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onFrameRef = useRef(onFrame);
  const subscribedRef = useRef(false);
  onFrameRef.current = onFrame;

  const stop = useCallback(async () => {
    if (!subscribedRef.current) return;
    subscribedRef.current = false;
    releaseCameraStream();
    setStreaming(false);
  }, []);

  const start = useCallback(async () => {
    if (subscribedRef.current) return;
    subscribedRef.current = true;
    setError(null);
    try {
      await ensureCameraStream();
    } catch (e) {
      subscribedRef.current = false;
      setError(e instanceof Error ? e.message : "启动失败");
    }
  }, []);

  useEffect(() => {
    const offStatus = subscribeCameraStatus(({ streaming: s, loading: l, error: err }) => {
      setStreaming(s);
      setLoading(l);
      setError(err);
    });
    const offFrame = subscribeCameraFrames((payload) => {
      onFrameRef.current?.(payload);
    });
    return () => {
      offStatus();
      offFrame();
      if (subscribedRef.current) {
        subscribedRef.current = false;
        releaseCameraStream();
      }
    };
  }, []);

  return { streaming, loading, error, setError, start, stop };
}
