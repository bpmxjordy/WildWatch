"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Stream } from "@/lib/supabase/types";

interface Props {
  streams: Stream[];
}

/**
 * A featured camera. Deliberately a still, not a player: mounting live HLS on
 * the home page pulled several megabits off the Smithsonian's CDN on every
 * visit, for video most people scroll past. Playback starts on the stream page.
 */
function FeaturedCard({ stream }: { stream: Stream }) {
  const poster = stream.latest_detection_thumbnail_url || stream.thumbnail_url;

  return (
    <Link
      href={`/stream/${stream.slug}`}
      className="ww-card group flex shrink-0 snap-start flex-col"
    >
      <div className="relative overflow-hidden rounded-md bg-paper-2 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_6px_18px_rgba(0,0,0,0.06)] transition-shadow group-hover:shadow-[0_10px_28px_rgba(0,0,0,0.13)]">
        <div className="aspect-video w-full">
          {poster ? (
            <img
              src={poster}
              alt={stream.name}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : null}
        </div>

        <span className="pointer-events-none absolute left-2 top-2 flex items-center gap-1.5 rounded bg-[#1e3320]/90 px-1.5 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-white backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-[#8fd177]" />
          Live
        </span>

        <span className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-black/35 opacity-0 backdrop-blur-sm transition-opacity duration-200 group-hover:opacity-100">
            <svg viewBox="0 0 24 24" className="ml-0.5 h-4 w-4 fill-white">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
        </span>
      </div>

      <span className="mt-2 truncate font-serif text-[14px] font-medium tracking-tight group-hover:underline">
        {stream.name}
      </span>
      {stream.location_name && (
        <span className="truncate font-mono text-[9px] uppercase tracking-[0.14em] text-muted">
          {stream.location_name}
        </span>
      )}
    </Link>
  );
}

function Arrow({
  dir,
  onClick,
  disabled,
}: {
  dir: "prev" | "next";
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={dir === "prev" ? "Scroll left" : "Scroll right"}
      className={`flex h-7 w-7 items-center justify-center rounded-full border border-rule transition-colors ${
        disabled
          ? "cursor-not-allowed text-muted/35"
          : "text-ink hover:bg-paper-2"
      }`}
    >
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d={dir === "prev" ? "M15 18l-6-6 6-6" : "M9 18l6-6-6-6"} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

/**
 * Featured cameras as a horizontal rail rather than a full grid, so the home
 * page leads with the live cameras without spending most of the fold on them.
 */
export default function FeaturedStreams({ streams }: Props) {
  const railRef = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const sync = useCallback(() => {
    const el = railRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 2);
    // 2px slack: fractional widths mean scrollLeft rarely lands exactly on the
    // maximum, which would otherwise leave the next arrow permanently enabled.
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 2);
  }, []);

  useEffect(() => {
    sync();
    const el = railRef.current;
    if (!el) return;
    const ro = new ResizeObserver(sync);
    ro.observe(el);
    return () => ro.disconnect();
  }, [sync, streams.length]);

  const nudge = (dir: 1 | -1) => {
    const el = railRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.round(el.clientWidth * 0.8), behavior: "smooth" });
  };

  if (streams.length === 0) return null;

  return (
    <section className="mb-9">
      <style>{`
        .ww-rail {
          /* Fade both edges so cards dissolve rather than being cut off. The
             fade is inset by a hair at each end once you can't scroll further,
             otherwise the first and last card look permanently faded. */
          -webkit-mask-image: linear-gradient(to right, transparent, #000 5%, #000 95%, transparent);
          mask-image: linear-gradient(to right, transparent, #000 5%, #000 95%, transparent);
        }
        .ww-rail.at-start {
          -webkit-mask-image: linear-gradient(to right, #000 0, #000 95%, transparent);
          mask-image: linear-gradient(to right, #000 0, #000 95%, transparent);
        }
        .ww-rail.at-end {
          -webkit-mask-image: linear-gradient(to right, transparent, #000 5%, #000 100%);
          mask-image: linear-gradient(to right, transparent, #000 5%, #000 100%);
        }
        .ww-rail.at-start.at-end {
          -webkit-mask-image: none;
          mask-image: none;
        }
        .ww-rail::-webkit-scrollbar { display: none; }
        .ww-card { width: 260px; }
        @media (max-width: 640px) { .ww-card { width: 208px; } }
      `}</style>

      <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-rule pb-3">
        <h2 className="font-serif text-[24px] font-medium tracking-tight text-ink">
          Featured streams
        </h2>
        <div className="flex items-center gap-2.5">
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.14em] text-muted sm:inline">
            Plays on WildWatch
          </span>
          <div className="flex gap-1.5">
            <Arrow dir="prev" onClick={() => nudge(-1)} disabled={atStart} />
            <Arrow dir="next" onClick={() => nudge(1)} disabled={atEnd} />
          </div>
        </div>
      </div>

      <div
        ref={railRef}
        onScroll={sync}
        className={`ww-rail flex snap-x snap-mandatory gap-4 overflow-x-auto pb-1 [scrollbar-width:none] ${
          atStart ? "at-start" : ""
        } ${atEnd ? "at-end" : ""}`}
      >
        {streams.map((s) => (
          <FeaturedCard key={s.id} stream={s} />
        ))}
      </div>
    </section>
  );
}
