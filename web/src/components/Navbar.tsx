import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-rule bg-[var(--bg)]/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-page items-center justify-between px-7 py-4">
        <Link href="/" className="flex items-baseline gap-2.5">
          <span className="font-serif text-2xl font-semibold tracking-tight text-ink">
            Wild<em className="font-normal not-italic text-accent-deep">Watch</em>
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
            Est. 2026
          </span>
        </Link>
        <div className="flex items-center gap-1">
          <Link
            href="/"
            className="rounded-full px-3.5 py-2 text-[13px] text-ink-2 transition-colors hover:bg-paper-2"
          >
            Live cameras
          </Link>
          <Link
            href="/map"
            className="rounded-full px-3.5 py-2 text-[13px] text-ink-2 transition-colors hover:bg-paper-2"
          >
            Map
          </Link>
          <Link
            href="/about"
            className="rounded-full px-3.5 py-2 text-[13px] text-ink-2 transition-colors hover:bg-paper-2"
          >
            About
          </Link>
        </div>
      </div>
    </nav>
  );
}
