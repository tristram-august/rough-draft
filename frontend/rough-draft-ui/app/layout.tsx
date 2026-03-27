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
          <div className="min-h-screen bg-gradient-to-b from-slate-100 via-slate-50 to-white text-slate-900">
            <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/70 backdrop-blur">
              <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl border border-slate-200 bg-white shadow-sm flex items-center justify-center font-semibold">
                    RD
                  </div>
                  <div>
                    <div className="text-lg font-semibold leading-tight">Rough Draft</div>
                    <div className="text-xs text-slate-500">
                      Draft board + community bust/success votes
                    </div>
                  </div>
                </div>

                <a
                  className="text-sm text-slate-500 hover:text-slate-900"
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                >
                  API Docs
                </a>
              </div>
            </header>

            <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>

            <footer className="mx-auto max-w-5xl px-4 pb-8 pt-2 text-xs text-slate-500">
              <div className="border-t border-slate-200 pt-4">Rough Draft • local dev</div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}