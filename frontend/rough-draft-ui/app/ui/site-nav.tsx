"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// The dashboard at "/" is the writing surface now, so /blog is an archive
// rather than a top-level section. Its routes stay — post permalinks live there.
export const NAV_ITEMS = [
  { href: "/picks", label: "Picks" },
  { href: "/power", label: "Power Rankings" },
  { href: "/draft", label: "Rough Draft" },
  { href: "/fantasy", label: "Fantasy Draft" },
] as const;

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Desktop nav — inline links beside the wordmark. */
export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="hidden sm:flex items-center gap-1">
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              active
                ? "bg-slate-800 text-slate-100"
                : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Mobile nav — scrollable pill row under the header bar. */
export function SiteNavMobile() {
  const pathname = usePathname();
  return (
    <nav className="sm:hidden flex gap-2 overflow-x-auto px-4 pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
              active
                ? "border-slate-600 bg-slate-800 text-slate-100"
                : "border-slate-800 text-slate-400"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
