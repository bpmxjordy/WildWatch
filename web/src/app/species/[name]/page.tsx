import { createServerClient } from "@/lib/supabase/server";
import Link from "next/link";
import { getSpeciesEmoji } from "@/lib/utils";

export const revalidate = 0;

interface PageProps {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);
  return {
    title: `${decoded} — WildWatch Species`,
    description: `Streams where ${decoded} has been detected.`,
  };
}

export default async function SpeciesDetailPage({ params }: PageProps) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);
  const supabase = await createServerClient();

  const { data: events } = await supabase
    .from("species_events")
    .select("*, streams:stream_id(slug, name, location_name)")
    .eq("common_name", decoded)
    .order("started_at", { ascending: false })
    .limit(50);

  return (
    <div>
      <Link
        href="/species"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-400 hover:text-white"
      >
        ← Back to species
      </Link>

      <div className="mb-8 flex items-center gap-3">
        <span className="text-4xl">{getSpeciesEmoji(decoded)}</span>
        <div>
          <h1 className="text-3xl font-bold text-white">{decoded}</h1>
          <p className="text-gray-400">
            {events?.length ?? 0} recorded sighting
            {(events?.length ?? 0) !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {(!events || events.length === 0) ? (
        <p className="py-12 text-center text-gray-500">No sightings recorded.</p>
      ) : (
        <div className="space-y-3">
          {events.map((event) => {
            const stream = event.streams as unknown as {
              slug: string;
              name: string;
              location_name: string | null;
            } | null;
            return (
              <Link
                key={event.id}
                href={stream ? `/stream/${stream.slug}` : "#"}
                className="block rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-600"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-white">
                      {stream?.name ?? "Unknown stream"}
                    </p>
                    {stream?.location_name && (
                      <p className="text-xs text-gray-500">
                        📍 {stream.location_name}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-400">
                      {new Date(event.started_at).toLocaleDateString()}
                    </p>
                    {event.peak_confidence && (
                      <p className="text-xs text-gray-500">
                        Peak: {Math.round(event.peak_confidence * 100)}%
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
