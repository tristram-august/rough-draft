"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

function VerifyEmailContent() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = React.useState<"loading" | "success" | "error">("loading");

  React.useEffect(() => {
    if (!token) { setStatus("error"); return; }
    fetch(`${API_BASE}/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then((r) => setStatus(r.ok ? "success" : "error"))
      .catch(() => setStatus("error"));
  }, [token]);

  return (
    <div className="max-w-sm mx-auto mt-20 text-center space-y-4">
      {status === "loading" && <p className="text-slate-400">Verifying…</p>}
      {status === "success" && (
        <>
          <div className="text-2xl font-bold text-slate-100">Email verified!</div>
          <p className="text-slate-400 text-sm">Your account is all set.</p>
          <Link href="/" className="inline-block mt-2 rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-100 hover:bg-slate-700 transition-colors">
            Go to the board
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <div className="text-2xl font-bold text-slate-100">Invalid link</div>
          <p className="text-slate-400 text-sm">This verification link is invalid or has already been used.</p>
          <Link href="/" className="inline-block mt-2 text-xs text-slate-500 hover:text-slate-300 transition-colors">
            Back to the board
          </Link>
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <React.Suspense fallback={<div className="mt-20 text-center text-slate-400">Loading…</div>}>
      <VerifyEmailContent />
    </React.Suspense>
  );
}
