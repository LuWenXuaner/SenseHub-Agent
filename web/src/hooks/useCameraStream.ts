import { useCallback, useEffect, useRef, useState } from "react";
import { DetectionBox } from "@/lib/api";
import {
  ensureCameraStream,
  forceReleaseCameraStream,
  releaseCameraStream,
  subscribeCameraFrames,
  subscribeCameraStatus,
} from "@/lib/cameraStreamHub";

type FrameHandler = (payload: {
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
}) => void;

export function useCameraStream(onFrame?: FrameHandler) {
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onFrameRef = useRef(onFrame);
  const subscribedRef = useRef(false);
  onFrameRef.current = onFrame;

  const stop = useCallback(async () => {
    subscribedRef.current = false;
    await forceReleaseCameraStream();
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
        void releaseCameraStream();
      }
    };
  }, []);

  return { streaming, loading, error, setError, start, stop };
}
