"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import type { StreamStats } from "@/lib/supabase/types";

interface Props {
  streamId: string;
  longitude: number | null;
}

const PERIODS = [
  { key: "24h", label: "24h" },
  { key: "48h", label: "48h" },
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
] as const;

type PeriodKey = (typeof PERIODS)[number]["key"];

function getUtcOffset(longitude: number | null): number {
  if (longitude === null) return 0;
  return Math.round(longitude / 15);
}

function utcToLocal(utcHour: number, offset: number): number {
  return (((utcHour + offset) % 24) + 24) % 24;
}

function fmtHr(h: number): string {
  const ampm = h < 12 ? "AM" : "PM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}${ampm}`;
}

function isNight(h: number): boolean {
  return h < 6 || h >= 19;
}

function ActivityChart({
  data,
  max,
  peakIdx,
  unit = "obs",
}: {
  data: number[];
  max: number;
  peakIdx: number;
  unit?: string;
}) {
  const [hover, setHover] = useState<{
    idx: number;
    x: number;
    y: number;
  } | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  return (
    <div className="relative">
      <div
        ref={chartRef}
        className="relative grid h-[160px] grid-cols-[repeat(24,1fr)] items-end gap-[3px] border-b border-rule pb-[22px] before:absolute before:left-0 before:right-0 before:top-0 before:border-t before:border-dashed before:border-rule-2 before:content-['']"
      >
        {data.map((v, i) => {
          const isPeak = i === peakIdx;
          const night = isNight(i);
          const heightPct = v === 0 ? 0 : Math.max((v / max) * 100, 3);
          return (
            <div
              key={i}
              className="flex cursor-default items-end"
              style={{ height: "100%" }}
              onMouseEnter={(e) => {
                const rect = chartRef.current?.getBoundingClientRect();
                const barRect = e.currentTarget.getBoundingClientRect();
                if (rect) {
                  setHover({
                    idx: i,
                    x: barRect.left + barRect.width / 2 - rect.left,
                    y:
                      barRect.bottom -
                      barRect.height * (heightPct / 100) -
                      rect.top,
                  });
                }
              }}
              onMouseLeave={() => setHover(null)}
            >
              <div
                className={`w-full rounded-t-[1px] transition-colors duration-150
                  ${isPeak ? (night ? "bg-accent" : "bg-accent-deep") : night ? "bg-ink-2/40" : "bg-ink-2"}
                  ${hover?.idx === i ? "!bg-accent-deep" : ""}`}
                style={{
                  height: `${heightPct}%`,
                  minHeight: v > 0 ? 3 : 1,
                }}
              />
            </div>
          );
        })}
      </div>

      {hover !== null && (
        <div
          className="pointer-events-none absolute z-50"
          style={{
            left: hover.x,
            top: hover.y - 8,
            transform: "translate(-50%, -100%)",
          }}
        >
          <div className="whitespace-nowrap rounded bg-[#1e3320] px-3 py-1.5 font-mono text-[11px] font-medium tracking-[0.04em] text-white shadow-lg">
            {fmtHr(hover.idx)} &middot; {data[hover.idx]} {unit}
          </div>
          <div className="flex justify-center">
            <div className="h-0 w-0 border-l-[5px] border-r-[5px] border-t-[5px] border-l-transparent border-r-transparent border-t-[#1e3320]" />
          </div>
        </div>
      )}
    </div>
  );
}

/** Compact duration: 45s, 12m, 2h 5m. */
function duration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  const h = Math.floor(s / 3600);
  const m = Math.round((s % 3600) / 60);
  return m ? `${h}h ${m}m` : `${h}h`;
}

function Metric({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div>
      <dt className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-muted">
        {label}
      </dt>
      <dd className="mt-1 font-serif text-[20px] font-medium tracking-tight">
        {value}
        <small className="ml-1.5 font-mono text-[10px] font-normal tracking-[0.04em] text-muted">
          {unit}
        </small>
      </dd>
    </div>
  );
}

interface EventSummary {
  sighting_count: number;
  species_count: number;
  total_seconds: number;
  longest_seconds: number;
  open_count: number;
}

