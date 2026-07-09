"use client";

import { useEffect, useRef } from "react";

interface AmbientFieldProps {
  /** 0–1 intensity that scales particle count, speed, and glow. */
  intensity: number;
  /** Hex accent color for the motes. */
  color?: string;
}

interface Mote {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  phase: number;
  speed: number;
}

/**
 * A drifting field of glowing "fireflies" rendered on canvas. Density and
 * liveliness scale with `intensity`, giving each camera an ambient signature
 * tied to how much wildlife activity it's seeing.
 */
export default function AmbientField({ intensity, color = "#6a9b5a" }: AmbientFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const motesRef = useRef<Mote[]>([]);
  const intensityRef = useRef(intensity);

  useEffect(() => {
    intensityRef.current = intensity;
  }, [intensity]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const [cr, cg, cb] = hexToRgb(color);

    function resize() {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    }

    function seed() {
      const base = 26;
      const extra = Math.round(intensityRef.current * 60);
      const target = base + extra;
      const motes = motesRef.current;
      while (motes.length < target) {
        motes.push(makeMote());
      }
      motes.length = target;
    }

    function makeMote(): Mote {
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: 0.6 + Math.random() * 2.2,
        phase: Math.random() * Math.PI * 2,
        speed: 0.4 + Math.random() * 1.4,
      };
    }

    let last = performance.now();
    function frame(now: number) {
      const dt = Math.min((now - last) / 16.67, 3);
      last = now;
      const inten = intensityRef.current;
      ctx!.clearRect(0, 0, width, height);

      const motes = motesRef.current;
      for (const m of motes) {
        m.x += m.vx * dt * (0.5 + inten);
        m.y += m.vy * dt * (0.5 + inten) - 0.05 * dt; // gentle upward drift
        m.phase += 0.02 * m.speed * dt;

        if (m.x < -10) m.x = width + 10;
        if (m.x > width + 10) m.x = -10;
        if (m.y < -10) m.y = height + 10;
        if (m.y > height + 10) m.y = -10;

        const twinkle = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(m.phase));
        const alpha = twinkle * (0.25 + 0.55 * inten);
        const glow = m.r * (2.5 + inten * 2);

        const grad = ctx!.createRadialGradient(m.x, m.y, 0, m.x, m.y, glow);
        grad.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
        grad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        ctx!.fillStyle = grad;
        ctx!.beginPath();
        ctx!.arc(m.x, m.y, glow, 0, Math.PI * 2);
        ctx!.fill();
      }

      rafRef.current = requestAnimationFrame(frame);
    }

    resize();
    window.addEventListener("resize", resize);
    rafRef.current = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [color]);

  // Re-seed density when intensity crosses into a new band
  useEffect(() => {
    const motes = motesRef.current;
    const target = 26 + Math.round(intensity * 60);
    if (target > motes.length) {
      while (motes.length < target) {
        motes.push({
          x: Math.random() * 1000,
          y: Math.random() * 1000,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.25,
          r: 0.6 + Math.random() * 2.2,
          phase: Math.random() * Math.PI * 2,
          speed: 0.4 + Math.random() * 1.4,
        });
      }
    } else {
      motes.length = target;
    }
  }, [intensity]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden
    />
  );
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(
    h.length === 3
      ? h.split("").map((c) => c + c).join("")
      : h,
    16
  );
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
