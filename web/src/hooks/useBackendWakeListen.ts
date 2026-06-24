import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { hasWakeActivation, openMicStream, recordUntilSilence } from "@/lib/wakeWord";

type WakeListenerOptions = {
  enabled: boolean;
  /** 完整 ASR 文本（含唤醒词），由大脑决定问答或执行 */
  onUtterance: (raw: string) => void;
  onStatus?: (msg: string) => void;
  onError?: (msg: string) => void;
};

/** 后端 Whisper 唤醒：说完并停顿后识别，整句交给大脑 */
export function useBackendWakeListen({
  enabled,
  onUtterance,
  onStatus,
  onError,
}: WakeListenerOptions) {
  const [listening, setListening] = useState(false);
  const [lastHeard, setLastHeard] = useState("");
  const streamRef = useRef<MediaStream | null>(null);
  const activeRef = useRef(false);
  const dedupeRef = useRef<{ text: string; ts: number }>({ text: "", ts: 0 });
  const handlersRef = useRef({ onUtterance, onStatus, onError });
  handlersRef.current = { onUtterance, onStatus, onError };

  const stopInternal = useCallback(() => {
    activeRef.current = false;
    setListening(false);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!enabled) {
      stopInternal();
      return;
    }

    let cancelled = false;
    activeRef.current = true;

    const loop = async () => {
      try {
        const stream = await openMicStream();
        if (cancelled || !activeRef.current) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        setListening(true);
        handlersRef.current.onStatus?.("正在监听…可说「灵枢」+ 指令或提问");

        while (activeRef.current && !cancelled) {
          try {
            const blob = await recordUntilSilence(stream, {
              silenceMs: 1800,
              maxMs: 14000,
              onSpeechStart: () => handlersRef.current.onStatus?.("正在听…请说完再停顿"),
              onWaitingSilence: () => handlersRef.current.onStatus?.("检测到停顿，识别中…"),
            });
            if (!activeRef.current || cancelled) break;
            const res = await api.transcribeVoice(blob);
            const raw = (res.text || "").trim();
            if (raw) {
              setLastHeard(raw);
              handlersRef.current.onStatus?.(`听到：${raw}`);
              if (hasWakeActivation(raw)) {
                const now = Date.now();
                if (dedupeRef.current.text === raw && now - dedupeRef.current.ts < 3500) continue;
                dedupeRef.current = { text: raw, ts: now };
                handlersRef.current.onUtterance(raw);
              }
            }
            handlersRef.current.onStatus?.("正在监听…可说「灵枢」+ 指令或提问");
          } catch (e) {
            const msg = e instanceof Error ? e.message : "识别失败";
            if (!msg.includes("未录到") && !msg.includes("无输入")) {
              handlersRef.current.onError?.(msg);
            }
          }
          await new Promise((r) => setTimeout(r, 200));
        }
      } catch (e) {
        if (!cancelled) {
          handlersRef.current.onError?.(
            e instanceof Error ? e.message : "无法访问麦克风，请检查浏览器权限"
          );
        }
      } finally {
        setListening(false);
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };

    void loop();
    return () => {
      cancelled = true;
      stopInternal();
    };
  }, [enabled, stopInternal]);

  return { listening, lastHeard };
}
