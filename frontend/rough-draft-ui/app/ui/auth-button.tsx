"use client";

import * as React from "react";
import Link from "next/link";
import { createPortal } from "react-dom";
import { useAuth } from "../contexts/auth-context";

export function AuthButton() {
  const { user, login, register, logout } = useAuth();
  const [modalOpen, setModalOpen] = React.useState(false);
  const [mode, setMode] = React.useState<"login" | "register">("login");

  const [username, setUsername] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  // Track whether we're mounted on the client (avoid SSR portal mismatch)
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  function openModal(m: "login" | "register") {
    setMode(m);
    setError(null);
    setUsername("");
    setEmail("");
    setPassword("");
    setModalOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, email, password);
      }
      setModalOpen(false);
    } catch (err: any) {
      setError(err.message ?? "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  const modal = modalOpen && mounted && createPortal(
    <>
      <div
        className="fixed inset-0 z-[100] bg-black/60"
        onClick={() => setModalOpen(false)}
      />
      <div
        className="fixed left-1/2 top-1/2 z-[101] w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-slate-700 bg-slate-950 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => { setMode("login"); setError(null); }}
              className={`text-sm font-medium transition-colors ${mode === "login" ? "text-slate-100" : "text-slate-500 hover:text-slate-300"}`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => { setMode("register"); setError(null); }}
              className={`text-sm font-medium transition-colors ${mode === "register" ? "text-slate-100" : "text-slate-500 hover:text-slate-300"}`}
            >
              Register
            </button>
          </div>
          <button
            type="button"
            onClick={() => setModalOpen(false)}
            className="text-slate-500 hover:text-slate-300 text-lg leading-none"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-slate-500">Username</label>
            <input
              autoFocus
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500"
              placeholder="username"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="text-xs text-slate-500">Email</label>
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500"
                placeholder="you@example.com"
              />
            </div>
          )}

          <div>
            <label className="text-xs text-slate-500">Password</label>
            <input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500"
              placeholder={mode === "register" ? "min 8 characters" : "password"}
            />
          </div>

          {error && (
            <div className="rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-xs text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-100 hover:bg-slate-700 disabled:opacity-50 transition-colors mt-1"
          >
            {submitting ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
    </>,
    document.body
  );

  return (
    <>
      {user ? (
        <div className="flex items-center gap-3">
          <Link href={`/profile/${user.username}`} className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
            {user.username}
          </Link>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800/60 transition-colors"
          >
            Sign out
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => openModal("login")}
            className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800/60 transition-colors"
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => openModal("register")}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 hover:bg-slate-700 transition-colors"
          >
            Register
          </button>
        </div>
      )}
      {modal}
    </>
  );
}
