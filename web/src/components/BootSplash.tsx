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

    // No dismiss-on-interaction. It used to end on pointerdown/keydown, which
    // meant a single stray click or keypress after load killed the whole
    // effect instantly -- at 3.8s a skip affordance isn't worth that.
    const timer = window.setTimeout(() => {
      window.__wwSplash = false;
      root.removeAttribute("data-ww-splash");
      setMounted(false);
    }, TOTAL_MS);

    return () => window.clearTimeout(timer);
  }, []);

  if (!mounted) return null;

  return (
    <div className="ww-splash" aria-hidden="true">

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
