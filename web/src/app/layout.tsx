import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Navbar from "@/components/Navbar";
import Providers from "@/components/Providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "WildWatch — Live Wildlife Detection",
  description:
    "Browse 100+ wildlife livestreams with real-time AI species detection powered by SpeciesNet.",
  openGraph: {
    title: "WildWatch — Live Wildlife Detection",
    description:
      "Browse 100+ wildlife livestreams with real-time AI species detection.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <Navbar />
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
