"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

function ResetPasswordContent() {
  const params = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);

  if (!token) {
    return (
      <div className="max-w-sm mx-auto mt-20 text-center">
        <p className="text-slate-400 text-sm">Invalid reset link.</p>
        <Link href="/" className="mt-4 inline-block text-xs text-slate-500 hover:text-slate-300 transition-colors">Back to the board</Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="max-w-sm mx-auto mt-20 text-center space-y-4">
        <div className="text-2xl font-bold text-slate-100">Password updated!</div>
        <p className="text-slate-400 text-sm">You can now sign in with your new password.</p>
        <Link href="/" className="inline-block mt-2 rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-100 hover:bg-slate-700 transition-colors">
          Go to the board
        </Link>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords don't match"); return; }
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Reset failed");
      }
      setDone(true);
    } catch (err: any) {
      setError(err.message ?? "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-20">
      <div className="text-2xl font-bold text-slate-100 mb-6">Set new password</div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="text-xs text-slate-500">New password</label>
          <input
            autoFocus
            required
            type="password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500"
            placeholder="min 8 characters"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Confirm password</label>
          <input
            required
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500"
            placeholder="repeat password"
          />
        </div>
        {error && (
          <div className="rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-xs text-red-300">{error}</div>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-100 hover:bg-slate-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? "…" : "Update password"}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <React.Suspense fallback={<div className="mt-20 text-center text-slate-400">Loading…</div>}>
      <ResetPasswordContent />
    </React.Suspense>
  );
}
