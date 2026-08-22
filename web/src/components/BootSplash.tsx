"use client";

import { useEffect, useLayoutEffect, useState } from "react";

/**
 * Total runtime, matched to the CSS timeline below. React only uses this to
 * unmount the (already invisible) overlay afterwards — it does not drive the
 * animation, so hydration being slow can't cut the effect short.
 */
const TOTAL_MS = 3800;

declare global {
  interface Window {
    __wwSplash?: boolean;
  }
}

/** useLayoutEffect warns during SSR; there is no layout pass on the server. */
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

/**
 * First-load splash: a camera viewfinder sweeps the screen hunting for a
 * subject, locks onto the bird from the logo, the wordmark resolves, and the
 * whole thing fades to reveal the site.
 *
 * Whether it plays is decided by the inline script in layout.tsx, before first
 * paint: `window.__wwSplash` plus `html[data-ww-splash]`. That matters for
 * three reasons:
 *
 *  - A skipped splash is never painted. Deciding in React meant the server
 *    rendered the overlay, the browser painted it, and hydration then removed
 *    it — a flash of splash on every repeat load.
 *  - The animation is pure CSS keyed off that attribute, so it starts at paint
 *    and runs its full course regardless of when hydration happens. Previously
 *    the keyframes started at paint while the removal timer started at
 *    hydration, so the two could drift apart.
 *  - The marker is an attribute, not a class, and the decision itself lives on
 *    `window`. React wipes className on <html> during hydration even though it
 *    renders none, which killed the splash ~300ms in — measured, not guessed.
 *
 * Shown on first load of a session; refreshes are skipped (navigation type
 * "reload"). `?splash` forces it.
 */
