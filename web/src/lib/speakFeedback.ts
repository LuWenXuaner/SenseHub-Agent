import { api, getToken } from "@/lib/api";

let currentAudio: HTMLAudioElement | null = null;
let currentObjectUrl: string | null = null;

function stopCurrent() {
  currentAudio?.pause();
  currentAudio = null;
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
}

async function playAuthAudio(path: string) {
  const token = getToken();
  const res = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("TTS 播放失败");
  const blob = await res.blob();
  stopCurrent();
  currentObjectUrl = URL.createObjectURL(blob);
  currentAudio = new Audio(currentObjectUrl);
  await new Promise<void>((resolve, reject) => {
    if (!currentAudio) return resolve();
    currentAudio.onended = () => resolve();
    currentAudio.onerror = () => reject(new Error("TTS 播放失败"));
    void currentAudio.play().catch(reject);
  });
}

export function buildExecutionAck(cmd: string, autonomous = false): string {
  const brief = cmd.length > 36 ? `${cmd.slice(0, 36)}…` : cmd;
  return autonomous
    ? `好的，我将开始自主执行，${brief}`
    : `好的，我将开始执行，${brief}`;
}

export async function speakReply(text: string, opts?: { enabled?: boolean }) {
  if (opts?.enabled === false || !text.trim()) return;
  try {
    const res = await api.ttsSpeak(text.trim());
    if (res.skipped || !res.url) return;
    await playAuthAudio(res.url);
  } catch {
    // TTS 不可用时静默跳过
  }
}

/** 语音指令确认播报（Pro+ 且 TTS 已启用） */
export async function speakExecutionAck(
  cmd: string,
  opts?: { autonomous?: boolean; enabled?: boolean }
) {
  if (opts?.enabled === false || !cmd.trim()) return;
  try {
    const text = buildExecutionAck(cmd.trim(), opts?.autonomous);
    const res = await api.ttsSpeak(text);
    if (res.skipped || !res.url) return;
    await playAuthAudio(res.url);
  } catch {
    // TTS 不可用时静默跳过
  }
}

export function stopSpeechFeedback() {
  stopCurrent();
}
