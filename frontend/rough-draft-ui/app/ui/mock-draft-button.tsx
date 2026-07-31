"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { useAuth } from "../contexts/auth-context";
import { API_BASE } from "../lib/posts";

const MOCK_DRAFT_URL = "/mock-draft.html";

type EmailRequest = {
  type: "mockdraft:email";
  summary: string;
  slot: number;
  rounds: number;
  valueIndex: number;
};

/**
 * Launches the standalone mock draft simulator in a near-fullscreen overlay.
 *
 * The simulator is a self-contained static page in /public — no bundler, no
 * imports, no API. Running it in a same-origin iframe means its localStorage
 * (mockDraftHistory2026 / mockDraftInProgress2026) persists exactly as it does
 * standalone, so in-progress and saved drafts survive closing the overlay.
 */
export function MockDraftButton() {
  const { user, token } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [mounted, setMounted] = React.useState(false);
  const frameRef = React.useRef<HTMLIFrameElement>(null);

  // Iframes cache independently of a parent hard-refresh, which is how a stale
  // copy of the simulator survives a redeploy. One cache-buster per page load
  // keeps it fresh without refetching on every open.
  const [cacheBust] = React.useState(() => Date.now());
  const frameSrc = `${MOCK_DRAFT_URL}?v=${cacheBust}`;

  React.useEffect(() => setMounted(true), []);

  const canEmail = Boolean(user && token);

  // Bridge between the sandboxed simulator and the API: the static page has no
  // auth context, so it hands its summary up and this side makes the call.
  React.useEffect(() => {
    if (!open) return;

    function reply(message: object) {
      frameRef.current?.contentWindow?.postMessage(message, window.location.origin);
    }

    async function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      const data = event.data as EmailRequest | undefined;
      if (!data || data.type !== "mockdraft:email") return;

      if (!canEmail) {
        reply({ type: "mockdraft:email-result", message: "Sign in to email results." });
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/mock-draft/email`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            summary: data.summary,
            slot: data.slot,
            rounds: data.rounds,
            value_index: data.valueIndex,
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail ?? `Failed (${res.status})`);
        }
        const body = await res.json();
        reply({ type: "mockdraft:email-result", message: `Sent to ${body.to}` });
      } catch (err) {
        reply({
          type: "mockdraft:email-result",
          message: err instanceof Error ? err.message : "Couldn't send that email",
        });
      }
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [open, canEmail, token]);

  // Escape to close, and stop the page behind from scrolling while open.
  React.useEffect(() => {
    if (!open) return;

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const overlay =
    open && mounted
      ? createPortal(
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Mock draft simulator"
            className="fixed inset-0 z-[120] flex flex-col bg-slate-950/95 backdrop-blur-sm"
          >
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-800 px-4 py-2.5">
              {/* Title truncates so the actions never wrap on a narrow phone. */}
              <span className="truncate text-sm font-semibold text-slate-200">
                Mock Draft Simulator
              </span>
              <div className="flex shrink-0 items-center gap-2">
                <a
                  href={MOCK_DRAFT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hidden rounded-lg border border-slate-800 px-2.5 py-1 text-xs text-slate-400 transition-colors hover:border-slate-700 hover:text-slate-200 sm:inline-block"
                >
                  Open in new tab
                </a>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-100 transition-colors hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>

            <iframe
              ref={frameRef}
              src={frameSrc}
              title="Mock draft simulator"
              onLoad={() =>
                frameRef.current?.contentWindow?.postMessage(
                  { type: "mockdraft:email-available", available: canEmail },
                  window.location.origin
                )
              }
              className="min-h-0 w-full flex-1 border-0 bg-slate-950"
            />
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-xl border border-sky-700 bg-sky-900/40 px-3 py-1.5 text-xs font-medium text-sky-100 transition-colors hover:bg-sky-900/70"
      >
        Mock Draft
      </button>
      {overlay}
    </>
  );
}
