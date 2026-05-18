"use client";

import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import type { Database } from "./types";

// Single shared client with realtime disabled to stay within free tier limits
let _client: ReturnType<typeof createSupabaseClient<Database>> | null = null;

export function createClient() {
  if (!_client) {
    _client = createSupabaseClient<Database>(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        realtime: { params: { eventsPerSecond: 0 } },
        global: { headers: {} },
      }
    );
    // Disconnect realtime channel immediately
    _client.realtime.disconnect();
  }
  return _client;
}
