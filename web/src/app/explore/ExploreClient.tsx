"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import type { Stream } from "@/lib/supabase/types";
import { getSpeciesEmoji, timeAgo } from "@/lib/utils";
import { STREAM_WILDLIFE_CATEGORY, WILDLIFE_CATEGORIES } from "@/lib/constants";
import ActivityClock from "./ActivityClock";
import AmbientField from "./AmbientField";

interface PeriodStats {
  hourly: number[];
  total: number;
  species: { common_name: string; count: number; avg_confidence: number }[];
}
type StreamStats = Record<string, PeriodStats>;

interface ExploreClientProps {
  streams: Stream[];
  statsMap: Record<string, StreamStats>;
}

const PERIODS = [
  { key: "24h", label: "24 hours" },
  { key: "48h", label: "48 hours" },
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
] as const;
type PeriodKey = (typeof PERIODS)[number]["key"];

const CATEGORY_ACCENT: Record<string, string> = {
  mammal: "#7db86a",
  bird: "#d4b45a",
  aquatic: "#3f9d9d",
};

function utcOffset(longitude: number | null): number {
  if (longitude == null) return 0;
  return Math.round(longitude / 15);
}

const EMPTY: PeriodStats = { hourly: Array(24).fill(0), total: 0, species: [] };

export default function ExploreClient({ streams, statsMap }: ExploreClientProps) {
  const usable = useMemo(
    () => streams.filter((s) => s.latest_detection_thumbnail_url || s.thumbnail_url),
    [streams]
  );

  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [period, setPeriod] = useState<PeriodKey>("24h");

  const stream = usable[index];

  const go = useCallback(
    (dir: number) => {
      setDirection(dir);
      setIndex((i) => (i + dir + usable.length) % usable.length);
    },
    [usable.length]
  );

  const jump = useCallback(
    (target: number) => {
      setDirection(target > index ? 1 : -1);
      setIndex(target);
    },
    [index]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  if (!stream) {
    return (
      <div className="-mx-7 -mt-9 flex min-h-[70vh] items-center justify-center">
        <p className="font-serif text-lg italic text-muted">
          No streams available to explore yet.
        </p>
      </div>
    );
  }

  const cat = STREAM_WILDLIFE_CATEGORY[stream.slug];
  const catInfo = cat ? WILDLIFE_CATEGORIES[cat] : null;
  const accent = (cat && CATEGORY_ACCENT[cat]) || "#7db86a";

  const stats = statsMap[stream.id];
  const periodData = stats?.[period] ?? EMPTY;

  // Local-time shift for the clock
  const offset = utcOffset(stream.longitude);
  const localHourly = periodData.hourly.map(
    (_, i) => periodData.hourly[((i - offset) % 24 + 24) % 24]
  );

  const total24h = stats?.["24h"]?.total ?? 0;
  const intensity = Math.min(1, Math.log1p(total24h) / Math.log1p(80));

  const thumb =
    stream.latest_detection_thumbnail_url || stream.thumbnail_url || "";
  const fresh =
    stream.latest_detection_at &&
    Date.now() - new Date(stream.latest_detection_at).getTime() < 5 * 60 * 1000;

  const species = periodData.species.slice(0, 7);
  const maxSpecies = Math.max(...species.map((s) => s.count), 1);

  const slideVariants = {
    enter: (dir: number) => ({ opacity: 0, x: dir * 60, scale: 0.98 }),
    center: { opacity: 1, x: 0, scale: 1 },
    exit: (dir: number) => ({ opacity: 0, x: dir * -60, scale: 0.98 }),
  };

  return (
    <div className="-mx-7 -mt-9">
      <div className="relative overflow-hidden rounded-2xl border border-[#22331f] bg-[#0c130c] text-[#eef5e9] shadow-[0_30px_80px_rgba(0,0,0,0.35)]">
        {/* Ambient particle field */}
        <AmbientField intensity={intensity} color={accent} />

        {/* Vignette */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(120% 90% at 50% 0%, rgba(30,51,32,0.35), transparent 55%), radial-gradient(100% 100% at 50% 120%, rgba(0,0,0,0.5), transparent 60%)",
          }}
        />

        {/* Top bar */}
        <div className="relative flex items-center justify-between px-7 py-5">
          <div>
            <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#8fb085] before:inline-block before:h-px before:w-4 before:bg-[#8fb085]">
              Field Station
            </span>
            <h1 className="mt-1 font-serif text-[26px] font-medium leading-none tracking-tight text-[#eef5e9]">
              Explore
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right font-mono text-[11px] tracking-wider text-[#8fb085]">
              <span className="text-[#eef5e9]">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-[#5f7d63]"> / {String(usable.length).padStart(2, "0")}</span>
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={() => go(-1)}
                aria-label="Previous stream"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-[#2c4429] text-[#b4ceaa] transition-colors hover:border-[#4a7043] hover:bg-[#16221457] hover:text-white"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <button
                onClick={() => go(1)}
                aria-label="Next stream"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-[#2c4429] text-[#b4ceaa] transition-colors hover:border-[#4a7043] hover:bg-[#16221457] hover:text-white"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Stage */}
        <div className="relative px-7 pb-4">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={stream.id}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ type: "spring", stiffness: 260, damping: 30, mass: 0.8 }}
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.15}
              onDragEnd={(_, info) => {
                if (info.offset.x < -80) go(1);
                else if (info.offset.x > 80) go(-1);
              }}
              className="grid grid-cols-1 gap-6 lg:grid-cols-[1.35fr_1fr]"
            >
              {/* Hero viewport */}
              <div className="relative aspect-[16/10] overflow-hidden rounded-xl border border-[#22331f] bg-black">
                <div className="absolute inset-0 overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={thumb}
                    alt={stream.name}
                    className="h-full w-full object-cover"
                    style={{ animation: "explore-kenburns 26s ease-in-out infinite" }}
                  />
                </div>
                <div
                  className="absolute inset-0"
                  style={{
                    background:
                      "linear-gradient(to top, rgba(4,8,4,0.92) 0%, rgba(4,8,4,0.25) 40%, transparent 70%)",
                  }}
                />

                {/* Live badge */}
                <div className="absolute left-4 top-4 flex items-center gap-2">
                  {stream.is_live ? (
                    <span className="relative flex items-center gap-2 rounded-full bg-black/50 px-3 py-1.5 backdrop-blur-md">
                      <span className="relative flex h-2 w-2">
                        <span
                          className="absolute inline-flex h-full w-full rounded-full bg-[#d94040]"
                          style={{ animation: "explore-pulse-ring 1.8s ease-out infinite" }}
                        />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-[#d94040]" />
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white">
                        Live
                      </span>
                    </span>
                  ) : (
                    <span className="rounded-full bg-black/50 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-[#9db89f] backdrop-blur-md">
                      Offline
                    </span>
                  )}
                  {catInfo && (
                    <span className="rounded-full bg-black/40 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[#b4ceaa] backdrop-blur-md">
                      {catInfo.emoji} {catInfo.label}
                    </span>
                  )}
                </div>

                {/* Bottom-left caption */}
                <div className="absolute inset-x-4 bottom-4">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8fb085]">
                    {stream.location_name || "Unknown location"}
                  </span>
                  <h2 className="mt-1 font-serif text-[clamp(24px,3vw,38px)] font-medium leading-none tracking-tight text-white">
                    {stream.name}
                  </h2>
                  {stream.latest_detection_common_name && (
                    <div className="mt-2.5 inline-flex items-center gap-2 rounded-full bg-[#0f1a0d]/80 px-3 py-1.5 backdrop-blur-md">
                      <span className="text-base leading-none">
                        {getSpeciesEmoji(stream.latest_detection_common_name)}
                      </span>
                      <span className="font-mono text-[11px] font-medium tracking-wide text-[#c9e8b8]">
                        {stream.latest_detection_common_name}
                      </span>
                      {stream.latest_detection_confidence != null && (
                        <span className="font-mono text-[10px] text-[#7f9c83]">
                          {Math.round(stream.latest_detection_confidence * 100)}%
                        </span>
                      )}
                      <span className="font-mono text-[10px] text-[#5f7d63]">
                        · {timeAgo(stream.latest_detection_at)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Data panel */}
              <div className="flex flex-col items-center justify-between gap-4 rounded-xl border border-[#1c2b1a] bg-[#0a110a]/60 px-5 py-5 backdrop-blur-sm">
                {/* Period tabs */}
                <div className="flex w-full items-center justify-center gap-1">
                  {PERIODS.map((p) => {
                    const has = !!stats?.[p.key];
                    return (
                      <button
                        key={p.key}
                        onClick={() => setPeriod(p.key)}
                        disabled={!has}
                        className={`rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                          period === p.key
                            ? "bg-[#c9e8b8] text-[#12210f]"
                            : has
                              ? "text-[#8fb085] hover:bg-[#16221457]"
                              : "cursor-not-allowed text-[#3f5642]"
                        }`}
                      >
                        {p.key}
                      </button>
                    );
                  })}
                </div>

                {/* Radial activity clock */}
                <ActivityClock
                  hourly={localHourly}
                  total={periodData.total}
                  periodLabel={PERIODS.find((p) => p.key === period)!.label}
                />

                {/* Species constellation */}
                <div className="w-full">
                  <p className="mb-2 text-center font-mono text-[9px] uppercase tracking-[0.18em] text-[#5f7d63]">
                    {species.length > 0 ? "Species observed" : "No species this period"}
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-1.5">
                    {species.map((sp, i) => {
                      const scale = 0.82 + (sp.count / maxSpecies) * 0.5;
                      return (
                        <motion.span
                          key={sp.common_name}
                          initial={{ opacity: 0, scale: 0.6 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.15 + i * 0.05, type: "spring", stiffness: 300, damping: 20 }}
                          className="inline-flex items-center gap-1.5 rounded-full border border-[#263a22] bg-[#101c0e] px-2.5 py-1"
                          style={{ fontSize: `${scale * 11}px` }}
                        >
                          <span>{getSpeciesEmoji(sp.common_name)}</span>
                          <span className="font-medium text-[#d4e7cb]">
                            {sp.common_name}
                          </span>
                          <span className="font-mono text-[#6f8d73]">{sp.count}</span>
                        </motion.span>
                      );
                    })}
                  </div>
                </div>

                {/* CTA */}
                <Link
                  href={`/stream/${stream.slug}`}
                  className="group inline-flex w-full items-center justify-center gap-2 rounded-full border border-[#3a5a34] bg-[#16281260] py-2.5 font-mono text-[11px] uppercase tracking-[0.16em] text-[#c9e8b8] transition-colors hover:bg-[#1d3a19] hover:text-white"
                >
                  Open full camera
                  <svg
                    className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </Link>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Filmstrip */}
        <div className="relative border-t border-[#1a2718] px-7 py-4">
          <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "thin" }}>
            {usable.map((s, i) => {
              const active = i === index;
              const st = s.latest_detection_thumbnail_url || s.thumbnail_url || "";
              return (
                <button
                  key={s.id}
                  onClick={() => jump(i)}
                  className={`relative h-14 w-24 flex-shrink-0 overflow-hidden rounded-md border transition-all ${
                    active
                      ? "border-[#c9e8b8] ring-2 ring-[#6a9b5a]/40"
                      : "border-[#20301d] opacity-55 hover:opacity-90"
                  }`}
                  style={{ scrollSnapAlign: "center" }}
                  title={s.name}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={st} alt={s.name} className="h-full w-full object-cover" loading="lazy" />
                  {s.is_live && (
                    <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[#d94040] shadow-[0_0_5px_#d94040]" />
                  )}
                  {active && (
                    <motion.div
                      layoutId="filmstrip-active"
                      className="absolute inset-x-0 bottom-0 h-0.5 bg-[#c9e8b8]"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Hint bar */}
        <div className="relative flex items-center justify-center gap-4 border-t border-[#141f12] px-7 py-2.5 font-mono text-[9.5px] uppercase tracking-[0.16em] text-[#4d6650]">
          <span className="flex items-center gap-1.5">
            <kbd className="rounded border border-[#26382330] px-1.5 py-0.5 text-[#7f9c83]">←</kbd>
            <kbd className="rounded border border-[#26382330] px-1.5 py-0.5 text-[#7f9c83]">→</kbd>
            navigate
          </span>
          <span className="text-[#2f4230]">·</span>
          <span>drag or swipe the stage</span>
          <span className="text-[#2f4230]">·</span>
          <span>click a frame below</span>
        </div>
      </div>
    </div>
  );
}
