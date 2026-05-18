"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { createClient } from "@/lib/supabase/client";

interface HourlyData {
  hour: number;
  detection_count: number;
}

interface Props {
  streamId: string;
  longitude: number | null;
}

/** Approximate UTC offset from longitude (e.g. longitude 35 -> +2h) */
function getUtcOffset(longitude: number | null): number {
  if (longitude === null) return 0;
  return Math.round(longitude / 15);
}

/** Convert a UTC hour to local hour given an offset */
function utcToLocal(utcHour: number, offset: number): number {
  return ((utcHour + offset) % 24 + 24) % 24;
}

function fmtHr(h: number): string {
  const ampm = h < 12 ? "AM" : "PM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}${ampm}`;
}

function isNight(h: number): boolean {
  return h < 6 || h >= 19;
}

function ActivityChart({ data, max, peakIdx }: { data: number[]; max: number; peakIdx: number }) {
  const [hover, setHover] = useState<{ idx: number; x: number; y: number } | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  return (
    <div className="relative">
      <div
        ref={chartRef}
        className="relative h-[160px] grid grid-cols-[repeat(24,1fr)] items-end gap-[3px] pb-[22px] border-b border-rule before:content-[''] before:absolute before:left-0 before:right-0 before:top-0 before:border-t before:border-dashed before:border-rule-2"
      >
        {data.map((v, i) => {
          const isPeak = i === peakIdx;
          const night = isNight(i);
          const heightPct = v === 0 ? 0 : Math.max((v / max) * 100, 3);
          return (
            <div
              key={i}
              className="flex items-end cursor-default"
              style={{ height: "100%" }}
              onMouseEnter={(e) => {
                const rect = chartRef.current?.getBoundingClientRect();
                const barRect = e.currentTarget.getBoundingClientRect();
                if (rect) {
                  setHover({
                    idx: i,
                    x: barRect.left + barRect.width / 2 - rect.left,
                    y: barRect.bottom - barRect.height * (heightPct / 100) - rect.top,
                  });
                }
              }}
              onMouseLeave={() => setHover(null)}
            >
              <div
                className={`w-full rounded-t-[1px] transition-colors duration-150
                  ${isPeak ? (night ? "bg-accent" : "bg-accent-deep") : night ? "bg-ink-2/40" : "bg-ink-2"}
                  ${hover?.idx === i ? "!bg-accent-deep" : ""}`}
                style={{ height: `${heightPct}%`, minHeight: v > 0 ? 3 : 1 }}
              />
            </div>
          );
        })}
      </div>

      {/* Single floating tooltip */}
      {hover !== null && (
        <div
          className="absolute z-50 pointer-events-none"
          style={{ left: hover.x, top: hover.y - 8, transform: "translate(-50%, -100%)" }}
        >
          <div className="bg-ink text-bg font-mono text-[11px] font-medium px-3 py-1.5 rounded shadow-lg tracking-[0.04em] whitespace-nowrap">
            {fmtHr(hover.idx)} · {data[hover.idx]} obs
          </div>
          <div className="flex justify-center">
            <div className="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[5px] border-t-ink" />
          </div>
        </div>
      )}
    </div>
  );
}

export default function ActivityMonitor({ streamId, longitude }: Props) {
  const [rawData, setRawData] = useState<HourlyData[]>([]);
  const [loading, setLoading] = useState(true);
  const offset = getUtcOffset(longitude);

  useEffect(() => {
    async function fetch() {
      const supabase = createClient();
      const { data, error } = await (supabase as any).rpc("get_hourly_activity", {
        p_stream_id: streamId,
      });
      if (!error && data) setRawData(data);
      setLoading(false);
    }
    fetch();
  }, [streamId]);

  // Fill all 24 hours (0-23) in LOCAL time, defaulting to 0
  const data = useMemo(() => {
    const map = new Map<number, number>();
    for (const r of rawData) {
      const localHour = utcToLocal(r.hour, offset);
      map.set(localHour, (map.get(localHour) ?? 0) + r.detection_count);
    }
    return Array.from({ length: 24 }, (_, i) => map.get(i) ?? 0);
  }, [rawData, offset]);

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
        <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
          <h3 className="font-serif text-[22px] font-medium tracking-tight">
            Activity by hour<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 24h</em>
          </h3>
        </div>
        <div className="h-[160px] animate-pulse bg-paper-2 rounded" />
      </section>
    );
  }

  if (total === 0) {
    return (
      <section className="flex flex-col">
        <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
          <h3 className="font-serif text-[22px] font-medium tracking-tight">
            Activity by hour<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 24h</em>
          </h3>
          <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted">0 detections</span>
        </div>
        <p className="py-8 text-center font-serif text-sm italic text-muted">
          No activity recorded in the last 24 hours.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
        <h3 className="font-serif text-[22px] font-medium tracking-tight">
          Activity by hour<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 24h · {tzLabel}</em>
        </h3>
        <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted">{total} detections</span>
      </div>

      {/* Chart */}
      <ActivityChart data={data} max={max} peakIdx={peakIdx} />

      {/* Axis labels */}
      <div className="flex justify-between mt-2 font-mono text-[9px] tracking-[0.1em] text-muted px-0">
        <span>12AM</span>
        <span>6AM</span>
        <span>12PM</span>
        <span>6PM</span>
        <span></span>
      </div>

      {/* Footer stats */}
      <dl className="mt-[18px] grid grid-cols-3 gap-[18px] border-t border-rule pt-4">
        <div>
          <dt className="font-mono text-[9.5px] tracking-[0.14em] uppercase text-muted">Peak hour</dt>
          <dd className="mt-1 font-serif text-[20px] font-medium tracking-tight">
            {fmtHr(peakIdx)}
            <small className="font-mono text-[10px] text-muted ml-1.5 tracking-[0.04em] font-normal">{data[peakIdx]} obs</small>
          </dd>
        </div>
        <div>
          <dt className="font-mono text-[9.5px] tracking-[0.14em] uppercase text-muted">Quietest</dt>
          <dd className="mt-1 font-serif text-[20px] font-medium tracking-tight">
            {fmtHr(minIdx)}
            <small className="font-mono text-[10px] text-muted ml-1.5 tracking-[0.04em] font-normal">{minVal} obs</small>
          </dd>
        </div>
        <div>
          <dt className="font-mono text-[9.5px] tracking-[0.14em] uppercase text-muted">Day / night split</dt>
          <dd className="mt-1 font-serif text-[20px] font-medium tracking-tight">
            {dayPct}%
            <small className="font-mono text-[10px] text-muted ml-1.5 tracking-[0.04em] font-normal">day</small>
          </dd>
        </div>
      </dl>
    </section>
  );
}
