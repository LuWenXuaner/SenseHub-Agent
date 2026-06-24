import { useEffect, useRef } from "react";

type Node = {
  ring: number;
  angle: number;
  color: string;
  size: number;
};

const COLORS = ["#4a9eff", "#22c55e", "#ff6900", "#8b5cf6"];

/** Hero 右侧：智能网络脉冲动画（2D，稳定可见） */
export function HeroNetworkVisual() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const nodes: Node[] = [
      { ring: 0, angle: 0, color: COLORS[0], size: 8 },
      { ring: 0, angle: Math.PI * 0.55, color: COLORS[1], size: 7 },
      { ring: 0, angle: Math.PI * 1.15, color: COLORS[2], size: 9 },
      { ring: 1, angle: 0.4, color: COLORS[0], size: 6 },
      { ring: 1, angle: 1.8, color: COLORS[2], size: 6 },
      { ring: 1, angle: 3.5, color: COLORS[1], size: 5 },
      { ring: 1, angle: 5.2, color: COLORS[3], size: 5 },
      { ring: 2, angle: 1.0, color: COLORS[2], size: 4 },
      { ring: 2, angle: 2.6, color: COLORS[0], size: 4 },
      { ring: 2, angle: 4.2, color: COLORS[1], size: 4 },
      { ring: 2, angle: 5.8, color: COLORS[3], size: 4 },
    ];

    let frame = 0;
    let raf = 0;

    const draw = () => {
      const parent = canvas.parentElement;
      const w = parent?.clientWidth ?? 480;
      const h = parent?.clientHeight ?? 400;
      const dpr = window.devicePixelRatio || 1;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const t = frame * 0.018;
      const base = Math.min(w, h) * 0.32;

      // 背景光晕
      const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, base * 1.4);
      bg.addColorStop(0, "rgba(255,105,0,0.12)");
      bg.addColorStop(0.45, "rgba(74,158,255,0.08)");
      bg.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      const positions = nodes.map((n) => {
        const r = base * (0.45 + n.ring * 0.32);
        const a = n.angle + t * (0.35 - n.ring * 0.08);
        const wobble = Math.sin(t * 2 + n.angle) * 6;
        return {
          x: cx + Math.cos(a) * (r + wobble),
          y: cy + Math.sin(a) * (r * 0.72 + wobble * 0.5),
          ...n,
        };
      });

      // 轨道虚线
      for (let ring = 0; ring < 3; ring++) {
        const r = base * (0.45 + ring * 0.32);
        ctx.beginPath();
        ctx.ellipse(cx, cy, r, r * 0.72, 0, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0,0,0,${0.06 + ring * 0.02})`;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 6]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 连线：中心 + 相邻节点
      const center = { x: cx, y: cy };
      for (const p of positions) {
        ctx.beginPath();
        ctx.moveTo(center.x, center.y);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = `${p.color}33`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      for (let i = 0; i < positions.length; i++) {
        const a = positions[i];
        const b = positions[(i + 1) % positions.length];
        if (a.ring === b.ring) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = "rgba(0,0,0,0.07)";
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }

      // 中心核心
      const pulse = 14 + Math.sin(t * 3) * 3;
      ctx.beginPath();
      ctx.arc(cx, cy, pulse, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,105,0,0.15)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, Math.PI * 2);
      ctx.fillStyle = "#ff6900";
      ctx.fill();

      // 节点
      for (const p of positions) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size + 6, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}22`;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      }

      // 漂浮粒子
      for (let i = 0; i < 24; i++) {
        const px = cx + Math.cos(t * 0.5 + i) * (base * 1.1 + i * 3);
        const py = cy + Math.sin(t * 0.7 + i * 0.8) * (base * 0.55);
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(30,30,30,0.2)";
        ctx.fill();
      }

      frame++;
      raf = requestAnimationFrame(draw);
    };

    const ro = new ResizeObserver(draw);
    if (canvas.parentElement) ro.observe(canvas.parentElement);
    draw();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="mimo-hero-visual-box" aria-hidden>
      <canvas ref={canvasRef} className="mimo-hero-visual-canvas" />
    </div>
  );
}
