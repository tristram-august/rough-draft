"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthButton } from "./auth-button";
import { VerifyBanner } from "./verify-banner";
import { SiteNav, SiteNavMobile } from "./site-nav";

/**
 * Social render slides (/social/...) are screenshotted at a fixed size for
 * Instagram -- the site header/footer would show up in every capture, so
 * those routes render bare instead of going through the normal chrome.
 */
export function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname?.startsWith("/social")) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5">
          <div className="flex items-center gap-6">
            <Link href="/" className="group flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-football.png" alt="" className="h-7 w-auto opacity-90 transition-opacity group-hover:opacity-100" />
              <span className="flex items-baseline gap-1.5">
                <span className="text-lg font-bold tracking-tight sm:text-xl">
                  Rough Draft
                </span>
                <span className="text-lg font-light tracking-tight text-slate-500 transition-colors group-hover:text-slate-400 sm:text-xl">
                  Football
                </span>
              </span>
            </Link>
            <SiteNav />
          </div>
          <AuthButton />
        </div>
        <SiteNavMobile />
        <VerifyBanner />
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-slate-800/60">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <div>Rough Draft Football • roughdraftfootball.com</div>
          <div className="flex gap-4">
            <Link href="/picks" className="hover:text-slate-300 transition-colors">
              Picks
            </Link>
            <Link href="/power" className="hover:text-slate-300 transition-colors">
              Power Rankings
            </Link>
            <Link href="/draft" className="hover:text-slate-300 transition-colors">
              Rough Draft
            </Link>
            <Link href="/fantasy" className="hover:text-slate-300 transition-colors">
              Fantasy Draft
            </Link>
            <Link href="/blog" className="hover:text-slate-300 transition-colors">
              Archive
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
