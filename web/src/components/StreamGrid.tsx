"use client";

import { useMemo, useState } from "react";
import type { Stream, Detection } from "@/lib/supabase/types";
import {
  DETECTION_STALE_SECONDS,
  STREAM_WILDLIFE_CATEGORY,
  type WildlifeCategory,
} from "@/lib/constants";
import StreamCard from "./StreamCard";
import FilterBar from "./FilterBar";
import SortSelect, { type SortOption } from "./SortSelect";

interface StreamGridProps {
  initialStreams: Stream[];
  cardDetections?: Detection[];
}

export default function StreamGrid({ initialStreams, cardDetections = [] }: StreamGridProps) {
  const streams = initialStreams;
  const [search, setSearch] = useState("");
  const [showAnimalsOnly, setShowAnimalsOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<WildlifeCategory | "">("");
  const [speciesFilter, setSpeciesFilter] = useState("");
  const [sort, setSort] = useState<SortOption>("latest");

  const detsByStream = useMemo(() => {
    // Group by stream_id, then keep only the most recent frame's detections (top 3)
    const byStream = new Map<string, Detection[]>();
    cardDetections.forEach((d) => {
      if (!byStream.has(d.stream_id)) byStream.set(d.stream_id, []);
      byStream.get(d.stream_id)!.push(d);
    });
    const result = new Map<string, Detection[]>();
    Array.from(byStream.entries()).forEach(([streamId, dets]) => {
      dets.sort((a: Detection, b: Detection) =>
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      );
      // Only keep detections from the most recent thumbnail
      const latestThumb = dets[0]?.thumbnail_path;
      const latest = latestThumb
        ? dets.filter((d: Detection) => d.thumbnail_path === latestThumb)
        : dets;
      // Cap at 3 for card view
      latest.sort((a: Detection, b: Detection) => b.confidence - a.confidence);
      result.set(streamId, latest.slice(0, 3));
    });
    return result;
  }, [cardDetections]);

  const availableSpecies = useMemo(() => {
    const names = new Set<string>();
    streams.forEach((s) => {
      if (s.latest_detection_common_name) {
        names.add(s.latest_detection_common_name);
      }
    });
    return Array.from(names).sort();
  }, [streams]);

  const filtered = useMemo(() => {
    let result = [...streams];

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.location_name?.toLowerCase().includes(q) ||
          s.latest_detection_common_name?.toLowerCase().includes(q)
      );
    }

    if (categoryFilter) {
      result = result.filter(
        (s) => STREAM_WILDLIFE_CATEGORY[s.slug] === categoryFilter
      );
    }

    if (showAnimalsOnly) {
      const now = Date.now();
      result = result.filter((s) => {
        if (
          s.latest_detection_category !== "animal" ||
          !s.latest_detection_at ||
          !s.latest_detection_common_name
        ) {
          return false;
        }
        const age = (now - new Date(s.latest_detection_at).getTime()) / 1000;
        return age < DETECTION_STALE_SECONDS;
      });
    }

    if (speciesFilter) {
      result = result.filter(
        (s) => s.latest_detection_common_name === speciesFilter
      );
    }

    switch (sort) {
      case "latest":
        result.sort((a, b) => {
          const aTime = a.latest_detection_at
            ? new Date(a.latest_detection_at).getTime()
            : 0;
          const bTime = b.latest_detection_at
            ? new Date(b.latest_detection_at).getTime()
            : 0;
          return bTime - aTime;
        });
        break;
      case "name":
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "species":
        result.sort((a, b) =>
          (a.latest_detection_common_name ?? "").localeCompare(
            b.latest_detection_common_name ?? ""
          )
        );
        break;
    }

    return result;
  }, [streams, search, showAnimalsOnly, categoryFilter, speciesFilter, sort]);

  return (
    <div>
      <div className="border-y border-rule py-4 mb-7">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            showAnimalsOnly={showAnimalsOnly}
            onToggleAnimals={() => setShowAnimalsOnly((v) => !v)}
            categoryFilter={categoryFilter}
            onCategoryChange={setCategoryFilter}
            speciesFilter={speciesFilter}
            onSpeciesChange={setSpeciesFilter}
            availableSpecies={availableSpecies}
          />
          <SortSelect value={sort} onChange={setSort} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-20 text-center text-muted">
          <p className="text-4xl mb-3">🔭</p>
          <p className="font-serif text-lg italic">No streams match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((stream) => (
            <StreamCard
              key={stream.id}
              stream={stream}
              detections={detsByStream.get(stream.id) ?? []}
            />
          ))}
        </div>
      )}

      <p className="mt-6 text-center font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
        Showing {filtered.length} of {streams.length} streams
      </p>
    </div>
  );
}
