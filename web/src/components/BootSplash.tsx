"use client";

import { useEffect, useState } from "react";

const TOTAL_MS = 2900;

/**
 * First-load splash: a camera viewfinder sweeps the screen hunting for a
 * subject, locks onto the bird from the logo, the wordmark resolves, and the
 * whole thing fades to reveal the site.
 *
 * Shown once per browser session, not on every route change — the App Router
 * keeps this layout mounted across client navigations, and sessionStorage
 * covers full reloads within the same session.
 *
 * Deliberately skipped for `prefers-reduced-motion`: the entire point of this
 * component is motion, so the honest response to that preference is to get out
 * of the way rather than to play a subdued version.
 */
export default function BootSplash() {
  const [phase, setPhase] = useState<"pending" | "playing" | "done">("pending");

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const seen = sessionStorage.getItem("ww-splash-seen");

    if (reduced || seen) {
      setPhase("done");
      return;
    }

    sessionStorage.setItem("ww-splash-seen", "1");
    setPhase("playing");

    // Belt and braces: the overlay is pointer-events:none once faded, but a
    // stuck splash would hide the whole site, so allow dismissing it too.
    const finish = () => setPhase("done");
    const timer = window.setTimeout(finish, TOTAL_MS);
    window.addEventListener("keydown", finish);
    window.addEventListener("pointerdown", finish);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", finish);
      window.removeEventListener("pointerdown", finish);
    };
  }, []);

  if (phase === "done") return null;

  return (
    <div className={`ww-splash${phase === "playing" ? " is-playing" : ""}`} aria-hidden="true">
      <style>{`
        .ww-splash {
          position: fixed;
          inset: 0;
          z-index: 200;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #F5FFF6;
          /* Opaque from first paint so the site never flashes through before
             hydration. The fill matches --bg, so a repeat visitor who gets it
             for a frame before the effect removes it sees nothing but the
             page background.

             ww-failsafe is the escape hatch: if JS never runs, the overlay
             would otherwise cover the site permanently. */
          opacity: 1;
          animation: ww-failsafe 400ms ease 6000ms forwards;
        }
        .ww-splash.is-playing {
          animation: ww-reveal 600ms ease-in 2300ms forwards;
        }
        @keyframes ww-failsafe {
          to { opacity: 0; visibility: hidden; }
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
           close in on the middle. Transform and opacity only, so the sweep
           stays on the compositor. */
        .ww-frame {
          position: absolute;
          inset: 0;
          animation: ww-hunt 2000ms cubic-bezier(0.65, 0, 0.35, 1) forwards;
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

        /* Motion blur. Blur tracks speed: heaviest through the long sweeps,
           gone by the time it settles, so the frame reads sharp once locked.
           Paired with the trailing ghosts below -- blur alone reads as "out of
           focus", the smear behind it is what reads as "moving fast". */
        .ww-frame.lead {
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

        /* Two lagging copies of the frame, blurrier and fainter, fading out as
           the sweep slows. */
        .ww-frame.ghost {
          animation:
            ww-hunt 2000ms cubic-bezier(0.65, 0, 0.35, 1) forwards,
            ww-ghost 2000ms ease-out forwards;
        }
        .ww-frame.g1 { animation-delay: 55ms, 0ms; }
        .ww-frame.g2 { animation-delay: 110ms, 0ms; }
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
          animation: ww-lock 700ms cubic-bezier(0.34, 1.3, 0.64, 1) 1500ms forwards;
        }
        @keyframes ww-lock {
          from { opacity: 0; transform: scale(0.82); }
          to   { opacity: 1; transform: scale(1); }
        }

        .ww-wordmark {
          position: absolute;
          top: calc(50% + 96px);
          opacity: 0;
          transform: translateY(6px);
          animation: ww-word 600ms ease-out 2050ms forwards;
          white-space: nowrap;
        }
        @keyframes ww-word {
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ww-reveal {
          to { opacity: 0; visibility: hidden; }
        }
      `}</style>

      <div className="ww-stage">
        {/* Ghosts render first so the sharp frame sits on top of its own smear */}
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
