"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { getSpeciesEmoji, timeAgo } from "@/lib/utils";

interface SpeciesRow {
  common_name: string;
  species_label: string | null;
  detection_count: number;
  avg_confidence: number;
  last_seen: string;
}

interface Props {
  streamId: string;
}

export default function SpeciesBreakdown({ streamId }: Props) {
  const [data, setData] = useState<SpeciesRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      const supabase = createClient();
      const { data: rows, error } = await (supabase as any).rpc("get_species_breakdown", {
        p_stream_id: streamId,
      });
      if (!error && rows) setData(rows);
      setLoading(false);
    }
    fetch();
  }, [streamId]);

  const total = data.reduce((a, b) => a + b.detection_count, 0);
  const max = data.length > 0 ? data[0].detection_count : 1;

  if (loading) {
    return (
      <section className="flex flex-col">
        <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
          <h3 className="font-serif text-[22px] font-medium tracking-tight">
            Most detected<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 7 days</em>
          </h3>
        </div>
        <div className="space-y-3.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-10 animate-pulse bg-paper-2 rounded" />
          ))}
        </div>
      </section>
    );
  }

  if (data.length === 0) {
    return (
      <section className="flex flex-col">
        <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
          <h3 className="font-serif text-[22px] font-medium tracking-tight">
            Most detected<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 7 days</em>
          </h3>
          <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted">0 total</span>
        </div>
        <p className="py-8 text-center font-serif text-sm italic text-muted">
          No species detected in the last 7 days.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-[18px] pb-2.5 border-b border-rule">
        <h3 className="font-serif text-[22px] font-medium tracking-tight">
          Most detected<em className="not-italic font-normal text-muted text-sm ml-2 italic">last 7 days</em>
        </h3>
        <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted">{total} total</span>
      </div>

      {/* Species list */}
      <div className="flex flex-col gap-3.5">
        {data.map((row, i) => {
          const pct = total > 0 ? (row.detection_count / total) * 100 : 0;
          const isLead = i === 0;
          const emoji = getSpeciesEmoji(row.common_name);

          // Extract latin name from species_label (format: "genus;species;common")
          const latinParts = row.species_label?.split(";") ?? [];
          const latinName = latinParts.length >= 2
            ? `${latinParts[latinParts.length - 2]} ${latinParts[latinParts.length - 1]}`.trim()
            : null;

          return (
            <div
              key={row.common_name}
              className="grid grid-cols-[28px_1fr_auto] gap-3 items-center"
            >
              {/* Glyph */}
              <span
                className={`w-7 h-7 rounded-full inline-flex items-center justify-center font-serif font-medium text-[13px] border
                  ${isLead
                    ? "bg-accent-deep text-[#f5f7f2] border-accent-deep"
                    : "bg-paper-2 text-ink-2 border-rule"
                  }`}
              >
                {emoji}
              </span>

              {/* Name + bar */}
              <div className="flex flex-col gap-1.5 min-w-0">
                <span className="flex items-baseline gap-2.5">
                  <span className="font-serif text-[16px] font-medium tracking-tight truncate">
                    {row.common_name}
                  </span>
                  {latinName && (
                    <span className="font-serif italic text-[12px] text-muted truncate">
                      {latinName}
                    </span>
                  )}
                </span>
                <span className="relative h-1 bg-rule rounded-[2px] overflow-hidden">
                  <i
                    className={`absolute inset-y-0 left-0 rounded-[2px] transition-[width] duration-[600ms] ease-[cubic-bezier(0.22,1,0.36,1)]
                      ${isLead ? "bg-accent-deep" : "bg-ink-2"}`}
                    style={{ width: `${(row.detection_count / max) * 100}%` }}
                  />
                </span>
              </div>

              {/* Count */}
              <div className="font-mono text-[11px] text-ink-2 tracking-[0.04em] whitespace-nowrap text-right">
                {row.detection_count}
                <span className="block text-[9.5px] text-muted mt-0.5">
                  {pct.toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-auto pt-[18px] border-t border-rule flex justify-between font-mono text-[10px] tracking-[0.14em] uppercase text-muted">
        <span>{data.length} species observed</span>
        <span>Updated {data[0] ? timeAgo(data[0].last_seen) : "—"}</span>
      </div>
    </section>
  );
}
