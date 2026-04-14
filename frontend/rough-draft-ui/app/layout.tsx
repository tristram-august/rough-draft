import "./globals.css";
import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Rough Draft",
  description: "Community-voted NFL draft board",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-slate-100">
            <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/70 backdrop-blur">
              <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-center">
                <div className="text-2xl font-bold tracking-tight">Rough Draft</div>
              </div>
            </header>

            <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>

            <footer className="mx-auto max-w-5xl px-4 pb-8 pt-2 text-xs text-slate-500">
              <div className="border-t border-slate-800 pt-4">Rough Draft • local dev</div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}