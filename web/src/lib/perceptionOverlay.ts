/** 在 canvas 上叠加检测框与手势标签 */

export type DetectionBox = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number;
  label?: string;
};

export type GesturePayload = {
  type?: string;
  confidence?: number;
  description?: string;
  hint?: string;
};

export type HandOverlay = {
  hand_box?: { x1: number; y1: number; x2: number; y2: number };
  index_tip?: { x: number; y: number };
  tracking?: boolean;
  pinch?: boolean;
};

export function drawPerceptionOverlay(
  canvas: HTMLCanvasElement | null,
  baseImage: string,
  opts: {
    detections?: DetectionBox[];
    gesture?: GesturePayload | null;
    personCount?: number;
    hands?: HandOverlay[];
  }
) {
  if (!canvas || !baseImage) return;
  const binary = atob(baseImage);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "image/jpeg" });
  createImageBitmap(blob)
    .then((bitmap) => {
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        bitmap.close();
        return;
      }
      if (canvas.width !== bitmap.width) canvas.width = bitmap.width;
      if (canvas.height !== bitmap.height) canvas.height = bitmap.height;
      ctx.drawImage(bitmap, 0, 0);
      bitmap.close();

      const dets = opts.detections || [];
      ctx.lineWidth = 2;
      ctx.font = "14px sans-serif";
      for (const d of dets) {
        ctx.strokeStyle = "#22c55e";
        ctx.strokeRect(d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1);
        const label = `${d.label || "person"} ${Math.round((d.confidence || 0) * 100)}%`;
        ctx.fillStyle = "rgba(34,197,94,0.85)";
        ctx.fillRect(d.x1, Math.max(0, d.y1 - 18), ctx.measureText(label).width + 8, 18);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, d.x1 + 4, Math.max(12, d.y1 - 5));
      }

      const hands = opts.hands || [];
      for (const hand of hands) {
        const box = hand.hand_box;
        if (!box) continue;
        const bw = box.x2 - box.x1;
        const bh = box.y2 - box.y1;
        ctx.strokeStyle = hand.tracking ? "#6f7bff" : "#94a3b8";
        ctx.lineWidth = 2;
        ctx.strokeRect(box.x1, box.y1, bw, bh);
        const handLabel = hand.pinch ? "食指 · 捏合" : hand.tracking ? "食指" : "手部";
        ctx.fillStyle = hand.tracking ? "rgba(111,123,255,0.88)" : "rgba(148,163,184,0.88)";
        ctx.fillRect(box.x1, Math.max(0, box.y1 - 18), ctx.measureText(handLabel).width + 8, 18);
        ctx.fillStyle = "#fff";
        ctx.fillText(handLabel, box.x1 + 4, Math.max(12, box.y1 - 5));

        const tip = hand.index_tip;
        if (tip) {
          ctx.beginPath();
          ctx.arc(tip.x, tip.y, 8, 0, Math.PI * 2);
          ctx.fillStyle = hand.pinch ? "#22c55e" : "#f59e0b";
          ctx.fill();
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }
      ctx.lineWidth = 2;

      const g = opts.gesture;
      const label =
        g?.type && g.type !== "none"
          ? String(g.description || g.type)
          : g?.hint
            ? String(g.hint)
            : "";
      if (label) {
        ctx.fillStyle = "rgba(111,123,255,0.9)";
        ctx.fillRect(8, 8, ctx.measureText(label).width + 12, 22);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, 14, 24);
      } else if (opts.personCount != null && opts.personCount > 0) {
        const text = `${opts.personCount} 人`;
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fillRect(8, 8, ctx.measureText(text).width + 12, 22);
        ctx.fillStyle = "#fff";
        ctx.fillText(text, 14, 24);
      }
    })
    .catch(() => {});
}

/** 校准圆点对应的物理屏幕坐标（优先与后端 mss 主屏坐标一致） */
export function screenCalibPoint(nx: number, ny: number): [number, number] {
  const scr = window.screen as Screen & { availLeft?: number; availTop?: number };
  const left = typeof scr.availLeft === "number" ? scr.availLeft : 0;
  const top = typeof scr.availTop === "number" ? scr.availTop : 0;
  const w = scr.availWidth || scr.width;
  const h = scr.availHeight || scr.height;
  return [left + nx * w, top + ny * h];
}
