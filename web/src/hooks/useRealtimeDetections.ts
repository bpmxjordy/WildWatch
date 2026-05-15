"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Stream } from "@/lib/supabase/types";

export function useRealtimeDetections(initialStreams: Stream[]) {
  const [streams, setStreams] = useState(initialStreams);
  const supabase = createClient();

  useEffect(() => {
    setStreams(initialStreams);
  }, [initialStreams]);

  useEffect(() => {
    const channel = supabase
      .channel("stream-detections")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "streams",
          filter: "is_active=eq.true",
        },
        (payload) => {
          setStreams((prev) =>
            prev.map((s) =>
              s.id === payload.new.id ? { ...s, ...payload.new } : s
            )
          );
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabase]);

  return streams;
}
