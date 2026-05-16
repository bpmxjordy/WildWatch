"use client";

import { useEffect, useState, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Stream } from "@/lib/supabase/types";

export function useRealtimeDetections(initialStreams: Stream[]) {
  const [streams, setStreams] = useState(initialStreams);
  const supabaseRef = useRef(createClient());

  useEffect(() => {
    setStreams(initialStreams);
  }, [initialStreams]);

  useEffect(() => {
    const supabase = supabaseRef.current;

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
      .subscribe((status) => {
        if (status === "CHANNEL_ERROR") {
          // Silently handle — site works fine with static data
          console.debug("[WildWatch] Realtime not available, using static data");
        }
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return streams;
}
