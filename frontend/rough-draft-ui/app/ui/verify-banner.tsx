"use client";

import * as React from "react";
import { useAuth } from "../contexts/auth-context";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function VerifyBanner() {
  const { user, token } = useAuth();
  const [dismissed, setDismissed] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [sent, setSent] = React.useState(false);

  if (!user || user.email_verified || dismissed) return null;

  async function resend() {
    if (!token || sending || sent) return;
    setSending(true);
    try {
      await fetch(`${API_BASE}/auth/resend-verification`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setSent(true);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-amber-950/60 border-b border-amber-800/40">
      <div className="mx-auto max-w-5xl px-4 py-2 flex items-center justify-between gap-4 text-xs text-amber-300">
        <span>Please verify your email address to unlock all features.</span>
        <div className="flex items-center gap-3 shrink-0">
          {sent ? (
            <span className="text-amber-400">Email sent!</span>
          ) : (
            <button
              type="button"
              onClick={resend}
              disabled={sending}
              className="underline hover:text-amber-100 transition-colors disabled:opacity-50"
            >
              {sending ? "Sending…" : "Resend email"}
            </button>
          )}
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="text-amber-600 hover:text-amber-300 transition-colors text-sm leading-none"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
