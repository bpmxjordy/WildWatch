"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { Stream } from "@/lib/supabase/types";

export default function AdminPage() {
  const supabase = useMemo(() => createClient(), []);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchStreams() {
    const { data } = await supabase
      .from("streams")
      .select("*")
      .order("name");
    setStreams(data ?? []);
    setLoading(false);
  }

  useEffect(() => {
    fetchStreams();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [form, setForm] = useState({
    slug: "",
    name: "",
    embed_url: "",
    source_url: "",
    location_name: "",
    country_code: "",
    platform: "youtube",
  });

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await supabase
      .from("streams")
      .insert(form as never);
    if (error) {
      alert(`Error: ${error.message}`);
      return;
    }
    setForm({
      slug: "",
      name: "",
      embed_url: "",
      source_url: "",
      location_name: "",
      country_code: "",
      platform: "youtube",
    });
    fetchStreams();
  }

  async function toggleActive(id: string, current: boolean) {
    await supabase
      .from("streams")
      .update({ is_active: !current } as never)
      .eq("id", id);
    setStreams((prev) =>
      prev.map((s) => (s.id === id ? { ...s, is_active: !current } : s))
    );
  }

  if (loading) {
    return <p className="py-20 text-center text-gray-500">Loading...</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-white">Admin — Manage Streams</h1>

      <form
        onSubmit={handleAdd}
        className="mb-8 space-y-3 rounded-xl border border-gray-800 bg-gray-900 p-4"
      >
        <h2 className="text-lg font-semibold text-white">Add Stream</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              ["slug", "Slug (url-safe)"],
              ["name", "Display Name"],
              ["embed_url", "Embed URL"],
              ["source_url", "Source URL (for yt-dlp)"],
              ["location_name", "Location"],
              ["country_code", "Country Code (ISO 3166-1 alpha-3)"],
            ] as const
          ).map(([key, label]) => (
            <input
              key={key}
              type="text"
              placeholder={label}
              required={key === "slug" || key === "name" || key === "embed_url" || key === "source_url"}
              value={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-green-500 focus:outline-none"
            />
          ))}
        </div>
        <button
          type="submit"
          className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
        >
          Add Stream
        </button>
      </form>

      <div className="space-y-2">
        {streams.map((s) => (
          <div
            key={s.id}
            className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 px-4 py-3"
          >
            <div>
              <p className="font-medium text-white">{s.name}</p>
              <p className="text-xs text-gray-500">{s.slug} — {s.location_name}</p>
            </div>
            <button
              onClick={() => toggleActive(s.id, s.is_active)}
              className={`rounded px-3 py-1 text-xs font-medium ${
                s.is_active
                  ? "bg-green-900/50 text-green-300"
                  : "bg-gray-800 text-gray-500"
              }`}
            >
              {s.is_active ? "Active" : "Inactive"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
