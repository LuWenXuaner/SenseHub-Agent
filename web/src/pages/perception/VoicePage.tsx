import { useRef, useState } from "react";
import { Mic, Square, Radio } from "lucide-react";
import { api, getToken } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { openMicStream, startHoldRecording } from "@/lib/wakeWord";
import { speakExecutionAck, speakReply } from "@/lib/speakFeedback";

export function VoicePage() {
  const { license } = useAuth();
  const streamEnabled = Boolean(license?.features?.voice_stream);
  const ttsEnabled = Boolean(license?.features?.tts_feedback);
  const [recording, setRecording] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const streamWsRef = useRef<WebSocket | null>(null);
  const streamRecorderRef = useRef<MediaRecorder | null>(null);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const holdRecRef = useRef<{ stop: () => Promise<Blob> } | null>(null);

  const startRecord = async () => {
    try {
      const stream = voiceStreamRef.current ?? (await openMicStream());
      voiceStreamRef.current = stream;
      holdRecRef.current = startHoldRecording(stream);
      setRecording(true);
      setResult("");
      setTranscript("");
    } catch {
      setResult("无法访问麦克风，请在浏览器设置中允许");
    }
  };

  const stopRecord = async () => {
    if (!holdRecRef.current) return;
    setRecording(false);
    setLoading(true);
    try {
      const blob = await holdRecRef.current.stop();
      holdRecRef.current = null;
      const tr = await api.transcribeVoice(blob);
      const heard = (tr.text || "").trim();
      setTranscript(heard || "（未识别到文字）");
      if (!heard) {
        setResult("未识别到语音");
        return;
      }
      const cmd = await api.voiceRunText(heard);
      const display = cmd.reply || cmd.message;
      setResult(display + (cmd.task_id ? ` → 任务 ${cmd.task_id.slice(0, 8)}` : ""));
      if (cmd.action === "execute") {
        await speakExecutionAck(heard, { enabled: ttsEnabled });
      } else if (cmd.action === "answer" || cmd.action === "status" || cmd.action === "cancel") {
        await speakReply(display, { enabled: ttsEnabled });
      }
    } catch (e) {
      setResult(e instanceof Error ? e.message : "识别失败");
    } finally {
      setLoading(false);
      voiceStreamRef.current?.getTracks().forEach((t) => t.stop());
      voiceStreamRef.current = null;
    }
  };

  const startStream = async () => {
    const token = getToken();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/voice/stream?token=${encodeURIComponent(token)}`);
    streamWsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "partial" || data.type === "final") setStreamText(data.text || "");
        if (data.type === "error") setResult(data.message);
      } catch {
        // ignore
      }
    };
    ws.onopen = async () => {
      const stream = await openMicStream();
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data);
      };
      streamRecorderRef.current = recorder;
      recorder.start(500);
      setStreaming(true);
      setStreamText("");
    };
  };

  const stopStream = () => {
    streamRecorderRef.current?.stop();
    streamRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    const ws = streamWsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "end" }));
      setTimeout(() => ws.close(), 800);
    }
    setStreaming(false);
  };

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-2xl font-bold">语音</h1>
      <p className="text-sm text-text-secondary">点麦克风开始说话，至少 1～2 秒后再点停止。</p>

      <div className="card flex flex-col items-center gap-4 py-8">
        {!recording ? (
          <button
            type="button"
            className="btn-primary flex h-20 w-20 items-center justify-center rounded-full"
            onClick={startRecord}
            disabled={loading}
          >
            <Mic size={32} />
          </button>
        ) : (
          <button
            type="button"
            className="btn-danger flex h-20 w-20 items-center justify-center rounded-full"
            onClick={stopRecord}
          >
            <Square size={28} />
          </button>
        )}
        <p className="text-sm text-text-secondary">
          {recording ? "录音中…说完点停止" : loading ? "Whisper 识别中…" : "点击开始录音"}
        </p>
      </div>

      {transcript && (
        <div className="card">
          <p className="text-xs text-text-secondary">识别结果</p>
          <p>{transcript}</p>
        </div>
      )}

      {streamEnabled && (
        <div className="card space-y-2">
          {!streaming ? (
            <button type="button" className="btn-secondary flex items-center gap-2" onClick={startStream}>
              <Radio size={16} /> 流式识别
            </button>
          ) : (
            <button type="button" className="btn-danger" onClick={stopStream}>
              停止流式
            </button>
          )}
          {streamText && <p className="text-sm">{streamText}</p>}
        </div>
      )}

      {result && (
        <p className={`text-sm ${result.includes("失败") || result.includes("无法") ? "text-danger" : "text-text-secondary"}`}>
          {result}
        </p>
      )}
    </div>
  );
}
