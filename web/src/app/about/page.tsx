export const metadata = {
  title: "About — WildWatch",
  description: "How WildWatch uses AI to detect wildlife in livestream cameras.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero */}
      <div className="border-b border-rule pb-10 mb-10">
        <span className="mb-3 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-accent-deep before:inline-block before:h-px before:w-4 before:bg-accent-deep">
          About
        </span>
        <h1 className="font-serif text-[clamp(40px,5vw,72px)] font-medium leading-[0.95] tracking-tight text-ink mb-6">
          Watching the wild,{" "}
          <em className="font-normal italic text-accent-deep">quietly</em>,
          together.
        </h1>
        <p className="text-[17px] leading-relaxed text-ink-2 max-w-[52ch]">
          WildWatch is a network of public wildlife camera livestreams, monitored
          by AI in real-time. Every camera streams live, free, to anyone with an
          internet connection — and every animal that walks into frame is
          automatically catalogued.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-5 border-b border-rule pb-10 mb-10 sm:grid-cols-4">
        {[
          { n: "22", l: "Cameras Live" },
          { n: "3", l: "Categories" },
          { n: "2,000+", l: "Species Supported" },
          { n: "60s", l: "Scan Interval" },
        ].map((s) => (
          <div key={s.l} className="border-l border-rule pl-4 first:border-0 first:pl-0">
            <span className="block font-serif text-[clamp(32px,3vw,48px)] font-medium tracking-tight leading-none text-ink">
              {s.n}
            </span>
            <span className="mt-2 block font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
              {s.l}
            </span>
          </div>
        ))}
      </div>

      {/* How it works */}
      <div className="mb-12">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
          Method
        </span>
        <h2 className="font-serif text-[28px] font-medium tracking-tight text-ink mt-1 mb-8">
          How a detection becomes a data point.
        </h2>

        <div className="flex flex-col">
          {[
            {
              num: "I.",
              title: "Frame extraction",
              desc: "The agent uses yt-dlp to resolve livestream URLs and ffmpeg to grab a single frame. URLs are cached for 3 hours to avoid rate limits. Frames from multiple streams are extracted in parallel.",
            },
            {
              num: "II.",
              title: "AI classification",
              desc: "Frames are sent to Google's SpeciesNet model — an ensemble of MegaDetector v5 (object detection) and EfficientNet V2 (species classification). Inference runs on a local GPU, grouped by country code for geographic filtering.",
            },
            {
              num: "III.",
              title: "Smart upload",
              desc: "Results are uploaded to Supabase only when the detection changes — consecutive blank frames are skipped. Old detections are pruned to keep the 5 most recent per stream, with storage cleanup.",
            },
            {
              num: "IV.",
              title: "Real-time dashboard",
              desc: "The Next.js dashboard subscribes to Supabase Realtime. When a new detection arrives, the grid updates instantly — no polling, no refresh needed.",
            },
          ].map((step, i) => (
            <div
              key={i}
              className={`grid grid-cols-[56px_1fr] gap-6 py-5 border-b border-rule ${
                i === 0 ? "border-t border-rule" : ""
              }`}
            >
              <span className="font-serif text-[28px] italic text-accent-deep">
                {step.num}
              </span>
              <div>
                <h3 className="font-serif text-[22px] font-medium tracking-tight text-ink mb-1.5">
                  {step.title}
                </h3>
                <p className="text-[14.5px] leading-relaxed text-ink-2 max-w-[56ch]">
                  {step.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tech stack */}
      <div className="border-t border-rule pt-9">
        <h3 className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-muted font-medium mb-5">
          Technology
        </h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            "Next.js 14",
            "Supabase",
            "SpeciesNet",
            "MegaDetector v5",
            "Tailwind CSS",
            "Vercel",
            "yt-dlp",
            "ffmpeg",
            "PyTorch + CUDA",
          ].map((t) => (
            <div
              key={t}
              className="rounded border border-dashed border-rule-2 bg-paper/40 px-4 py-4 text-center font-serif text-[15px] italic text-muted"
            >
              {t}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
