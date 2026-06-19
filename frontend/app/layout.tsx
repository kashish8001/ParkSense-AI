import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "leaflet/dist/leaflet.css";

export const metadata: Metadata = {
  title: "ParkSense AI",
  description: "Parking enforcement intelligence for Bengaluru",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-border bg-card/80 backdrop-blur">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-4">
            <div>
              <h1 className="text-xl font-bold">ParkSense AI</h1>
              <p className="text-sm text-muted-foreground">Bengaluru parking enforcement intelligence</p>
            </div>
            <nav className="flex gap-4 text-sm">
              <Link href="/" className="text-primary hover:underline">
                Dashboard
              </Link>
              <Link href="/simulation" className="hover:text-primary">
                Simulation
              </Link>
              <a href="http://127.0.0.1:8000/docs" className="hover:text-primary" target="_blank" rel="noreferrer">
                API Docs
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
