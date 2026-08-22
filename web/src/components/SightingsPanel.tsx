"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Props {
  streamId: string;
}

const PERIODS = [
  { key: "24h", label: "24h", hours: 24 },
  { key: "7d", label: "7 days", hours: 24 * 7 },
  { key: "30d", label: "30 days", hours: 24 * 30 },
] as const;

type PeriodKey = (typeof PERIODS)[number]["key"];

interface EventRow {
  common_name: string;
  sighting_count: number;
  total_seconds: number;
  avg_seconds: number;
  longest_seconds: number;
  peak_confidence: number | null;
  last_seen: string;
}

interface Summary {
  sighting_count: number;
  species_count: number;
  total_seconds: number;
  longest_seconds: number;
  open_count: number;
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[22px] tabular-nums">{value}</div>
      <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
        {label}
      </div>
    </div>
  );
}

/**
 * Sightings — distinct visits, as opposed to the per-frame samples in
 * "Activity by hour".
 *
 * One animal lingering on camera is a single sighting here but many detections
 * there, so the two panels will disagree by design. That's the point: activity
 * measures how much the camera saw, sightings measure how many animals showed
 * up.
 */
export default function SightingsPanel({ streamId }: Props) {
  const [period, setPeriod] = useState<PeriodKey>("24h");
  const [rows, setRows] = useState<EventRow[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();
    const hours = PERIODS.find((p) => p.key === period)!.hours;
    const since = new Date(Date.now() - hours * 3600 * 1000).toISOString();

    async function load() {
      setLoading(true);
      const [ev, sum] = await Promise.all([
        (supabase as any).rpc("get_events_since", { p_stream_id: streamId, p_since: since }),
        (supabase as any).rpc("get_event_summary_since", { p_stream_id: streamId, p_since: since }),
      ]);
      if (cancelled) return;
      setRows((ev.data as EventRow[]) ?? []);
      setSummary(((sum.data as Summary[]) ?? [])[0] ?? null);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [streamId, period]);

  const maxCount = Math.max(...(rows ?? []).map((r) => r.sighting_count), 1);

  return (
    <section className="flex flex-col">
      <div className="mb-[18px] flex items-baseline justify-between border-b border-rule pb-2.5">
        <h3 className="font-serif text-[22px] font-medium tracking-tight">
          Sightings
          <em className="ml-2 text-sm font-normal not-italic italic text-muted">
            distinct visits
          </em>
        </h3>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`rounded px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] transition-colors ${
                period === p.key
                  ? "bg-[#1e3320] text-white"
                  : "text-muted hover:text-ink"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-[160px] animate-pulse rounded bg-paper-2" />
      ) : !summary || summary.sighting_count === 0 ? (
        <p className="py-8 text-center font-serif italic text-muted">
          No sightings recorded in this window.
        </p>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-4 gap-4">
            <Stat label="Sightings" value={String(summary.sighting_count)} />
            <Stat label="Species" value={String(summary.species_count)} />
            <Stat label="On camera" value={duration(summary.total_seconds)} />
            <Stat label="Longest" value={duration(summary.longest_seconds)} />
          </div>

          {summary.open_count > 0 && (
            <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.14em] text-[#6a9b5a]">
              ● {summary.open_count} on screen now
            </p>
          )}

          <ul className="flex flex-col gap-2.5">
            {rows!.map((r) => (
              <li key={r.common_name} className="flex items-center gap-3">
                <span className="w-[38%] shrink-0 truncate font-serif text-[15px]">
                  {r.common_name}
                </span>
                <span className="relative h-[6px] flex-1 overflow-hidden rounded-full bg-paper-2">
                  <span
                    className="absolute inset-y-0 left-0 rounded-full bg-[#6a9b5a]"
                    style={{ width: `${(r.sighting_count / maxCount) * 100}%` }}
                  />
                </span>
                <span className="w-[3.5rem] shrink-0 text-right font-mono text-[12px] tabular-nums">
                  {r.sighting_count}×
                </span>
                <span className="w-[4.5rem] shrink-0 text-right font-mono text-[11px] tabular-nums text-muted">
                  {duration(r.avg_seconds)} avg
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
