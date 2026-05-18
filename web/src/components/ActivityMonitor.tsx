"use client";

import { useEffect, useState, useMemo } from "react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface HourlyData {
  hour: number;
  detection_count: number;
}

interface Props {
  streamId: string;
}

function fmtHr(h: number): string {
  const ampm = h < 12 ? "AM" : "PM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}${ampm}`;
}

function isNight(h: number): boolean {
  return h < 6 || h >= 19;
}

export default function ActivityMonitor({ streamId }: Props) {
  const [rawData, setRawData] = useState<HourlyData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      const { data, error } = await supabase.rpc("get_hourly_activity", {
        p_stream_id: streamId,
      });
      if (!error && data) setRawData(data);
      setLoading(false);
    }
    fetch();
  }, [streamId]);

  // Fill all 24 hours (0-23), defaulting to 0
  const data = useMemo(() => {
    const map = new Map(rawData.map((r) => [r.hour, r.detection_count]));
    return Array.from({ length: 24 }, (_, i) => map.get(i) ?? 0);
  }, [rawData]);

  const max = Math.max(...data, 1);
  const total = data.reduce((a, b) => a + b, 0);
  const peakIdx = data.indexOf(Math.max(...data));
  const minVal = Math.min(...data);
  const minIdx = data.indexOf(minVal);
  const dayCount = data.reduce((a, v, i) => a + (isNight(i) ? 0 : v), 0);
  const dayPct = total > 0 ? Math.round((dayCount / total) * 100) : 0;

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
          Activity by hour<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 24h</em>
        </h3>
        <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted">{total} detections</span>
      </div>

      {/* Chart */}
      <div className="relative h-[160px] grid grid-cols-[repeat(24,1fr)] items-end gap-[3px] pb-[22px] border-b border-rule before:content-[''] before:absolute before:left-0 before:right-0 before:top-0 before:border-t before:border-dashed before:border-rule-2">
        {data.map((v, i) => {
          const isPeak = i === peakIdx;
          const night = isNight(i);
          return (
            <div
              key={i}
              className={`relative rounded-t-[1px] min-h-[2px] cursor-default transition-all duration-150 group
                ${isPeak ? (night ? "bg-accent" : "bg-accent-deep") : night ? "bg-ink-2/40" : "bg-ink-2"}
                hover:bg-accent-deep hover:scale-y-[1.02] origin-bottom`}
              style={{ height: `${(v / max) * 100}%` }}
            >
              <span className="absolute bottom-[calc(100%+6px)] left-1/2 -translate-x-1/2 bg-ink text-bg font-mono text-[10px] px-1.5 py-[3px] rounded-[2px] whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity tracking-[0.04em]">
                {fmtHr(i)} · {v} obs
              </span>
            </div>
          );
        })}
      </div>

      {/* Axis */}
      <div className="grid grid-cols-[repeat(24,1fr)] gap-[3px] mt-2 font-mono text-[9px] tracking-[0.1em] text-muted">
        {Array.from({ length: 24 }, (_, i) => (
          <span key={i} className={`text-center ${i % 6 === 0 ? "visible" : "invisible"}`}>
            {i === 0 ? "12A" : i === 6 ? "6A" : i === 12 ? "12P" : i === 18 ? "6P" : ""}
          </span>
        ))}
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
