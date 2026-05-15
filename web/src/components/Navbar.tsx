import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="border-b border-gray-800 bg-gray-950">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-xl font-bold text-white">
          <span className="text-2xl">🌿</span>
          <span>WildWatch</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm text-gray-300 hover:text-white transition-colors">
            Streams
          </Link>
          <Link href="/species" className="text-sm text-gray-300 hover:text-white transition-colors">
            Species
          </Link>
          <Link href="/about" className="text-sm text-gray-300 hover:text-white transition-colors">
            About
          </Link>
        </div>
      </div>
    </nav>
  );
}
