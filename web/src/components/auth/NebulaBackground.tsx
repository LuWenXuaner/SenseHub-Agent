import { useEffect, useRef } from "react";
import { useTheme } from "@/hooks/useTheme";

function readThemeColors() {
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  const primary = styles.getPropertyValue("--primary").trim() || "#6366f1";
  const background = styles.getPropertyValue("--background").trim() || "#0f1117";
  return { primary, background };
}

function hexToHsl(hex: string): [number, number, number] {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return [239, 70, 65];
  const r = parseInt(raw.slice(0, 2), 16) / 255;
  const g = parseInt(raw.slice(2, 4), 16) / 255;
  const b = parseInt(raw.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [239, 70, l * 100];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

/** 星云背景 — 改编自 https://rstyro.github.io/html5/nebula.html */
export function NebulaBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { mode: themeMode } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    let num = 200;
    let _x = 0;
    let _y = 0;
    const _z = 150;
    let toX = _x;
    let toY = _y;
    let animId = 0;
    let destroyed = false;

    const dtr = (d: number) => (d * Math.PI) / 180;
    const rnd = () => Math.sin(Math.floor(Math.random() * 360) * (Math.PI / 180));

    const cam = {
      obj: { x: _x, y: _y, z: _z },
      dest: { x: 0, y: 0, z: 1 },
      dist: { x: 0, y: 0, z: 200 },
      ang: { cplane: 0, splane: 0, ctheta: 0, stheta: 0 },
      zoom: 1,
      disp: { x: w / 2, y: h / 2, z: 0 },
      upd() {
        cam.dist.x = cam.dest.x - cam.obj.x;
        cam.dist.y = cam.dest.y - cam.obj.y;
        cam.dist.z = cam.dest.z - cam.obj.z;
        cam.ang.cplane = -cam.dist.z / Math.sqrt(cam.dist.x ** 2 + cam.dist.z ** 2);
        cam.ang.splane = cam.dist.x / Math.sqrt(cam.dist.x ** 2 + cam.dist.z ** 2);
        cam.ang.ctheta =
          Math.sqrt(cam.dist.x ** 2 + cam.dist.z ** 2) /
          Math.sqrt(cam.dist.x ** 2 + cam.dist.y ** 2 + cam.dist.z ** 2);
        cam.ang.stheta =
          -cam.dist.y / Math.sqrt(cam.dist.x ** 2 + cam.dist.y ** 2 + cam.dist.z ** 2);
      },
    };

    type Vec3 = { x: number; y: number; z: number };
    type Out = Vec3 & { p?: number };

    const trans = {
      parts: {
        sz(p: Vec3, sz: Vec3): Vec3 {
          return { x: p.x * sz.x, y: p.y * sz.y, z: p.z * sz.z };
        },
        rot: {
          x(p: Vec3, rot: Vec3): Vec3 {
            return {
              x: p.x,
              y: p.y * Math.cos(dtr(rot.x)) - p.z * Math.sin(dtr(rot.x)),
              z: p.y * Math.sin(dtr(rot.x)) + p.z * Math.cos(dtr(rot.x)),
            };
          },
          y(p: Vec3, rot: Vec3): Vec3 {
            return {
              x: p.x * Math.cos(dtr(rot.y)) + p.z * Math.sin(dtr(rot.y)),
              y: p.y,
              z: -p.x * Math.sin(dtr(rot.y)) + p.z * Math.cos(dtr(rot.y)),
            };
          },
          z(p: Vec3, rot: Vec3): Vec3 {
            return {
              x: p.x * Math.cos(dtr(rot.z)) - p.y * Math.sin(dtr(rot.z)),
              y: p.x * Math.sin(dtr(rot.z)) + p.y * Math.cos(dtr(rot.z)),
              z: p.z,
            };
          },
        },
        pos(p: Vec3, pos: Vec3): Vec3 {
          return { x: p.x + pos.x, y: p.y + pos.y, z: p.z + pos.z };
        },
      },
      pov: {
        plane(p: Vec3): Vec3 {
          return {
            x: p.x * cam.ang.cplane + p.z * cam.ang.splane,
            y: p.y,
            z: p.x * -cam.ang.splane + p.z * cam.ang.cplane,
          };
        },
        theta(p: Vec3): Vec3 {
          return {
            x: p.x,
            y: p.y * cam.ang.ctheta - p.z * cam.ang.stheta,
            z: p.y * cam.ang.stheta + p.z * cam.ang.ctheta,
          };
        },
        set(p: Vec3): Vec3 {
          return { x: p.x - cam.obj.x, y: p.y - cam.obj.y, z: p.z - cam.obj.z };
        },
      },
      persp(p: Vec3): Out {
        return {
          x: (p.x * cam.dist.z) / p.z * cam.zoom,
          y: (p.y * cam.dist.z) / p.z * cam.zoom,
          z: p.z * cam.zoom,
          p: cam.dist.z / p.z,
        };
      },
      disp(p: Out, disp: Vec3): Out {
        return { x: p.x + disp.x, y: -p.y + disp.y, z: p.z + disp.z, p: p.p };
      },
      steps(_obj_: Vec3, sz: Vec3, rot: Vec3, pos: Vec3): Out {
        let args = trans.parts.sz(_obj_, sz);
        args = trans.parts.rot.x(args, rot);
        args = trans.parts.rot.y(args, rot);
        args = trans.parts.rot.z(args, rot);
        args = trans.parts.pos(args, pos);
        args = trans.pov.plane(args);
        args = trans.pov.theta(args);
        args = trans.pov.set(args);
        return trans.disp(trans.persp(args), cam.disp);
      },
    };

    class Particle {
      transIn = {
        vtx: { x: 0, y: 0, z: 0 },
        sz: { x: 0, y: 0, z: 0 },
        rot: { x: 20, y: -20, z: 0 },
        pos: { x: 0, y: 0, z: 0 },
      };
      transOut: Out = { x: 0, y: 0, z: 0, p: 0 };

      constructor(vtx: Vec3, pos: Vec3) {
        this.transIn.vtx = vtx;
        this.transIn.pos = pos;
      }

      vupd() {
        this.transOut = trans.steps(
          this.transIn.vtx,
          this.transIn.sz,
          this.transIn.rot,
          this.transIn.pos
        );
      }
    }

    const diff = 200;
    const vel = 0.04;
    const lim = 360;
    const varr: Particle[] = [];
    const calc: Vec3[] = [];
    const rotObj = { x: 0, y: 0, z: 0 };
    const objSz = { x: w / 5, y: h / 5, z: w / 5 };

    const [baseHue] = hexToHsl(readThemeColors().primary);

    const add = () => {
      varr.push(
        new Particle(
          { x: rnd(), y: rnd(), z: rnd() },
          {
            x: diff * Math.sin(360 * Math.random() * (Math.PI / 180)),
            y: diff * Math.sin(360 * Math.random() * (Math.PI / 180)),
            z: diff * Math.sin(360 * Math.random() * (Math.PI / 180)),
          }
        )
      );
      calc.push({
        x: 360 * Math.random(),
        y: 360 * Math.random(),
        z: 360 * Math.random(),
      });
    };

    for (let i = 0; i < num; i++) add();

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
      cam.disp.x = w / 2;
      cam.disp.y = h / 2;
      objSz.x = w / 5;
      objSz.y = h / 5;
      objSz.z = w / 5;
    };

    const onMove = (clientX: number, clientY: number) => {
      toX = (clientX - w / 2) * -0.8;
      toY = (clientY - h / 2) * 0.8;
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      cam.upd();
      rotObj.x += 0.1;
      rotObj.y += 0.1;
      rotObj.z += 0.1;

      for (let i = 0; i < varr.length; i++) {
        calc[i].x += vel;
        calc[i].y += vel;
        calc[i].z += vel;
        if (calc[i].x > lim) calc[i].x = 0;
        if (calc[i].y > lim) calc[i].y = 0;
        if (calc[i].z > lim) calc[i].z = 0;

        varr[i].transIn.pos = {
          x: diff * Math.cos((calc[i].x * Math.PI) / 180),
          y: diff * Math.sin((calc[i].y * Math.PI) / 180),
          z: diff * Math.sin((calc[i].z * Math.PI) / 180),
        };
        varr[i].transIn.rot = rotObj;
        varr[i].transIn.sz = objSz;
        varr[i].vupd();
        const p = varr[i].transOut.p;
        if (typeof p !== "number" || p < 0) continue;
        const { x, y } = varr[i].transOut;
        const hue = (baseHue + i * 2) % 360;
        const g = ctx.createRadialGradient(x, y, p, x, y, p * 2);
        ctx.globalCompositeOperation = "lighter";
        g.addColorStop(0, "hsla(255, 100%, 95%, 0.95)");
        g.addColorStop(0.5, `hsla(${hue}, 78%, 58%, 0.85)`);
        g.addColorStop(1, `hsla(${hue + 8}, 72%, 42%, 0.35)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, p * 2, 0, Math.PI * 2, false);
        ctx.fill();
      }
    };

    const upd = () => {
      cam.obj.x += (toX - cam.obj.x) * 0.05;
      cam.obj.y += (toY - cam.obj.y) * 0.05;
    };

    const loop = () => {
      if (destroyed) return;
      upd();
      draw();
      animId = requestAnimationFrame(loop);
    };

    resize();
    loop();

    const onMouseMove = (e: MouseEvent) => onMove(e.clientX, e.clientY);
    const onTouchMove = (e: TouchEvent) => {
      e.preventDefault();
      onMove(e.touches[0].clientX, e.touches[0].clientY);
    };

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("touchmove", onTouchMove, { passive: false });

    return () => {
      destroyed = true;
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
    };
  }, [themeMode]);

  return (
    <div className="auth-nebula-wrap" aria-hidden>
      <canvas ref={canvasRef} className="auth-nebula-canvas" />
    </div>
  );
}
