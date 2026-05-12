import "./globals.css";
import type { Metadata } from "next";
import Providers from "./providers";
import { AuthButton } from "./ui/auth-button";
import { VerifyBanner } from "./ui/verify-banner";

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
              <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between">
                <div className="absolute left-1/2 -translate-x-1/2 text-xl sm:text-3xl font-bold tracking-tight">Rough Draft</div>
                <div className="invisible text-xl sm:text-3xl font-bold">Rough Draft</div>
                <AuthButton />
              </div>
              <VerifyBanner />
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