export default function BootSplash() {
  const [mounted, setMounted] = useState(true);

  // Runs before paint. React clears attributes it didn't render on <html>
  // during hydration, which stripped the marker mid-animation; re-assert it
  // synchronously so the frame after hydration still has it.
  useIsomorphicLayoutEffect(() => {
    if (window.__wwSplash) {
      document.documentElement.setAttribute("data-ww-splash", "1");
    }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (!window.__wwSplash) {
      // Never painted (display:none), so removing it now is invisible.
      setMounted(false);
      return;
    }

    const finish = () => {
      window.__wwSplash = false;
      root.removeAttribute("data-ww-splash");
      setMounted(false);
    };
    const timer = window.setTimeout(finish, TOTAL_MS);
    // Let an impatient visitor skip it.
    window.addEventListener("pointerdown", finish);
    window.addEventListener("keydown", finish);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("pointerdown", finish);
      window.removeEventListener("keydown", finish);
    };
  }, []);

  if (!mounted) return null;

  return (
    <div className="ww-splash" aria-hidden="true">
      <style>{`
        /* Inert unless the pre-paint script opted this load in. */
        .ww-splash { display: none; }

        html[data-ww-splash] .ww-splash {
          display: flex;
          position: fixed;
          inset: 0;
          z-index: 200;
          align-items: center;
          justify-content: center;
          background: #F5FFF6;
          opacity: 1;
          /* Hold on the finished logo, then reveal. Runs from first paint, so
             it completes even if hydration is slow. */
          animation: ww-reveal 700ms ease-in 3100ms forwards;
        }

        .ww-stage {
          position: relative;
          width: 150px;
          height: 150px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        /* The viewfinder: four brackets that hunt across the screen, then
           close in on the middle. */
        .ww-frame {
          position: absolute;
          inset: 0;
          will-change: transform, filter;
        }
        @keyframes ww-hunt {
          0%   { transform: translate(-38vw, -26vh) scale(2.6); opacity: 0; }
          12%  { opacity: 1; }
          28%  { transform: translate(34vw, -20vh) scale(2.3); }
          50%  { transform: translate(26vw, 24vh) scale(2.0); }
          70%  { transform: translate(-24vw, 18vh) scale(1.7); }
          86%  { transform: translate(-6vw, -4vh) scale(1.2); }
          100% { transform: translate(0, 0) scale(1); }
        }

        /* Motion blur tracks speed: heaviest through the long sweeps, gone by
           the time it settles, so the frame reads sharp once locked. Blur
           alone reads as "out of focus" — the trailing copies below are what
           read as "moving fast". */
        html[data-ww-splash] .ww-frame.lead {
          animation:
            ww-hunt 2000ms cubic-bezier(0.65, 0, 0.35, 1) forwards,
            ww-blur 2000ms cubic-bezier(0.65, 0, 0.35, 1) forwards;
        }
        @keyframes ww-blur {
          0%   { filter: blur(7px); }
          40%  { filter: blur(5px); }
          72%  { filter: blur(3px); }
          90%  { filter: blur(0.6px); }
          100% { filter: blur(0); }
        }

        html[data-ww-splash] .ww-frame.ghost {
          animation:
            ww-hunt 2000ms cubic-bezier(0.65, 0, 0.35, 1) forwards,
            ww-ghost 2000ms ease-out forwards;
        }
        html[data-ww-splash] .ww-frame.g1 { animation-delay: 55ms, 0ms; }
        html[data-ww-splash] .ww-frame.g2 { animation-delay: 110ms, 0ms; }
        @keyframes ww-ghost {
          0%   { opacity: 0.5; filter: blur(11px); }
          55%  { opacity: 0.32; filter: blur(9px); }
          82%  { opacity: 0; filter: blur(6px); }
          100% { opacity: 0; filter: blur(0); }
        }

        .ww-corner {
          position: absolute;
          width: 34px;
          height: 34px;
          border: 4px solid #5A7A5E;
          opacity: 0.91;
        }
        .ww-corner.tl { top: 0; left: 0; border-right: 0; border-bottom: 0; }
        .ww-corner.tr { top: 0; right: 0; border-left: 0; border-bottom: 0; }
        .ww-corner.bl { bottom: 0; left: 0; border-right: 0; border-top: 0; }
        .ww-corner.br { bottom: 0; right: 0; border-left: 0; border-top: 0; }

        /* The subject resolves as the viewfinder settles. */
        .ww-bird {
          width: 78px;
          height: 78px;
          position: relative;
          z-index: 1;
          opacity: 0;
          transform: scale(0.82);
        }
        html[data-ww-splash] .ww-bird {
          animation: ww-lock 700ms cubic-bezier(0.34, 1.3, 0.64, 1) 1500ms forwards;
        }
        @keyframes ww-lock {
          from { opacity: 0; transform: scale(0.82); }
          to   { opacity: 1; transform: scale(1); }
        }

        /* Lands at 2750ms, comfortably before the 3100ms reveal — previously
           the wordmark was still fading in as the overlay began fading out. */
        .ww-wordmark {
          position: absolute;
          top: calc(50% + 96px);
          opacity: 0;
          transform: translateY(6px);
          white-space: nowrap;
        }
        html[data-ww-splash] .ww-wordmark {
          animation: ww-word 600ms ease-out 2150ms forwards;
        }
        @keyframes ww-word {
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ww-reveal {
          to { opacity: 0; visibility: hidden; }
        }
      `}</style>

      <div className="ww-stage">
        {/* Ghosts first, so the sharp frame sits on top of its own smear */}
        <div className="ww-frame ghost g2">
          <span className="ww-corner tl" />
          <span className="ww-corner tr" />
          <span className="ww-corner bl" />
          <span className="ww-corner br" />
        </div>
        <div className="ww-frame ghost g1">
          <span className="ww-corner tl" />
          <span className="ww-corner tr" />
          <span className="ww-corner bl" />
          <span className="ww-corner br" />
        </div>
        <div className="ww-frame lead">
          <span className="ww-corner tl" />
          <span className="ww-corner tr" />
          <span className="ww-corner bl" />
          <span className="ww-corner br" />
        </div>

        <svg className="ww-bird" viewBox="0 0 1000 1000" fill="none">
          <path
            d="M495.178 494.052C363.701 495.869 324.294 630.424 318.943 695.329C395.77 557.43 496.204 532.285 536.818 536.949C533.363 496.214 560.717 396.856 700.837 324.16C635.802 327.58 500.901 362.687 495.178 494.052Z"
            fill="#5A7A5E"
          />
        </svg>
      </div>

      {/* Same treatment as the navbar wordmark */}
      <span className="ww-wordmark font-serif text-3xl font-semibold tracking-tight text-ink">
        Wild<em className="font-normal not-italic text-accent-deep">Watch</em>
      </span>
    </div>
  );
}
