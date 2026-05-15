"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Detection } from "@/lib/supabase/types";

export function useStreamDetections(streamId: string) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    async function fetch() {
      const { data } = await supabase
        .from("detections")
        .select("*")
        .eq("stream_id", streamId)
        .order("detected_at", { ascending: false })
        .limit(50);
      setDetections(data ?? []);
      setLoading(false);
    }
    fetch();

    const channel = supabase
      .channel(`detections-${streamId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "detections",
          filter: `stream_id=eq.${streamId}`,
        },
        (payload) => {
          setDetections((prev) => [payload.new as Detection, ...prev].slice(0, 50));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabase, streamId]);

  return { detections, loading };
}
