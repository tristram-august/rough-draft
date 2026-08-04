"use client";

import * as React from "react";
import { timeAgo, type NewsFeed } from "../lib/dashboard";

const PAGE_SIZE = 6;

/**
 * Renders nothing until mounted, then fills in the relative time. timeAgo()
 * depends on Date.now(), so computing it once during SSR and again at
 * hydration can disagree by enough to cross a minute boundary ("5m ago" vs
 * "6m ago") — a hydration mismatch, since the server's HTML and the client's
 * first render need to match exactly. Deferring to a client-only effect
 * means both are empty on that first render; the real value fills in a
 * moment after mount instead.
 */
function RelativeTime({ iso }: { iso: string | null }) {
  const [text, setText] = React.useState("");
  React.useEffect(() => setText(timeAgo(iso)), [iso]);
  return <>{text}</>;
}

export function NewsWidget({ feed }: { feed: NewsFeed }) {
  const [visible, setVisible] = React.useState(PAGE_SIZE);

  if (feed.items.length === 0) return null;

  const shown = feed.items.slice(0, visible);
  const canExpand = feed.items.length > PAGE_SIZE;
  const isExpanded = visible >= feed.items.length;

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
          Around the league
        </h2>
        <span className="text-[11px] text-slate-600">{feed.source}</span>
      </div>

      <ul className="divide-y divide-slate-800/60">
        {shown.map((item, i) => (
          <li key={`${item.url ?? item.headline}-${i}`} className="py-2.5 first:pt-0 last:pb-0">
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block"
              >
                <span className="text-sm leading-snug text-slate-300 transition-colors group-hover:text-sky-300">
                  {item.headline}
                </span>
                <span className="mt-0.5 flex items-center gap-1 text-[11px] text-slate-600">
                  {item.source && (
                    <>
                      <span className="text-slate-500">{item.source}</span>
                      <span>·</span>
                    </>
                  )}
                  <RelativeTime iso={item.published} />
                </span>
              </a>
            ) : (
              <>
                <span className="text-sm leading-snug text-slate-300">{item.headline}</span>
                <span className="mt-0.5 flex items-center gap-1 text-[11px] text-slate-600">
                  {item.source && (
                    <>
                      <span className="text-slate-500">{item.source}</span>
                      <span>·</span>
                    </>
                  )}
                  <RelativeTime iso={item.published} />
                </span>
              </>
            )}
          </li>
        ))}
      </ul>

      {canExpand && (
        <button
          type="button"
          onClick={() => setVisible(isExpanded ? PAGE_SIZE : visible + PAGE_SIZE)}
          className="mt-3 w-full rounded-lg border border-slate-800 py-1.5 text-xs font-medium text-slate-500 transition-colors hover:border-slate-700 hover:text-slate-300"
        >
          {isExpanded ? "Show less" : "Show more"}
        </button>
      )}
    </section>
  );
}
