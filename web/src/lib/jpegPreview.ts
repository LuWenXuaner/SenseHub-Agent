/** Canvas 绘制 JPEG，单帧解码、丢弃中间帧，避免 img/dataURL 内存暴涨。 */

const decodePending = new WeakMap<HTMLCanvasElement, boolean>();
const latestFrame = new WeakMap<HTMLCanvasElement, string>();
const rafScheduled = new WeakMap<HTMLCanvasElement, boolean>();

async function decodeToCanvas(canvas: HTMLCanvasElement, base64: string) {
  if (decodePending.get(canvas)) return;
  decodePending.set(canvas, true);
  try {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const bitmap = await createImageBitmap(new Blob([bytes], { type: "image/jpeg" }));
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      bitmap.close();
      return;
    }
    if (canvas.width !== bitmap.width) canvas.width = bitmap.width;
    if (canvas.height !== bitmap.height) canvas.height = bitmap.height;
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
  } catch {
    // ignore bad frame
  } finally {
    decodePending.set(canvas, false);
    const next = latestFrame.get(canvas);
    if (next && next !== base64) {
      void decodeToCanvas(canvas, next);
    }
  }
}

export function clearJpegCanvas(canvas: HTMLCanvasElement | null) {
  if (!canvas) return;
  latestFrame.delete(canvas);
  decodePending.delete(canvas);
  rafScheduled.delete(canvas);
  const w = canvas.width || canvas.clientWidth || 1;
  const h = canvas.height || canvas.clientHeight || 1;
  if (canvas.width !== w) canvas.width = w;
  if (canvas.height !== h) canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, w, h);
}

export function drawJpegToCanvas(canvas: HTMLCanvasElement | null, base64: string) {
  if (!canvas || !base64) return;
  latestFrame.set(canvas, base64);
  if (rafScheduled.get(canvas)) return;
  rafScheduled.set(canvas, true);
  requestAnimationFrame(() => {
    rafScheduled.set(canvas, false);
    const latest = latestFrame.get(canvas);
    if (latest) void decodeToCanvas(canvas, latest);
  });
}
