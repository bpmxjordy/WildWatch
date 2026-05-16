"use client";

import { useEffect, useState, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Detection } from "@/lib/supabase/types";

export function useStreamDetections(streamId: string) {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(true);
  const supabaseRef = useRef(createClient());

  useEffect(() => {
    const supabase = supabaseRef.current;

    async function fetchDetections() {
      const { data } = await supabase
        .from("detections")
        .select("*")
        .eq("stream_id", streamId)
        .order("detected_at", { ascending: false })
        .limit(5);
      setDetections(data ?? []);
      setLoading(false);
    }
    fetchDetections();

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
          setDetections((prev) => [payload.new as Detection, ...prev].slice(0, 5));
        }
      )
      .subscribe((status) => {
        if (status === "CHANNEL_ERROR") {
          console.debug("[WildWatch] Realtime not available for detections");
        }
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [streamId]);

  return { detections, loading };
}
