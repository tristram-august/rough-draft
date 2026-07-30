"use client";

import Link from "next/link";
import { useAuth } from "../contexts/auth-context";

/** Renders its link only for signed-in mods. Mod status lives client-side. */
export function ModLink({ href, label }: { href: string; label: string }) {
  const { user } = useAuth();
  if (!user?.is_mod) return null;
  return (
    <Link
      href={href}
      className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-700"
    >
      {label}
    </Link>
  );
}
