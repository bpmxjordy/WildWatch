"use client";

import Link from "next/link";
import type { Stream } from "@/lib/supabase/types";

interface Props {
  streams: Stream[];
}

/**
 * Cameras that play inline on their stream page rather than linking out to a
 * third-party site.
 *
 * These deliberately do *not* play here. Mounting five live HLS streams on the
 * home page pulled several megabits from the Smithsonian's CDN on every visit,
 * for video most visitors would scroll straight past. The card is a still with
 * a Live badge; playback starts when the visitor actually asks for it by
 * opening the stream.
 */
function FeaturedCard({ stream }: { stream: Stream }) {
  const poster = stream.latest_detection_thumbnail_url || stream.thumbnail_url;

  return (
    <Link href={`/stream/${stream.slug}`} className="group flex flex-col">
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

        <span className="pointer-events-none absolute left-2.5 top-2.5 flex items-center gap-1.5 rounded bg-[#1e3320]/90 px-2 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-[#8fd177]" />
          Live
        </span>

        {/* Play affordance, so it's clear the still leads to a running stream */}
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-black/35 opacity-0 backdrop-blur-sm transition-opacity duration-200 group-hover:opacity-100">
            <svg viewBox="0 0 24 24" className="ml-0.5 h-5 w-5 fill-white">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
        </span>
      </div>

      <div className="mt-2.5 flex items-baseline justify-between gap-3">
        <span className="truncate font-serif text-[16px] font-medium tracking-tight group-hover:underline">
          {stream.name}
        </span>
        {stream.location_name && (
          <span className="shrink-0 font-mono text-[9.5px] uppercase tracking-[0.14em] text-muted">
            {stream.location_name}
          </span>
        )}
      </div>
    </Link>
  );
}

/**
 * Shown on the home page until the visitor narrows the list — once they're
 * filtering, they've said what they want and a fixed set of cameras is noise.
 */
export default function FeaturedStreams({ streams }: Props) {
  if (streams.length === 0) return null;

  return (
    <section className="mb-10">
      <div className="mb-5 flex items-baseline justify-between border-b border-rule pb-3.5">
        <h2 className="font-serif text-[26px] font-medium tracking-tight text-ink">
          Watch live
        </h2>
        <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
          Plays on WildWatch
        </span>
      </div>

      <div className="grid grid-cols-1 gap-x-6 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
        {streams.map((s) => (
          <FeaturedCard key={s.id} stream={s} />
        ))}
      </div>
    </section>
  );
}
