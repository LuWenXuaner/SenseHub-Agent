/** 从 ASR 文本中提取唤醒指令（兼容同音字） */

const NOISE = /[，。！？!?、,.]/g;

const WAKE_WITH_CMD =
  /(?:(?:灵|零|凌|领|令|林)(?:枢|书|疏|舒|数)|领悟|灵枢)(?:帮我|请|啊|呀)?\s*(.+)$/i;

export function normalizeSpeechText(raw: string): string {
  return raw.replace(NOISE, " ").replace(/\s+/g, " ").trim();
}

/** 是否包含唤醒词（宽松匹配，不截断内容） */
export function hasWakeActivation(raw: string): boolean {
  const text = normalizeSpeechText(raw);
  if (!text) return false;
  return /(?:灵|零|凌|领|令|林)(?:枢|书|疏|舒|数)|领悟|灵枢/i.test(text);
}

/** @deprecated 不再截断指令；完整 ASR 文本交给大脑。保留供测试对照。 */
export function extractWakeCommand(raw: string): string | null {
  const text = normalizeSpeechText(raw);
  if (!text) return null;

  const wakeMatch = text.match(WAKE_WITH_CMD);
  if (!wakeMatch) return null;
  const cmd = wakeMatch[1]?.trim();
  if (!cmd || cmd.length < 2) return null;
  return cmd;
}

export function pickRecorderMimeType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const t of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) return t;
  }
  return "audio/webm";
}

/** 检测到说话后，等静音结束再停止录音（避免话没说完就截断） */
export async function recordUntilSilence(
  stream: MediaStream,
  opts: {
    minSpeechMs?: number;
    silenceMs?: number;
    maxMs?: number;
    onSpeechStart?: () => void;
    onWaitingSilence?: () => void;
  } = {}
): Promise<Blob> {
  const minSpeechMs = opts.minSpeechMs ?? 500;
  const silenceMs = opts.silenceMs ?? 1600;
  const maxMs = opts.maxMs ?? 12000;
  const mimeType = pickRecorderMimeType();
  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks: Blob[] = [];

  const audioCtx = new AudioContext();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const samples = new Uint8Array(analyser.fftSize);

  let speechDetected = false;
  let speechStartedAt = 0;
  let silenceStartedAt: number | null = null;
  const startedAt = performance.now();
  let rafId = 0;
  let maxTimer: ReturnType<typeof setTimeout> | null = null;

  const rms = () => {
    analyser.getByteTimeDomainData(samples);
    let sum = 0;
    for (let i = 0; i < samples.length; i += 1) {
      const n = (samples[i] - 128) / 128;
      sum += n * n;
    }
    return Math.sqrt(sum / samples.length);
  };

  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (maxTimer) clearTimeout(maxTimer);
      void audioCtx.close().catch(() => {});
    };
    const finish = (blob: Blob) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(blob);
    };
    const fail = (msg: string) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(new Error(msg));
    };

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    recorder.onerror = () => fail("录音失败");
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: mimeType });
      if (blob.size < 64) fail("未录到声音，请调大麦克风音量或靠近麦克风");
      else finish(blob);
    };

    const stopRecording = () => {
      if (recorder.state === "recording") recorder.stop();
    };

    const tick = () => {
      const now = performance.now();
      const level = rms();
      const speaking = level > 0.018;

      if (speaking) {
        if (!speechDetected) {
          speechDetected = true;
          speechStartedAt = now;
          opts.onSpeechStart?.();
        }
        silenceStartedAt = null;
      } else if (speechDetected) {
        if (silenceStartedAt === null) {
          silenceStartedAt = now;
          opts.onWaitingSilence?.();
        }
        const silentFor = now - silenceStartedAt;
        const spokeFor = now - speechStartedAt;
        if (silentFor >= silenceMs && spokeFor >= minSpeechMs) {
          stopRecording();
          return;
        }
      }

      if (now - startedAt >= maxMs) {
        if (speechDetected) stopRecording();
        return;
      }
      rafId = requestAnimationFrame(tick);
    };

    recorder.start(200);
    rafId = requestAnimationFrame(tick);
    maxTimer = setTimeout(() => {
      if (speechDetected) stopRecording();
    }, maxMs + 500);
    setTimeout(() => {
      if (!speechDetected && !settled) {
        // 一直没人说话，继续等下一段
        stopRecording();
      }
    }, maxMs);
  });
}

/** 录制一段音频（固定时长，供测试用） */
export async function recordAudioChunk(
  stream: MediaStream,
  minMs = 1200,
  maxMs = 4000
): Promise<Blob> {
  const mimeType = pickRecorderMimeType();
  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks: Blob[] = [];

  return new Promise((resolve, reject) => {
    let settled = false;
    const fail = (msg: string) => {
      if (settled) return;
      settled = true;
      reject(new Error(msg));
    };
    const ok = (blob: Blob) => {
      if (settled) return;
      settled = true;
      resolve(blob);
    };

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    recorder.onerror = () => fail("录音失败");
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: mimeType });
      if (blob.size < 64) fail("未录到声音，请调大麦克风音量或靠近麦克风");
      else ok(blob);
    };
    recorder.start(200);
    setTimeout(() => {
      if (recorder.state === "recording") recorder.stop();
    }, maxMs);
    setTimeout(() => {
      if (!settled && recorder.state === "inactive" && chunks.length === 0) {
        fail("麦克风无输入");
      }
    }, minMs + maxMs + 800);
  });
}

export async function openMicStream(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
}

/** 按住录音：从 stream 录到 stop 被调用 */
export function startHoldRecording(stream: MediaStream): {
  stop: () => Promise<Blob>;
} {
  const mimeType = pickRecorderMimeType();
  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };
  recorder.start(200);
  return {
    stop: () =>
      new Promise((resolve, reject) => {
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: mimeType });
          if (blob.size < 64) reject(new Error("录音太短，请至少说 1～2 秒"));
          else resolve(blob);
        };
        if (recorder.state === "recording") recorder.stop();
      }),
  };
}