const PERIOD_HOURS: Record<PeriodKey, number> = {
  "24h": 24,
  "48h": 48,
  "7d": 24 * 7,
  "30d": 24 * 30,
};

type Mode = "detections" | "sightings";

export default function ActivityMonitor({ streamId, longitude }: Props) {
  const [stats, setStats] = useState<StreamStats["stats"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<PeriodKey>("24h");
  const [mode, setMode] = useState<Mode>("detections");
  const offset = getUtcOffset(longitude);

  // Sightings are queried live -- species_events holds one row per visit, so
  // unlike detections it doesn't need the pre-computed stream_stats path.
  const [eventHourly, setEventHourly] = useState<number[] | null>(null);
  const [eventSummary, setEventSummary] = useState<EventSummary | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);

  useEffect(() => {
    if (mode !== "sightings") return;
    let cancelled = false;
    const supabase = createClient();
    const since = new Date(
      Date.now() - PERIOD_HOURS[period] * 3600 * 1000
    ).toISOString();

    async function loadEvents() {
      setEventsLoading(true);
      const [hourly, summary] = await Promise.all([
        (supabase as any).rpc("get_event_hourly_since", {
          p_stream_id: streamId,
          p_since: since,
        }),
        (supabase as any).rpc("get_event_summary_since", {
          p_stream_id: streamId,
          p_since: since,
        }),
      ]);
      if (cancelled) return;
      const buckets = Array.from({ length: 24 }, () => 0);
      for (const r of hourly.data ?? []) buckets[r.hour] = r.sighting_count;
      setEventHourly(buckets);
      setEventSummary((summary.data ?? [])[0] ?? null);
      setEventsLoading(false);
    }

    loadEvents();
    return () => {
      cancelled = true;
    };
  }, [streamId, period, mode]);

  useEffect(() => {
    async function fetch() {
      const supabase = createClient();

      // Try pre-calculated stats first
      const { data: row } = await supabase
        .from("stream_stats")
        .select("stats")
        .eq("stream_id", streamId)
        .single();

      if (row?.stats) {
        const parsed =
          typeof row.stats === "string" ? JSON.parse(row.stats) : row.stats;
        setStats(parsed);
        setLoading(false);
        return;
      }

      // Fallback: compute 24h from RPC
      const { data: rpcData } = await (supabase as any).rpc(
        "get_hourly_activity",
        { p_stream_id: streamId }
      );
      if (rpcData) {
        const hourly = Array.from({ length: 24 }, () => 0);
        for (const r of rpcData) hourly[r.hour] = r.detection_count;
        setStats({
          "24h": { hourly, total: hourly.reduce((a, b) => a + b, 0), species: [] },
        });
      }
      setLoading(false);
    }
    fetch();
  }, [streamId]);

  const periodData = stats?.[period];
  const detectionHourly = periodData?.hourly ?? Array.from({ length: 24 }, () => 0);
  const rawHourly =
    mode === "sightings"
      ? eventHourly ?? Array.from({ length: 24 }, () => 0)
      : detectionHourly;

  const data = useMemo(() => {
    return rawHourly.map((_, i) => rawHourly[((i - offset) % 24 + 24) % 24]);
  }, [rawHourly, offset]);

  const max = Math.max(...data, 1);
  const total = data.reduce((a, b) => a + b, 0);
  const peakIdx = data.indexOf(Math.max(...data));
  const minVal = Math.min(...data);
  const minIdx = data.indexOf(minVal);
  const dayCount = data.reduce((a, v, i) => a + (isNight(i) ? 0 : v), 0);
  const dayPct = total > 0 ? Math.round((dayCount / total) * 100) : 0;

  const tzLabel = offset >= 0 ? `UTC+${offset}` : `UTC${offset}`;

  if (loading) {
    return (
      <section className="flex flex-col">
        <div className="mb-[18px] flex items-baseline justify-between border-b border-rule pb-2.5">
          <h3 className="font-serif text-[22px] font-medium tracking-tight">
            Activity by hour
          </h3>
        </div>
        <div className="h-[160px] animate-pulse rounded bg-paper-2" />
      </section>
    );
  }

  return (
    <section className="flex flex-col">
      {/* Header with period tabs */}
      <div className="mb-[18px] flex items-baseline justify-between border-b border-rule pb-2.5">
        <h3 className="font-serif text-[22px] font-medium tracking-tight">
          Activity by hour
          <em className="ml-2 text-sm font-normal not-italic text-muted italic">
            {tzLabel}
          </em>
        </h3>
        <div className="flex items-center gap-1">
          {PERIODS.map((p) => {
            // Sightings are queried live for any window, so the period buttons
            // aren't gated on which pre-computed stats happen to exist.
            const available = mode === "sightings" ? true : stats?.[p.key];
            return (
              <button
                key={p.key}
                onClick={() => setPeriod(p.key)}
                disabled={!available}
                className={`rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                  period === p.key
                    ? "bg-ink text-[var(--bg)]"
                    : available
                      ? "text-muted hover:bg-paper-2"
                      : "cursor-not-allowed text-muted/40"
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Detections count every frame an animal appeared in; sightings count
          each visit once. They disagree by design, so they're separate views
          of the same window rather than one blended number. */}
      <div className="mb-4 flex gap-4 border-b border-rule-2">
        {(
          [
            ["detections", "Detections", "every frame"],
            ["sightings", "Sightings", "each visit once"],
          ] as const
        ).map(([key, label, hint]) => (
          <button
            key={key}
            onClick={() => setMode(key)}
            className={`-mb-px border-b-2 pb-2 text-left transition-colors ${
              mode === key
                ? "border-accent-deep text-ink"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            <span className="font-mono text-[11px] uppercase tracking-[0.14em]">
              {label}
            </span>
            <span className="ml-1.5 font-serif text-[11px] italic text-muted">
              {hint}
            </span>
          </button>
        ))}
      </div>

      {mode === "sightings" && eventsLoading ? (
        <div className="h-[160px] animate-pulse rounded bg-paper-2" />
      ) : total === 0 ? (
        <p className="py-8 text-center font-serif text-sm italic text-muted">
          {mode === "sightings"
            ? "No sightings recorded in this period."
            : "No activity recorded in this period."}
        </p>
      ) : (
        <>
          <ActivityChart
            data={data}
            max={max}
            peakIdx={peakIdx}
            unit={mode === "sightings" ? "visits" : "obs"}
          />

          {/* Axis labels */}
          <div className="mt-2 flex justify-between px-0 font-mono text-[9px] tracking-[0.1em] text-muted">
            <span>12AM</span>
            <span>6AM</span>
            <span>12PM</span>
            <span>6PM</span>
            <span></span>
          </div>

          {/* Footer stats — sightings can report things a frame count can't,
              like how long an animal actually stayed. */}
          <dl className="mt-[18px] grid grid-cols-3 gap-[18px] border-t border-rule pt-4">
            <Metric
              label="Peak hour"
              value={fmtHr(peakIdx)}
              unit={`${data[peakIdx]} ${mode === "sightings" ? "visits" : "obs"}`}
            />
            {mode === "sightings" ? (
              <>
                <Metric
                  label="Sightings"
                  value={String(eventSummary?.sighting_count ?? total)}
                  unit={`${eventSummary?.species_count ?? 0} species`}
                />
                <Metric
                  label="Longest visit"
                  value={duration(eventSummary?.longest_seconds ?? 0)}
                  unit={`${duration(eventSummary?.total_seconds ?? 0)} total`}
                />
              </>
            ) : (
              <>
                <Metric label="Total" value={String(total)} unit="obs" />
                <Metric label="Day / night" value={`${dayPct}%`} unit="day" />
              </>
            )}
          </dl>

          {mode === "sightings" && (eventSummary?.open_count ?? 0) > 0 && (
            <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-accent-deep">
              ● {eventSummary!.open_count} on screen now
            </p>
          )}
        </>
      )}
    </section>
  );
}
