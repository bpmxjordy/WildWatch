export const metadata = {
  title: "About — WildWatch",
  description: "How WildWatch uses AI to detect wildlife in livestream cameras.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-3xl font-bold text-white">About WildWatch</h1>

      <div className="space-y-6 text-gray-300 leading-relaxed">
        <p>
          WildWatch aggregates 100+ public wildlife camera livestreams and uses
          AI to detect which streams currently have animals visible. Browse the
          grid, filter by species, and find the most interesting streams in
          real-time.
        </p>

        <h2 className="text-xl font-semibold text-white">How it works</h2>
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            A local agent continuously cycles through all streams, extracting a
            frame from each every 15-30 seconds.
          </li>
          <li>
            Each frame is analyzed by Google&apos;s SpeciesNet model — an
            ensemble of MegaDetector (finds animals, people, and vehicles) and
            an EfficientNet V2 species classifier (identifies 2000+ species).
          </li>
          <li>
            Detection results and thumbnails are uploaded to our database in
            real-time.
          </li>
          <li>
            The dashboard subscribes to live updates, so species tags refresh
            instantly as new detections come in.
          </li>
        </ol>

        <h2 className="text-xl font-semibold text-white">SpeciesNet</h2>
        <p>
          SpeciesNet is an open-source model by Google for wildlife camera trap
          image analysis. It combines object detection with species
          classification and supports geographic filtering to avoid impossible
          predictions (e.g. no kangaroos in Denmark).
        </p>

        <h2 className="text-xl font-semibold text-white">Stream Sources</h2>
        <p>
          Streams come from public wildlife cameras on YouTube, explore.org,
          zoo webcams, and national park cameras. All streams are publicly
          available and freely accessible.
        </p>

        <h2 className="text-xl font-semibold text-white">Open Source</h2>
        <p>
          WildWatch is an open-source project. The web dashboard is built with
          Next.js and deployed on Vercel. The detection agent runs locally on a
          GPU machine. Data is stored in Supabase with real-time subscriptions.
        </p>
      </div>
    </div>
  );
}
